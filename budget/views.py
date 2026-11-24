from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.db.models import DecimalField, Sum
from django.db.models.functions import Coalesce, ExtractMonth
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import BudgetEntryForm, MonthlyFilterForm, SignUpForm, YearlyGoalForm
from .models import BudgetEntry, YearlyGoal

ZERO = Decimal('0')


# ----------------------------------------------------------------------
# 共通ヘルパー
# ----------------------------------------------------------------------
def _user_entries(request):
    """ログイン中ユーザー自身のエントリだけを返す。

    すべてのビューはここを入口にして、「user での絞り込み忘れ」
    （他人のデータが見える・消せる事故）を構造的に防ぐ。
    """
    return BudgetEntry.objects.filter(user=request.user).select_related('category')


def _total(queryset):
    """amount の合計。該当なしなら 0。"""
    return queryset.aggregate(
        total=Coalesce(Sum('amount'), ZERO, output_field=DecimalField())
    )['total']


def _redirect_back(request, default='budget:dashboard'):
    """?next= / hidden next があれば（安全なURLに限り）そこへ戻す。"""
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(default)


# ----------------------------------------------------------------------
# ダッシュボード
# ----------------------------------------------------------------------
@login_required
def dashboard(request):
    """ダッシュボード表示"""
    today = timezone.localdate()  # 日本時間の「今日」
    entries = _user_entries(request)

    month_entries = entries.filter(date__year=today.year, date__month=today.month)
    monthly_income = _total(month_entries.filter(category__category_type='income'))
    monthly_expense = _total(month_entries.filter(category__category_type='expense'))
    monthly_balance = monthly_income - monthly_expense

    year_entries = entries.filter(date__year=today.year)
    yearly_income = _total(year_entries.filter(category__category_type='income'))
    yearly_expense = _total(year_entries.filter(category__category_type='expense'))
    yearly_savings = yearly_income - yearly_expense

    yearly_goal = YearlyGoal.objects.filter(user=request.user, year=today.year).first()
    goal_achievement_rate = 0
    if yearly_goal and yearly_goal.savings_goal:
        goal_achievement_rate = round(yearly_savings / yearly_goal.savings_goal * 100, 2)

    context = {
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_balance': monthly_balance,
        'yearly_savings': yearly_savings,
        'yearly_goal': yearly_goal,
        'goal_achievement_rate': goal_achievement_rate,
        'recent_entries': entries[:10],
        'current_year': today.year,
        'current_month': today.month,
    }
    return render(request, 'budget/dashboard.html', context)


# ----------------------------------------------------------------------
# エントリの追加・編集・削除
# ----------------------------------------------------------------------
@login_required
def add_entry(request):
    """家計簿エントリ追加"""
    if request.method == 'POST':
        form = BudgetEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)  # 一旦保存を止める
            entry.user = request.user        # user をセット
            entry.save()
            messages.success(request, '家計簿エントリを追加しました。')
            return _redirect_back(request)
    else:
        form = BudgetEntryForm()

    return render(request, 'budget/entry_form.html', {
        'form': form,
        'title': '新規エントリ',
        'next': request.GET.get('next', ''),
    })


@login_required
def edit_entry(request, pk):
    """家計簿エントリ編集（自分のエントリのみ。他人のものは 404）"""
    entry = get_object_or_404(BudgetEntry, pk=pk, user=request.user)
    if request.method == 'POST':
        form = BudgetEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, '家計簿エントリを更新しました。')
            return _redirect_back(request)
    else:
        form = BudgetEntryForm(instance=entry)

    return render(request, 'budget/entry_form.html', {
        'form': form,
        'title': 'エントリ編集',
        'next': request.GET.get('next', ''),
    })


@login_required
@require_POST  # 削除は POST のみ（GET で消えるとリンクのプリフェッチ等で事故る）
def delete_entry(request, pk):
    """家計簿エントリ削除（自分のエントリのみ。他人のものは 404）"""
    entry = get_object_or_404(BudgetEntry, pk=pk, user=request.user)
    entry.delete()
    messages.success(request, '家計簿エントリを削除しました。')
    return _redirect_back(request)


# ----------------------------------------------------------------------
# 月別表示
# ----------------------------------------------------------------------
@login_required
def monthly_view(request):
    """月別表示"""
    today = timezone.localdate()

    # ?page=2 のように year/month が無いリクエストでも、
    # 「今月」で補ったデータでフォームを検証する
    data = {
        'year': request.GET.get('year', today.year),
        'month': request.GET.get('month', today.month),
    }
    form = MonthlyFilterForm(data)
    if form.is_valid():
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
    else:
        year, month = today.year, today.month
        form = MonthlyFilterForm(initial={'year': year, 'month': month})
        messages.warning(request, '年月の指定が正しくないため、今月を表示しています。')

    entries = _user_entries(request).filter(
        date__year=year, date__month=month
    ).order_by('-date', '-created_at')

    # ページネーション（1ページ20件）
    page_obj = Paginator(entries, 20).get_page(request.GET.get('page'))

    # カテゴリ別集計
    def by_category(category_type):
        return list(
            entries.filter(category__category_type=category_type)
            .values('category__name', 'category__color')
            .annotate(total=Sum('amount', output_field=DecimalField()))
            .order_by('-total')
        )

    income_by_category = by_category('income')
    expense_by_category = by_category('expense')
    total_income = sum((i['total'] or ZERO for i in income_by_category), ZERO)
    total_expense = sum((i['total'] or ZERO for i in expense_by_category), ZERO)

    # 前月・翌月リンク用
    first_day = date(year, month, 1)
    prev_month = first_day - timedelta(days=1)
    next_month = (first_day + timedelta(days=32)).replace(day=1)

    context = {
        'form': form,
        'page_obj': page_obj,
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'year': year,
        'month': month,
        'prev_month': prev_month,
        'next_month': next_month,
        # ページ送りリンクが年月を失わないようにする
        'querystring': f'year={year}&month={month}',
    }
    return render(request, 'budget/monthly_view.html', context)


# ----------------------------------------------------------------------
# 年間グラフ
# ----------------------------------------------------------------------
def get_monthly_totals(user, year):
    """{月(1-12): 合計金額} の辞書を (収入, 支出) の順で返す。"""
    rows = (
        BudgetEntry.objects.filter(user=user, date__year=year)
        .annotate(m=ExtractMonth('date'))
        .values('m', 'category__category_type')
        .annotate(total=Sum('amount'))
        .order_by('m')
    )
    income, expense = {}, {}
    for row in rows:
        target = income if row['category__category_type'] == 'income' else expense
        target[row['m']] = int(row['total'])
    return income, expense


@login_required
def graph_view(request):
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
    except ValueError:
        year = today.year
    year = min(max(year, 2000), 2100)

    income, expense = get_monthly_totals(request.user, year)

    # 1〜12月を固定で並べ、データの無い月は 0 で埋める。
    # → ラベル・収入・支出の3本が必ず同じ長さ・同じ並びになる。
    months = list(range(1, 13))
    income_data = [income.get(m, 0) for m in months]
    expense_data = [expense.get(m, 0) for m in months]

    context = {
        'year': year,
        'months': [f'{m}月' for m in months],
        'income_data': income_data,
        'expense_data': expense_data,
        'rows': [
            {'label': f'{m}月', 'income': i, 'expense': e, 'balance': i - e}
            for m, i, e in zip(months, income_data, expense_data)
        ],
        'total_income': sum(income_data),
        'total_expense': sum(expense_data),
        'total_balance': sum(income_data) - sum(expense_data),
    }
    return render(request, 'budget/graph.html', context)


# ----------------------------------------------------------------------
# 年間目標
# ----------------------------------------------------------------------
@login_required
def goal_list(request):
    """年間目標の一覧 + 新規追加（同じ画面）"""
    if request.method == 'POST':
        form = YearlyGoalForm(request.POST, user=request.user)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            messages.success(request, f'{goal.year}年の目標を登録しました。')
            return redirect('budget:goal_list')
    else:
        form = YearlyGoalForm(user=request.user)

    entries = _user_entries(request)
    rows = []
    for goal in YearlyGoal.objects.filter(user=request.user).order_by('-year'):
        year_entries = entries.filter(date__year=goal.year)
        savings = (_total(year_entries.filter(category__category_type='income'))
                   - _total(year_entries.filter(category__category_type='expense')))
        rate = round(savings / goal.savings_goal * 100, 1) if goal.savings_goal else 0
        rows.append({
            'goal': goal,
            'savings': savings,
            'rate': rate,
            'bar': max(0, min(100, rate)),  # 進捗バー用（0〜100に丸める）
        })

    return render(request, 'budget/goal_list.html', {'form': form, 'rows': rows})


@login_required
def goal_edit(request, pk):
    """年間目標の編集（自分の目標のみ。他人のものは 404）"""
    goal = get_object_or_404(YearlyGoal, pk=pk, user=request.user)
    if request.method == 'POST':
        form = YearlyGoalForm(request.POST, instance=goal, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '年間目標を更新しました。')
            return redirect('budget:goal_list')
    else:
        form = YearlyGoalForm(instance=goal, user=request.user)

    return render(request, 'budget/entry_form.html', {
        'form': form,
        'title': f'{goal.year}年の目標を編集',
        'next': reverse('budget:goal_list'),   # キャンセルの戻り先
    })


@login_required
@require_POST
def goal_delete(request, pk):
    """年間目標の削除（POSTのみ・自分の目標のみ）"""
    goal = get_object_or_404(YearlyGoal, pk=pk, user=request.user)
    goal.delete()
    messages.success(request, '年間目標を削除しました。')
    return redirect('budget:goal_list')


# ----------------------------------------------------------------------
# ログイン / ユーザー登録
# ----------------------------------------------------------------------
class BudgetLoginView(LoginView):
    """ログイン画面。登録が許可されているときだけ「新規登録」リンクを出す。"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['allow_signup'] = settings.ALLOW_SIGNUP
        return context


def signup(request):
    """ユーザー登録。登録した人はそのままログイン状態にする。"""
    if not settings.ALLOW_SIGNUP:
        raise Http404  # 無効のときは「画面が存在しない」ことにする

    if request.user.is_authenticated:
        return redirect('budget:dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'アカウントを作成しました。まずは年間目標を設定してみましょう。')
            return redirect('budget:goal_list')
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})

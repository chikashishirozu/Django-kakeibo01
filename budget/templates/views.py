from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Sum, Q
from django.db.models.functions import Coalesce, TruncMonth
from datetime import date, datetime
from decimal import Decimal
from django.db.models import Sum, DecimalField
from collections import OrderedDict
from .models import BudgetEntry, Category, YearlyGoal
from .forms import BudgetEntryForm, MonthlyFilterForm

import calendar
from datetime import date
from django.utils import timezone

@login_required
def dashboard(request):
    """ダッシュボード表示"""
    current_year = date.today().year
    current_month = date.today().month
    
    # 今月の収支計算
    monthly_income = BudgetEntry.objects.filter(
        date__year=current_year,
        date__month=current_month,
        category__category_type='income'
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
    )['total']

    monthly_expense = BudgetEntry.objects.filter(
        date__year=current_year,
        date__month=current_month,
        category__category_type='expense'
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
    )['total']

    monthly_balance = monthly_income - monthly_expense

    # 年間貯蓄計算
    yearly_income = BudgetEntry.objects.filter(
        date__year=current_year,
        category__category_type='income'
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
    )['total']

    yearly_expense = BudgetEntry.objects.filter(
        date__year=current_year,
        category__category_type='expense'
    ).aggregate(
        total=Coalesce(Sum('amount'), Decimal('0.0'), output_field=DecimalField())
    )['total']
    
    yearly_savings = yearly_income - yearly_expense
    
    # 年間目標取得
    try:
        yearly_goal = YearlyGoal.objects.get(year=current_year)
        goal_achievement_rate = round((yearly_savings / yearly_goal.savings_goal * 100), 2) if yearly_goal.savings_goal else 0
    except YearlyGoal.DoesNotExist:
        yearly_goal = None
        goal_achievement_rate = 0
    
    # 最近のエントリ
    recent_entries = BudgetEntry.objects.select_related('category')[:10]
    
    context = {
        'monthly_income': monthly_income,
        'monthly_expense': monthly_expense,
        'monthly_balance': monthly_balance,
        'yearly_savings': yearly_savings,
        'yearly_goal': yearly_goal,
        'goal_achievement_rate': goal_achievement_rate,
        'recent_entries': recent_entries,
        'current_year': current_year,
        'current_month': current_month,
    }
    
    return render(request, 'budget/dashboard.html', context)

@login_required
def add_entry(request):
    """家計簿エントリ追加"""
    if request.method == 'POST':
        form = BudgetEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)     # ← 一旦保存を止める
            entry.user = request.user           # ← user をセット
            entry.save()                        # ← 今回保存！
            messages.success(request, '家計簿エントリを追加しました。')
            return redirect('budget:dashboard')
    else:
        form = BudgetEntryForm()
    
    return render(request, 'budget/entry_form.html', {'form': form, 'title': '新規エントリ'})

@login_required
def monthly_view(request):
    """月別表示"""
    form = MonthlyFilterForm(request.GET or None)
    
    if form.is_valid():
        year = form.cleaned_data['year']
        month = form.cleaned_data['month']
    else:
        year = date.today().year
        month = date.today().month
    
    # 月別データ取得
    entries = BudgetEntry.objects.filter(
        date__year=year,
        date__month=month
    ).select_related('category').order_by('-date')
    
    # ページネーション追加
    paginator = Paginator(entries, 20)  # 1ページ20件
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        # ...（既存のcontext）...
        'page_obj': page_obj,
    }    
    
    # カテゴリ別集計
    income_by_category = entries.filter(
        category__category_type='income'
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount', output_field=DecimalField())
    ).order_by('-total')

    expense_by_category = entries.filter(
        category__category_type='expense'
    ).values('category__name', 'category__color').annotate(
        total=Sum('amount', output_field=DecimalField())
    ).order_by('-total')

    # Noneの合計を防ぐために Decimal で初期化
    total_income = sum(item['total'] or Decimal('0.0') for item in income_by_category)
    total_expense = sum(item['total'] or Decimal('0.0') for item in expense_by_category)
        
    context = {
        'form': form,
        'entries': entries,
        'income_by_category': income_by_category,
        'expense_by_category': expense_by_category,
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': total_income - total_expense,
        'year': year,
        'month': month,
    }
    
    return render(request, 'budget/monthly_view.html', context)

@login_required
def edit_entry(request, pk):
    """家計簿エントリ編集"""
    entry = get_object_or_404(BudgetEntry, pk=pk)
    if request.method == 'POST':
        form = BudgetEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, '家計簿エントリを更新しました。')
            return redirect('budget:dashboard')
    else:
        form = BudgetEntryForm(instance=entry)
    
    return render(request, 'budget/entry_form.html', {
        'form': form,
        'title': 'エントリ編集'
    })

@login_required
def delete_entry(request, pk):
    """家計簿エントリ削除"""
    entry = get_object_or_404(BudgetEntry, pk=pk)
    if request.method == 'POST':
        entry.delete()
        messages.success(request, '家計簿エントリを削除しました。')
    return redirect('budget:dashboard')

def get_monthly_totals(user, year):
    entries = BudgetEntry.objects.filter(user=user, date__year=year)

    monthly_data = entries.annotate(month=TruncMonth('date')) \
        .values('month', 'category__category_type') \
        .annotate(total=Sum('amount')) \
        .order_by('month')

    income_data = {}
    expense_data = {}

    for item in monthly_data:
        month = item['month'].strftime('%Y-%m')
        total = float(item['total'])
        if item['category__category_type'] == 'income':
            income_data[month] = total
        else:
            expense_data[month] = total

    return income_data, expense_data

@login_required   
def graph_view(request):
    year = date.today().year
    income_data, expense_data = get_monthly_totals(request.user, year)
    context = {
        'income_data': list(income_data.values()),
        'expense_data': list(expense_data.values()),
        'months': [calendar.month_abbr[int(m.split('-')[1])] for m in income_data.keys()],
        'year': year,
    }
    return render(request, 'budget/graph.html', context)


    

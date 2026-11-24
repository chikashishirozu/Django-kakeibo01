from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from .models import BudgetEntry, Category, YearlyGoal


class BudgetEntryForm(forms.ModelForm):
    """家計簿入力フォーム"""

    class Meta:
        model = BudgetEntry
        fields = ['date', 'category', 'amount', 'description']
        widgets = {
            # type="date" の input は値が YYYY-MM-DD でないと空表示になる。
            # LANGUAGE_CODE='ja' だと既定が YYYY/MM/DD になるため format を明示する。
            'date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '金額を入力',
                'min': 0,
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '摘要（任意）',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 新規入力の初期日付は「日本時間の今日」
        if not self.instance.pk and 'date' not in (kwargs.get('initial') or {}):
            self.initial['date'] = timezone.localdate()

        # 有効なカテゴリだけ表示。ただし編集中のエントリが
        # 無効化済みカテゴリを使っていても、それは選択肢に残す
        queryset = Category.objects.filter(is_active=True)
        if self.instance.pk:
            queryset = Category.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.category_id)
            )
        self.fields['category'].queryset = queryset


def _current_year():
    return timezone.localdate().year


def _current_month():
    return timezone.localdate().month


class MonthlyFilterForm(forms.Form):
    """月別フィルタフォーム"""

    # initial に callable を渡すと、表示のたびに評価される。
    # （date.today().year を直接書くと、サーバー起動時の値で固定されてしまう）
    year = forms.IntegerField(
        label='年',
        min_value=2000,
        max_value=2100,
        initial=_current_year,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    month = forms.IntegerField(
        label='月',
        min_value=1,
        max_value=12,
        initial=_current_month,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12}),
    )


class YearlyGoalForm(forms.ModelForm):
    """年間貯蓄目標フォーム。user はフォームに出さず、ビュー側でログイン中ユーザーを入れる。"""

    year = forms.IntegerField(
        label='年', min_value=2000, max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
    )
    savings_goal = forms.DecimalField(
        label='貯蓄目標額（円）', min_value=0, max_digits=12, decimal_places=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1000}),
    )

    class Meta:
        model = YearlyGoal
        fields = ['year', 'savings_goal']

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if not self.instance.pk:
            self.initial.setdefault('year', timezone.localdate().year)

    def clean_year(self):
        # ModelForm は user を持たないため、(user, year) の重複は自分で検査する。
        # （最後の砦は DB の UniqueConstraint）
        year = self.cleaned_data['year']
        duplicated = (
            YearlyGoal.objects.filter(user=self.user, year=year)
            .exclude(pk=self.instance.pk)
            .exists()
        )
        if duplicated:
            raise ValidationError(f'{year}年の目標はすでに登録されています。一覧から編集してください。')
        return year


class SignUpForm(UserCreationForm):
    """ユーザー登録フォーム。パスワードは settings.AUTH_PASSWORD_VALIDATORS で検査される。"""

    class Meta:
        model = User
        fields = ('username',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

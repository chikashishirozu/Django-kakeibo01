from django import forms
from .models import BudgetEntry, Category, MonthlyBudget
from datetime import date

class BudgetEntryForm(forms.ModelForm):
    """家計簿入力フォーム"""
    
    class Meta:
        model = BudgetEntry
        fields = ['date', 'category', 'amount', 'description']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '金額を入力'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '摘要（任意）'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # アクティブなカテゴリのみ表示
        self.fields['category'].queryset = Category.objects.filter(is_active=True)

class MonthlyFilterForm(forms.Form):
    """月別フィルタフォーム"""
    year = forms.IntegerField(
        label='年',
        initial=date.today().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    month = forms.IntegerField(
        label='月',
        initial=date.today().month,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 12})
    )

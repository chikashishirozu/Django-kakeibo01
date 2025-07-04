# Create your models here.

from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.contrib.auth.models import User
import datetime

class Category(models.Model):
    """収支カテゴリ（食費、交通費、給与など）"""
    CATEGORY_TYPES = [
        ('income', '収入'),
        ('expense', '支出'),
    ]
    
    name = models.CharField('カテゴリ名', max_length=50)
    category_type = models.CharField('種別', max_length=10, choices=CATEGORY_TYPES)
    color = models.CharField('表示色', max_length=7, default='#007bff')  # HEXカラー
    is_active = models.BooleanField('有効', default=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ'
        ordering = ['category_type', 'name']
    
    def __str__(self):
        return f"{self.get_category_type_display()}: {self.name}"

class BudgetEntry(models.Model):
    """家計簿エントリ（日々の収支記録）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)    
    date = models.DateField('日付', default=datetime.date.today)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='カテゴリ')
    amount = models.DecimalField(
        '金額', 
        max_digits=10, 
        decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    description = models.CharField('摘要', max_length=200, blank=True)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '家計簿エントリ'
        verbose_name_plural = '家計簿エントリ'
        ordering = ['-date', '-created_at']
    
    def __str__(self):
        return f"{self.date} - {self.category.name}: {self.amount:,}円"

class MonthlyBudget(models.Model):
    """月別予算設定"""
    year = models.IntegerField('年')
    month = models.IntegerField('月')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='カテゴリ')
    budget_amount = models.DecimalField('予算額', max_digits=10, decimal_places=0)
    
    class Meta:
        verbose_name = '月別予算'
        verbose_name_plural = '月別予算'
        unique_together = ['year', 'month', 'category']
    
    def __str__(self):
        return f"{self.year}年{self.month}月 - {self.category.name}: {self.budget_amount:,}円"

class YearlyGoal(models.Model):
    """年間貯蓄目標"""
    year = models.IntegerField('年', unique=True)
    savings_goal = models.DecimalField('貯蓄目標額', max_digits=12, decimal_places=0)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '年間目標'
        verbose_name_plural = '年間目標'
    
    def __str__(self):
        return f"{self.year}年目標: {self.savings_goal:,}円"

from django.contrib import admin
from .models import Category, BudgetEntry, MonthlyBudget, YearlyGoal

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category_type', 'color', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name']

@admin.register(BudgetEntry)
class BudgetEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'category', 'amount', 'description']
    list_filter = ['date', 'category__category_type', 'category']
    search_fields = ['description']
    date_hierarchy = 'date'

@admin.register(YearlyGoal)
class YearlyGoalAdmin(admin.ModelAdmin):
    list_display = ['year', 'savings_goal']

"""household_budget プロジェクトの URL 設定"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from budget import views as budget_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # ログイン / ログアウト（settings.LOGIN_URL = 'login' が指す先）
    path('accounts/login/', budget_views.BudgetLoginView.as_view(), name='login'),
    path('accounts/signup/', budget_views.signup, name='signup'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('budget/', include('budget.urls')),

    # permanent=True (301) はブラウザに永久キャッシュされるため、将来の変更に備えて 302 にする
    path('', RedirectView.as_view(pattern_name='budget:dashboard', permanent=False)),
]

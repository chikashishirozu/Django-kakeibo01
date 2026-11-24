from django.urls import path
from . import views

app_name = 'budget'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('add/', views.add_entry, name='add_entry'),
    path('monthly/', views.monthly_view, name='monthly_view'),
    path('entry/<int:pk>/edit/', views.edit_entry, name='edit_entry'),
    path('entry/<int:pk>/delete/', views.delete_entry, name='delete_entry'),
    path('graph/', views.graph_view, name='graph'),
    path('goals/', views.goal_list, name='goal_list'),
    path('goals/<int:pk>/edit/', views.goal_edit, name='goal_edit'),
    path('goals/<int:pk>/delete/', views.goal_delete, name='goal_delete'),
]

from django.contrib import admin
from django.urls import path, include
from budget import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('budget/', include('budget.urls')),
]

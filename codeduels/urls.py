"""
URL configuration for codeduels project.
"""
from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('problems/', include('problems.urls')),
    path('duels/', include('duels.urls')),
    path('interviews/', include('interviews.urls')),
]

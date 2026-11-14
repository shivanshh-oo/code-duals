from django.urls import path
from . import views

urlpatterns = [
    path('', views.problem_list, name='problem_list'),
    path('api/', views.problem_list_api, name='problem_list_api'),
    path('<int:pk>/', views.problem_detail, name='problem_detail'),
]

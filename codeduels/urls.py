"""
URL configuration for codeduels project.
"""
from django.contrib import admin
from django.urls import path, include
from . import views
from accounts import interviews as voice_interviews
from interviews import ai

urlpatterns = [
    path('ai/', ai.lobby, name='ai_interview'),
    path('ai/chat/', ai.chat, name='ai_chat'),
    path('ai/start/', ai.start, name='ai_start'),
    path('ai/<uuid:pk>/', ai.room, name='ai_room'),
    path('ai/<uuid:pk>/answer/', ai.answer, name='ai_answer'),
    path('interview/', voice_interviews.interview, name='interview'),
    path('interview/evaluate/', voice_interviews.evaluate, name='interview_evaluate'),
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('problems/', include('problems.urls')),
    path('duels/', include('duels.urls')),
    path('interviews/', include('interviews.urls')),
]

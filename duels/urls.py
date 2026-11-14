from django.urls import path
from . import views

urlpatterns = [
    path('play/', views.play, name='play'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('practice/<int:problem_id>/', views.practice, name='practice'),
    path('practice/<int:problem_id>/submit/', views.practice_submit, name='practice_submit'),

    # Quick match
    path('quick-match/join/', views.quick_match_join, name='quick_match_join'),
    path('quick-match/poll/', views.quick_match_poll, name='quick_match_poll'),
    path('quick-match/cancel/', views.quick_match_cancel, name='quick_match_cancel'),

    # Create private match
    path('create-match/', views.create_match, name='create_match'),

    # Match arena and status
    path('match/<int:match_id>/', views.match_arena, name='match_arena'),
    path('match-status/<int:match_id>/', views.match_status_api, name='match_status_api'),
    path('match/<int:match_id>/submit/<int:problem_id>/', views.match_submit, name='match_submit'),
    path('match/<int:match_id>/result/', views.match_result, name='match_result'),
]

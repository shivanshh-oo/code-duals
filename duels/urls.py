from django.urls import path
from . import views

urlpatterns = [
    path('daily/', views.daily_challenge, name='daily_challenge'),
    path('submissions/', views.submission_history, name='submission_history'),
    path('history/', views.match_history, name='match_history'),
    path('friends/', views.friends, name='friends'),
    path('friends/add/', views.add_friend, name='add_friend'),
    path('friends/accept/<int:friendship_id>/', views.accept_friend, name='accept_friend'),
    path('friends/challenge/<int:user_id>/', views.challenge_friend, name='challenge_friend'),
    path('notifications/', views.notifications, name='notifications'),
    path('match/<int:match_id>/rematch/', views.rematch, name='rematch'),
    path('match/<int:match_id>/abandon/', views.abandon_match, name='abandon_match'),
    path('spectate/<int:match_id>/', views.spectate, name='spectate'),
    path('spectate/<int:match_id>/status/', views.spectator_status, name='spectator_status'),
    path('join/<str:invite_code>/', views.join_match, name='join_match'),
    path('match/<int:match_id>/ready/', views.ready_match, name='ready_match'),
    path('match/<int:match_id>/switch-team/', views.switch_team, name='switch_team'),
    path('leaderboard/export/', views.leaderboard_csv, name='leaderboard_csv'),
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

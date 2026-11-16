from django.urls import path
from . import views

urlpatterns = [
    path('', views.track_list, name='interview_tracks'),
    path('start/<int:track_id>/', views.start_interview, name='start_interview'),
    path('session/<int:session_id>/', views.interview_session, name='interview_session'),
    path('session/<int:session_id>/submit/<int:problem_id>/', views.submit_interview_problem, name='submit_interview_problem'),
    path('session/<int:session_id>/finish/', views.finish_interview, name='finish_interview'),
    path('session/<int:session_id>/report/', views.interview_report, name='interview_report'),
]


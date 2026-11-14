from django.urls import path
from .consumers import DuelConsumer
websocket_urlpatterns = [path('ws/duel/<str:invite_code>/', DuelConsumer.as_asgi())]

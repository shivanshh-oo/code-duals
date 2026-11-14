from channels.generic.websocket import JsonWebsocketConsumer
from asgiref.sync import async_to_sync
from .models import Participant


class DuelConsumer(JsonWebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        code = self.scope['url_route']['kwargs']['invite_code']
        if not user.is_authenticated or not Participant.objects.filter(user=user, match__invite_code=code).exists():
            self.close(code=4403)
            return
        self.room = f'duel_{code}'
        async_to_sync(self.channel_layer.group_add)(self.room, self.channel_name)
        self.accept()

    def disconnect(self, code):
        if hasattr(self, 'room'):
            async_to_sync(self.channel_layer.group_discard)(self.room, self.channel_name)

    def duel_event(self, event):
        self.send_json({'event': event['event']})

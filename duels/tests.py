from django.test import TestCase, TransactionTestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Match, Participant, Friendship
from problems.models import Problem, TestCase as ProblemTest
from .matching import WaitingList
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from .routing import websocket_urlpatterns
from .views import broadcast


class DuelFlowTests(TestCase):
    def setUp(self):
        WaitingList._waiting.clear()
        self.clients = []
        for name in ['alice', 'bob', 'outsider']:
            user = User.objects.create_user(name, password='test-password')
            user.profile.placement_done = True
            user.profile.save()
            client = Client()
            client.force_login(user)
            self.clients.append(client)
        self.problem = Problem.objects.create(title='Echo', statement='Echo input', category='DSA', difficulty='Easy')
        ProblemTest.objects.create(problem=self.problem, input='hi', expected_output='hi')

    def test_queue_submit_finish(self):
        a, b, outsider = self.clients
        for client in [a, b]:
            self.assertEqual(client.post('/duels/quick-match/join/', {'difficulty': 'Easy'}).status_code, 200)
        match_id = a.get('/duels/quick-match/poll/').json()['match_id']
        self.assertEqual(b.get('/duels/quick-match/poll/').json()['match_id'], match_id)
        self.assertEqual(a.get(f'/duels/match/{match_id}/').status_code, 200)
        self.assertEqual(outsider.get(f'/duels/match-status/{match_id}/').status_code, 404)
        response = a.post(f'/duels/match/{match_id}/submit/{self.problem.pk}/', {'code': 'print(input())'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verdict'], 'Accepted')
        Match.objects.filter(pk=match_id).update(ends_at=timezone.now())
        self.assertEqual(a.get(f'/duels/match-status/{match_id}/').json()['status'], 'finished')
        self.assertGreater(Participant.objects.get(match_id=match_id, user__username='alice').rating_change, 0)
        self.assertEqual(a.get(f'/duels/match/{match_id}/result/').status_code, 200)

    def test_private_and_export(self):
        a, b, outsider = self.clients
        room = a.post('/duels/create-match/', {'difficulty': 'Easy', 'duration': 10}).json()
        url = '/duels/join/' + room['invite_code'] + '/'
        self.assertEqual(b.post(url).status_code, 302)
        self.assertEqual(outsider.post(url).status_code, 400)
        for client in [a, b]:
            self.assertEqual(client.post(f"/duels/match/{room['match_id']}/ready/").status_code, 302)
        self.assertEqual(Match.objects.get(pk=room['match_id']).status, 'active')
        self.assertIn('attachment', a.get('/duels/leaderboard/export/')['Content-Disposition'])

    def test_placement_and_practice_with_csrf(self):
        user = User.objects.get(username='alice')
        user.profile.placement_done = False
        user.profile.save()
        self.problem.is_placement = True
        self.problem.save()
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.get('/accounts/placement/').status_code, 200)
        token = client.cookies['csrftoken'].value
        response = client.post('/accounts/placement/submit/',
                               {f'code_{self.problem.pk}': 'print(input())'},
                               HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['score'], 1)
        self.assertEqual(response.json()['rating'], 2000)
        response = client.post(f'/duels/practice/{self.problem.pk}/submit/',
                               {'code': 'print(input())'}, HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['verdict'], 'Accepted')

    def test_social_progress_and_history_pages(self):
        a, b, _ = self.clients
        self.assertEqual(a.post('/duels/friends/add/', {'username': 'bob'}).status_code, 302)
        relation = Friendship.objects.get(sender__username='alice', receiver__username='bob')
        self.assertEqual(b.post(f'/duels/friends/accept/{relation.pk}/').status_code, 302)
        self.assertEqual(a.get('/duels/friends/').status_code, 200)
        self.assertEqual(a.get('/duels/daily/').status_code, 200)
        self.assertEqual(a.get('/duels/submissions/').status_code, 200)
        self.assertEqual(a.get('/duels/history/').status_code, 200)
        self.assertEqual(b.get('/duels/notifications/').status_code, 200)


class DuelSocketTests(TransactionTestCase):
    def test_participant_events_and_outsider_rejection(self):
        player = User.objects.create_user('socket-player')
        outsider = User.objects.create_user('socket-outsider')
        match = Match.objects.create(is_private=True)
        Participant.objects.create(match=match, user=player)

        async def check_connections():
            router = URLRouter(websocket_urlpatterns)
            allowed = WebsocketCommunicator(router, f'/ws/duel/{match.invite_code}/')
            allowed.scope['user'] = player
            connected, _ = await allowed.connect()
            self.assertTrue(connected)
            denied = WebsocketCommunicator(router, f'/ws/duel/{match.invite_code}/')
            denied.scope['user'] = outsider
            connected, code = await denied.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4403)
            from channels.db import database_sync_to_async
            for event in ['player_joined', 'player_ready', 'match_started',
                          'opponent_progress', 'match_finished']:
                await database_sync_to_async(broadcast)(match, event)
                self.assertEqual(await allowed.receive_json_from(), {'event': event})
            await allowed.disconnect()
            await denied.disconnect()

        async_to_sync(check_connections)()

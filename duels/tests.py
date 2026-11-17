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

    def test_2v2_lobby_teams_and_scoring(self):
        users = []
        clients = []
        for name in ['p1', 'p2', 'p3', 'p4']:
            u = User.objects.create_user(name, password='pwd')
            u.profile.placement_done = True
            u.profile.save()
            c = Client()
            c.force_login(u)
            users.append(u)
            clients.append(c)

        c1, c2, c3, c4 = clients
        # 1. Host creates 2v2 match
        resp = c1.post('/duels/create-match/', {'difficulty': 'Easy', 'duration': 20, 'match_type': '2v2'}).json()
        match_id = resp['match_id']
        code = resp['invite_code']
        self.assertEqual(resp['match_type'], '2v2')

        # 2. Other 3 players join via invite
        join_url = f'/duels/join/{code}/'
        for c in [c2, c3, c4]:
            self.assertEqual(c.post(join_url).status_code, 302)

        m = Match.objects.get(pk=match_id)
        self.assertEqual(m.participants.count(), 4)

        # 3. Switch team test
        self.assertEqual(c2.post(f'/duels/match/{match_id}/switch-team/', {'team': 'team_b'}).status_code, 200)
        p2 = Participant.objects.get(match=m, user=users[1])
        self.assertEqual(p2.team, 'team_b')

        # Balance teams: p1, p3 in team_a; p2, p4 in team_b
        Participant.objects.filter(match=m, user=users[0]).update(team='team_a')
        Participant.objects.filter(match=m, user=users[1]).update(team='team_b')
        Participant.objects.filter(match=m, user=users[2]).update(team='team_a')
        Participant.objects.filter(match=m, user=users[3]).update(team='team_b')

        # 4. Ready up all 4 players
        for c in [c1, c2, c3, c4]:
            self.assertEqual(c.post(f'/duels/match/{match_id}/ready/').status_code, 302)

        m.refresh_from_db()
        self.assertEqual(m.status, 'active')

        # 5. Team A solves a problem
        sub_resp = c1.post(f'/duels/match/{match_id}/submit/{self.problem.pk}/', {'code': 'print(input())'})
        self.assertEqual(sub_resp.json()['verdict'], 'Accepted')

        # 6. Check match status API for 2v2
        status_data = c1.get(f'/duels/match-status/{match_id}/').json()
        self.assertEqual(status_data['match_type'], '2v2')
        self.assertEqual(status_data['my_team_solved'], 1)
        self.assertEqual(status_data['opp_team_solved'], 0)

        # Finish match & check rating settlement
        from .views import _finish_match
        _finish_match(m)
        m.refresh_from_db()
        self.assertEqual(m.status, 'finished')
        # Winning team (team A) should gain rating
        self.assertGreater(Participant.objects.get(match=m, user=users[0]).rating_change, 0)


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

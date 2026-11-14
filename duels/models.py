import uuid
from django.db import models
from django.contrib.auth.models import User
from problems.models import Problem


class Match(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('active', 'Active'),
        ('finished', 'Finished'),
    ]
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    invite_code = models.CharField(max_length=20, unique=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='waiting')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Medium')
    duration_minutes = models.IntegerField(default=30)
    started_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    winner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_matches')
    is_private = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    rematch_of = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.invite_code:
            self.invite_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Match {self.invite_code} ({self.status})'


class MatchProblem(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='match_problems')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('match', 'problem')

    def __str__(self):
        return f'{self.match.invite_code} - {self.problem.title}'


class Participant(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='participations')
    score = models.FloatField(default=0)
    problems_solved = models.IntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)
    rating_change = models.IntegerField(default=0)
    is_ready = models.BooleanField(default=False)
    abandoned = models.BooleanField(default=False)

    class Meta:
        unique_together = ('match', 'user')

    def __str__(self):
        return f'{self.user.username} in {self.match.invite_code}'


class Submission(models.Model):
    VERDICT_CHOICES = [
        ('Accepted', 'Accepted'),
        ('Wrong Answer', 'Wrong Answer'),
        ('Time Limit', 'Time Limit Exceeded'),
        ('Error', 'Runtime Error'),
    ]

    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES)
    tests_passed = models.IntegerField(default=0)
    tests_total = models.IntegerField(default=0)
    time_taken = models.FloatField(default=0, help_text='Seconds since match start')
    submitted_at = models.DateTimeField(auto_now_add=True)
    runtime_ms = models.PositiveIntegerField(default=0)
    similarity_percent = models.PositiveSmallIntegerField(default=0)
    is_flagged = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.participant.user.username} - {self.problem.title}: {self.verdict}'


class Friendship(models.Model):
    STATUS = [('pending', 'Pending'), ('accepted', 'Accepted')]
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_sent')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_received')
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['sender', 'receiver'], name='unique_friend_request')]


class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duel_notifications')
    message = models.CharField(max_length=250)
    url = models.CharField(max_length=250, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Achievement(models.Model):
    code = models.CharField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=250)
    icon = models.CharField(max_length=20, default='★')
    xp_reward = models.PositiveIntegerField(default=100)


class UserAchievement(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'achievement'], name='unique_user_achievement')]

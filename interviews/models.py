from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from problems.models import Problem
import uuid


class AIInterview(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_interviews')
    category = models.CharField(max_length=40)
    question = models.TextField()
    turns = models.JSONField(default=list)
    revision = models.PositiveIntegerField(default=0)
    report = models.JSONField(default=dict)
    xp_awarded = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class InterviewTrack(models.Model):
    DIFFICULTY_CHOICES = [
        ('Entry', 'Entry Level / Junior'),
        ('Mid', 'Mid-Level SWE'),
        ('Senior', 'Senior SWE'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    target_role = models.CharField(max_length=100, help_text='e.g. Backend Engineer, Systems SWE')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Mid')
    description = models.TextField()
    time_limit_minutes = models.IntegerField(default=45)
    problems = models.ManyToManyField(Problem, through='TrackProblem', related_name='interview_tracks')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.title} ({self.difficulty})'


class TrackProblem(models.Model):
    track = models.ForeignKey(InterviewTrack, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    phase_label = models.CharField(max_length=60, default='Core Challenge')  # e.g. Warm-up, Core Problem, Optimization

    class Meta:
        ordering = ['order']
        unique_together = ('track', 'problem')

    def __str__(self):
        return f'{self.track.title} - Step {self.order}: {self.problem.title}'


class InterviewSession(models.Model):
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='interview_sessions')
    track = models.ForeignKey(InterviewTrack, on_delete=models.CASCADE, related_name='sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    total_score = models.FloatField(default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    tests_passed_ratio = models.FloatField(default=0, help_text='Percentage of total test cases passed (0.0 to 1.0)')

    def __str__(self):
        return f'{self.user.username} - {self.track.title} ({self.status})'


class InterviewSubmission(models.Model):
    VERDICT_CHOICES = [
        ('Accepted', 'Accepted'),
        ('Wrong Answer', 'Wrong Answer'),
        ('Time Limit', 'Time Limit Exceeded'),
        ('Error', 'Runtime Error'),
    ]

    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    code = models.TextField()
    verdict = models.CharField(max_length=20, choices=VERDICT_CHOICES)
    tests_passed = models.IntegerField(default=0)
    tests_total = models.IntegerField(default=0)
    time_taken = models.FloatField(default=0, help_text='Seconds since interview start')
    runtime_ms = models.PositiveIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.session.user.username} [{self.session.track.title}] - {self.problem.title}: {self.verdict}'

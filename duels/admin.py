from django.contrib import admin
from .models import Match, MatchProblem, Participant, Submission


class MatchProblemInline(admin.TabularInline):
    model = MatchProblem
    extra = 1


class ParticipantInline(admin.TabularInline):
    model = Participant
    extra = 0


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('invite_code', 'status', 'difficulty', 'duration_minutes', 'winner', 'created_at')
    list_filter = ('status', 'difficulty')
    inlines = [MatchProblemInline, ParticipantInline]


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('participant', 'problem', 'verdict', 'tests_passed', 'tests_total', 'submitted_at')
    list_filter = ('verdict',)

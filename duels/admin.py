from django.contrib import admin
from .models import (Match, MatchProblem, Participant, Submission, Friendship,
                     Notification, Achievement, UserAchievement)


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
    list_display = ('participant', 'problem', 'verdict', 'tests_passed', 'tests_total', 'is_flagged', 'similarity_percent', 'submitted_at')
    list_filter = ('verdict', 'is_flagged')
    search_fields = ('participant__user__username', 'problem__title', 'code')


admin.site.register(Friendship)
admin.site.register(Notification)
admin.site.register(Achievement)
admin.site.register(UserAchievement)
admin.site.site_header = 'CodeDuels Control Center'
admin.site.site_title = 'CodeDuels Admin'

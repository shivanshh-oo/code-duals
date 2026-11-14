from django.contrib import admin
from .models import Problem, TestCase, Solution


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 2


class SolutionInline(admin.StackedInline):
    model = Solution
    extra = 0


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'difficulty', 'difficulty_rating', 'is_placement', 'is_draft')
    list_filter = ('category', 'difficulty', 'is_placement', 'is_draft')
    search_fields = ('title',)
    inlines = [TestCaseInline, SolutionInline]


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('problem', 'is_sample')
    list_filter = ('is_sample',)


@admin.register(Solution)
class SolutionAdmin(admin.ModelAdmin):
    list_display = ('problem',)

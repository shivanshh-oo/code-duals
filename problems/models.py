from django.db import models


class Problem(models.Model):
    CATEGORY_CHOICES = [
        ('DSA', 'Data Structures & Algorithms'),
        ('Web Dev', 'Web Development'),
        ('AI-ML', 'AI & Machine Learning'),
    ]
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    title = models.CharField(max_length=200)
    statement = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES)
    difficulty_rating = models.IntegerField(default=1000, help_text='Rating 800-2000')
    time_limit_sec = models.IntegerField(default=5)
    is_placement = models.BooleanField(default=False)
    is_draft = models.BooleanField(default=False, help_text='Drafts are hidden from players')
    source_url = models.URLField(blank=True, null=True, help_text='Link to original source')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.title} ({self.difficulty})'

    class Meta:
        ordering = ['difficulty_rating']


class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='test_cases')
    input = models.TextField()
    expected_output = models.TextField()
    is_sample = models.BooleanField(default=False, help_text='Shown to users')

    def __str__(self):
        return f'TestCase for {self.problem.title} (sample={self.is_sample})'


class Solution(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE, related_name='solution')
    explanation = models.TextField()
    reference_code = models.TextField()

    def __str__(self):
        return f'Solution for {self.problem.title}'

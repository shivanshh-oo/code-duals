from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'placement_done', 'is_setter')
    list_filter = ('placement_done', 'is_setter')

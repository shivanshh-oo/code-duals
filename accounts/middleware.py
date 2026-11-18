from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.db.models import F


class PlacementRequiredMiddleware:
    """Redirect authenticated users who haven't done placement to the placement page."""

    EXEMPT_URLS = [
        '/problems/',
        '/interview/',
        '/interviews/',
        '/ai/',
        '/accounts/placement/',
        '/accounts/logout/',
        '/accounts/login/',
        '/accounts/register/',
        '/accounts/google/',
        '/accounts/social/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            profile = request.user.profile
            today = timezone.localdate()
            if profile.last_active_date != today:
                profile.login_streak = profile.login_streak + 1 if profile.last_active_date == today - timedelta(days=1) else 1
                profile.last_active_date = today
                type(profile).objects.filter(pk=profile.pk).exclude(last_active_date=today).update(
                    login_streak=profile.login_streak, last_active_date=today, xp=F('xp') + 10)
                profile.refresh_from_db()
        if (request.user.is_authenticated
                and hasattr(request.user, 'profile')
                and not request.user.profile.placement_done
                and not any(request.path.startswith(url) for url in self.EXEMPT_URLS)):
            return redirect('placement')
        return self.get_response(request)

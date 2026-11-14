from django.shortcuts import redirect
from django.urls import reverse


class PlacementRequiredMiddleware:
    """Redirect authenticated users who haven't done placement to the placement page."""

    EXEMPT_URLS = [
        '/accounts/placement/',
        '/accounts/logout/',
        '/accounts/login/',
        '/accounts/register/',
        '/admin/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.user.is_authenticated
                and hasattr(request.user, 'profile')
                and not request.user.profile.placement_done
                and not any(request.path.startswith(url) for url in self.EXEMPT_URLS)):
            return redirect('placement')
        return self.get_response(request)

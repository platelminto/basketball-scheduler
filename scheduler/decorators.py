from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse


def api_login_required(view_func):
    """
    Decorator for API views that require authentication.
    Returns JSON response with 401 status for unauthenticated requests.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Authentication required',
                'login_url': reverse('scheduler:login')
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def schedule_app_login_required(view_func):
    """
    Decorator for React app views that require authentication.
    Renders the React app which will handle login redirect internally.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Always render the React app - React will handle auth check and redirect
        return view_func(request, *args, **kwargs)
    return wrapper


def public_or_authenticated(view_func):
    """
    Decorator that allows both public and authenticated access.
    Useful for views that have different behavior based on auth status.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Always allow access, but view can check request.user.is_authenticated
        return view_func(request, *args, **kwargs)
    return wrapper


# List of API endpoints that should remain public
PUBLIC_API_ENDPOINTS = [
    'scheduler:public_schedule_api',
    'scheduler:team_calendar_export',
    'scheduler:season_standings_api',
    'scheduler:login',
    'scheduler:logout', 
    'scheduler:auth_status',
    'scheduler:csrf_token',
]


def is_public_endpoint(request):
    """Check if the current request is for a public endpoint"""
    from django.urls import resolve, reverse, NoReverseMatch
    
    try:
        # Get the URL name for the current request
        resolved = resolve(request.path)
        url_name = f"{resolved.namespace}:{resolved.url_name}" if resolved.namespace else resolved.url_name
        
        return url_name in PUBLIC_API_ENDPOINTS
    except:
        return False
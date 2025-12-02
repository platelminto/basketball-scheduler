import json
import logging
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.views.decorators.http import require_http_methods
from django.middleware.csrf import get_token
from django.conf import settings

logger = logging.getLogger(__name__)


@ensure_csrf_cookie
def get_csrf_token(request):
    """Get CSRF token for frontend"""
    token = get_token(request)
    logger.info(f"CSRF token requested - Origin: {request.headers.get('Origin', 'none')}, "
                f"Referer: {request.headers.get('Referer', 'none')}, "
                f"Host: {request.headers.get('Host', 'none')}")
    logger.info(f"CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}")
    return JsonResponse({'csrfToken': token})


@csrf_protect
@require_http_methods(["POST"])
def login_view(request):
    """Handle user login via JSON API"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'error': 'Username and password are required'
            }, status=400)
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_active:
            login(request, user)
            return JsonResponse({
                'success': True,
                'user': {
                    'username': user.username,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid username or password'
            }, status=401)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.exception("Error during login")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred during login'
        }, status=500)


@require_http_methods(["POST"])
def logout_view(request):
    """Handle user logout"""
    logout(request)
    return JsonResponse({'success': True})


def auth_status(request):
    """Check if user is authenticated and return user info"""
    if request.user.is_authenticated:
        return JsonResponse({
            'authenticated': True,
            'user': {
                'username': request.user.username,
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser
            }
        })
    else:
        return JsonResponse({'authenticated': False})


@login_required
def protected_test(request):
    """Test endpoint to verify authentication is working"""
    return JsonResponse({
        'message': 'You are authenticated!',
        'user': request.user.username
    })
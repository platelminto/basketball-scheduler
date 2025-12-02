import logging
from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware

logger = logging.getLogger(__name__)


class CSRFDebugMiddleware(CsrfViewMiddleware):
    """Extended CSRF middleware that logs detailed debug info on failures."""

    def _reject(self, request, reason):
        logger.warning(
            f"CSRF REJECTED - Reason: {reason}\n"
            f"  Path: {request.path}\n"
            f"  Method: {request.method}\n"
            f"  Origin: {request.headers.get('Origin', 'none')}\n"
            f"  Referer: {request.headers.get('Referer', 'none')}\n"
            f"  Host: {request.headers.get('Host', 'none')}\n"
            f"  X-CSRFToken header: {'present' if request.headers.get('X-CSRFToken') else 'missing'}\n"
            f"  csrftoken cookie: {'present' if request.COOKIES.get('csrftoken') else 'missing'}\n"
            f"  CSRF_TRUSTED_ORIGINS: {settings.CSRF_TRUSTED_ORIGINS}\n"
            f"  CSRF_COOKIE_SECURE: {getattr(settings, 'CSRF_COOKIE_SECURE', False)}\n"
            f"  DEBUG: {settings.DEBUG}"
        )
        return super()._reject(request, reason)

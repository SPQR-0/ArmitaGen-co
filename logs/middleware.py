from .models import UserActivity
from django.utils import timezone

class UserActivityMiddleware:
    """
    Logs every page/API request as a UserActivity.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith('/admin'):
            UserActivity.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key,
                action_type='page_view',
                severity='info',
                description=f'Visited {request.path}',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                device_type=detect_device_type(request),
                browser=detect_browser(request),
                os=detect_os(request),
                metadata={
                    'method': request.method,
                    'status_code': response.status_code,
                    'timestamp': timezone.now().isoformat()
                }
            )
        return response

# Helpers: reuse your existing functions from signals.py
from .signals import get_client_ip, detect_device_type, detect_browser, detect_os


class ErrorLoggingMiddleware:
    """
    Catches unhandled exceptions and logs them.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
            from .models import ErrorLog
            import traceback

            ErrorLog.objects.create(
                error_type='server',
                error_message=str(e),
                stack_trace=traceback.format_exc(),
                user=request.user if request.user.is_authenticated else None,
                url=request.path,
                request_method=request.method,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            raise

import traceback
from django.db import models
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from .models import UserActivity, ErrorLog
from .utils import log_activity, log_error
from .signals import get_client_ip, detect_device_type, detect_browser, detect_os


# 1) Error Logging Middleware
class ErrorLoggingMiddleware:
    """
    Logs unhandled exceptions into ErrorLog model.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as e:
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


# 2) Session Tracking + Guest Migration Middleware
class UserSessionTrackingMiddleware(MiddlewareMixin):
    """
    Ensures a session key exists for guest users and migrates guest activities after authentication.
    """

    def process_request(self, request):
        # Ensure session key exists
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key
        request._guest_session_key = session_key

        # Migrate guest activities after login
        if request.user.is_authenticated:
            if request.session.get('_migrate_guest_activities'):
                self._migrate_guest_activities(session_key, request.user)
                del request.session['_migrate_guest_activities']

        return None

    def _migrate_guest_activities(self, session_key, user):
        guest_activities = UserActivity.objects.filter(
            session_key=session_key,
            user__isnull=True
        )

        updated_count = guest_activities.update(user=user)

        if updated_count > 0:
            log_activity(
                user=user,
                action_type='other',
                description=f'{updated_count} فعالیت مهمان به حساب کاربر لینک شد',
                severity='info',
                metadata={
                    'migrated_activities': updated_count,
                    'old_session_key': session_key
                }
            )


# 3) Main User Activity Middleware (page views + server errors)
class ActivityTrackingMiddleware(MiddlewareMixin):
    """
    Logs page views (GET 200) and exceptions.
    """

    EXCLUDE_PATHS = [
        '/admin/',
        '/admin/jsi18n/',
        '/static/',
        '/media/',
        '/__debug__/',
    ]

    def process_request(self, request):
        request._activity_start_time = timezone.now()
        return None

    def process_response(self, request, response):
        # Ignore excluded paths
        if any(request.path.startswith(path) for path in self.EXCLUDE_PATHS):
            return response

        # Ignore AJAX API calls
        if request.path.startswith('/council/api/'):
            return response

        # Log only successful GET page views
        if request.method == 'GET' and response.status_code == 200:
            self._log_page_view(request, response)

        return response

    def process_exception(self, request, exception):
        user = request.user if request.user.is_authenticated else None

        log_error(
            error_type='server',
            error_message=str(exception),
            user=user,
            request=request,
            view_name=request.resolver_match.view_name if request.resolver_match else None,
            stack_trace=traceback.format_exc()
        )
        return None

    # -----------------------
    # Helpers
    # -----------------------
    def _log_page_view(self, request, response):
        user = request.user if request.user.is_authenticated else None
        session_key = None if user else request.session.session_key

        path = request.path
        description = self._get_page_description(path)

        log_activity(
            user=user,
            session_key=session_key,
            action_type='page_view',
            description=description,
            severity='info',
            request=request,
            metadata={
                'path': path,
                'method': request.method,
                'status_code': response.status_code,
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': get_client_ip(request),
                'device_type': detect_device_type(request),
                'browser': detect_browser(request),
                'os': detect_os(request),
                'timestamp': timezone.now().isoformat(),
            }
        )

    def _get_page_description(self, path):
        descriptions = {
            '/': 'بازدید صفحه اصلی',
            '/council/consultation/': 'بازدید صفحه رزرو مشاوره - مرحله 1',
            '/council/select-time/': 'بازدید صفحه انتخاب زمان - مرحله 2',
            '/council/verify-phone/': 'بازدید صفحه تایید شماره - مرحله 3',
        }

        if path in descriptions:
            return descriptions[path]

        if '/council/review/' in path:
            return 'بازدید صفحه بررسی رزرو - مرحله 4'
        if '/council/receipt/' in path:
            return 'بازدید صفحه رسید نهایی'

        return f'بازدید صفحه {path}'

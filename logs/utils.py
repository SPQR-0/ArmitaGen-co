import traceback

from django.contrib.contenttypes.models import ContentType

from .models import UserActivity, ErrorLog, PaymentLog


def log_activity(user=None, action_type='other', description='', severity='info',
                 related_object=None, metadata=None, request=None, session_key=None):
    """
    Quick helper to log user activity

    Usage:
        log_activity(
            user=request.user,
            action_type='page_view',
            description='User viewed homepage',
            metadata={'page': 'home'},
            request=request
        )
    """
    activity_data = {
        'user': user,
        'session_key': session_key,
        'action_type': action_type,
        'severity': severity,
        'description': description,
        'metadata': metadata or {}
    }

    # Add related object if provided
    if related_object:
        activity_data['content_type'] = ContentType.objects.get_for_model(related_object)
        activity_data['object_id'] = related_object.pk

    # Extract request info if provided
    if request:
        from .signals import get_client_ip, detect_device_type, detect_browser, detect_os

        activity_data['ip_address'] = get_client_ip(request)
        activity_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        activity_data['device_type'] = detect_device_type(request)
        activity_data['browser'] = detect_browser(request)
        activity_data['os'] = detect_os(request)

    return UserActivity.objects.create(**activity_data)


def log_error(error_type='other', error_message='', user=None, request=None,
              view_name=None, stack_trace=None):
    """
    Quick helper to log errors

    Usage:
        try:
            # some code
        except Exception as e:
            log_error(
                error_type='database',
                error_message=str(e),
                user=request.user,
                request=request,
                stack_trace=traceback.format_exc()
            )
    """
    error_data = {
        'error_type': error_type,
        'error_message': error_message,
        'user': user,
        'view_name': view_name,
        'stack_trace': stack_trace or traceback.format_exc()
    }

    if request:
        from .signals import get_client_ip

        error_data['url'] = request.build_absolute_uri()
        error_data['request_method'] = request.method
        error_data['ip_address'] = get_client_ip(request)
        error_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')

        # Sanitize request data (remove sensitive info)
        request_data = {}
        if request.method == 'POST':
            request_data = {k: v for k, v in request.POST.items() if k not in ['password', 'csrfmiddlewaretoken']}
        elif request.method == 'GET':
            request_data = dict(request.GET.items())

        error_data['request_data'] = request_data

    return ErrorLog.objects.create(**error_data)


def log_payment_transaction(payment, reservation, user, transaction_type,
                            gateway_response=None, request_data=None, ip_address=None):
    """
    Log payment transaction details (safe: doesn't assume Payment.gateway exists).
    """
    # ۱. اول تلاش به‌دست آوردن نام درگاه از gateway_response (اگر ارائه شده)
    gateway_from_response = None
    if isinstance(gateway_response, dict):
        # بعضی درگاه‌ها کلید متفاوت دارند؛ اینجا چند کلید احتمالی رو چک می‌کنیم
        gateway_from_response = (
            gateway_response.get('gateway')
            or gateway_response.get('provider')
            or gateway_response.get('payment_gateway')
        )

    # ۲. سپس تلاش می‌کنیم از مدل payment بخوانیم در صورت وجود (با getattr امن)
    gateway_from_payment = getattr(payment, 'gateway', None) or getattr(payment, 'gateway_name', None)

    # ۳. نهایی: اولویت: gateway_response -> payment attribute -> مقدار پیش‌فرض
    gateway_name = gateway_from_response or gateway_from_payment or "zarinpal"

    return PaymentLog.objects.create(
        payment=payment,
        reservation=reservation,
        user=user,
        transaction_type=transaction_type,
        amount=payment.amount,
        gateway_name=gateway_name,
        gateway_status=(gateway_response.get('status') if isinstance(gateway_response, dict) else None),
        gateway_message=(gateway_response.get('message') if isinstance(gateway_response, dict) else None),
        authority=getattr(payment, 'reference_code', None),
        ref_id=getattr(payment, 'tracking_code', None),
        request_data=request_data or {},
        response_data=gateway_response or {},
        ip_address=ip_address
    )


class ActivityLogger:
    """
    Context manager for automatic activity logging

    Usage:
        with ActivityLogger(user, 'file_upload', 'User uploaded file') as logger:
            # do something
            logger.metadata['file_name'] = 'test.pdf'
    """

    def __init__(self, user, action_type, description, severity='info', request=None):
        self.user = user
        self.action_type = action_type
        self.description = description
        self.severity = severity
        self.request = request
        self.metadata = {}
        self.activity = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.severity = 'error'
            self.metadata['error'] = str(exc_val)

        self.activity = log_activity(
            user=self.user,
            action_type=self.action_type,
            description=self.description,
            severity=self.severity,
            metadata=self.metadata,
            request=self.request
        )

        return False  # Don't suppress exceptions

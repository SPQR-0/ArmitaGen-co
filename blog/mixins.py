from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Prefetch
from django.utils import timezone

from .models import PostSection, Media


class PublishedPostMixin:
    """Mixin to show only published posts"""

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(
            status='published',
            published_at__lte=timezone.now()
        )


class OptimizedQuerysetMixin:
    """Mixin for query optimization"""

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.select_related('author').prefetch_related(
            Prefetch('sections', queryset=PostSection.objects.order_by('order')),
            Prefetch('media', queryset=Media.objects.all())
        )


class AdminOnlyMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to restrict access to admins only"""

    login_url = '/admin/login/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

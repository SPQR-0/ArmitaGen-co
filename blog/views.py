from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView

from .mixins import *
from .models import Post
from .models import PostLike


def get_client_ip(request):
    """Getting the user's real IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class PostListView(PublishedPostMixin, OptimizedQuerysetMixin, ListView):
    """List of all published posts with filtering"""

    model = Post
    template_name = 'blog/blog-list-sidebar.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by author
        author = self.request.GET.get('editor')
        if author:
            queryset = queryset.filter(author__username=author)

        # Filter by year
        year = self.request.GET.get('year')
        if year and year.isdigit():
            queryset = queryset.filter(published_at__year=year)

        # Filter by month
        month = self.request.GET.get('month')
        if month and month.isdigit():
            queryset = queryset.filter(published_at__month=month)

        # Ordering
        sort = self.request.GET.get('sort', '-published_at')
        allowed_sorts = ['-published_at', 'published_at', 'title', '-title', '-created_at']
        if sort in allowed_sorts:
            queryset = queryset.order_by(sort)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter params to context for display in template
        context['current_author'] = self.request.GET.get('author', '')
        context['current_year'] = self.request.GET.get('year', '')
        context['current_month'] = self.request.GET.get('month', '')
        context['current_sort'] = self.request.GET.get('sort', '-published_at')

        # Cache available years for 1 hour
        available_years = cache.get('blog_available_years')
        if available_years is None:
            available_years = list(
                Post.objects
                .filter(status='published')
                .dates('published_at', 'year', order='DESC')
            )
            cache.set('blog_available_years', available_years, 60 * 60)

        context['available_years'] = available_years

        return context


class PostDetailView(PublishedPostMixin, DetailView):
    """Display details of a single post"""

    model = Post
    template_name = 'blog/post_detail.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        """Optimized query with nested prefetch"""

        return (
            Post.objects
            .select_related('editor')
            .prefetch_related(
                'authors',
                Prefetch(
                    'sections',
                    queryset=PostSection.objects
                    .order_by('order')
                    .prefetch_related(
                        Prefetch(
                            'media',
                            queryset=Media.objects.order_by('created_at')
                        )
                    )
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['sections'] = self.object.sections.all()
        context['authors'] = self.object.authors.all()

        # Like info
        ip_address = get_client_ip(self.request)
        context['likes_count'] = self.object.get_likes_count()
        context['is_liked'] = self.object.is_liked_by_ip(ip_address)
        context['previous_post'] = (
            Post.objects
            .filter(
                status='published',
                published_at__lt=self.object.published_at
            )
            .order_by('-published_at')
            .only('title', 'slug')
            .first()
        )

        context['next_post'] = (
            Post.objects
            .filter(
                status='published',
                published_at__gt=self.object.published_at
            )
            .order_by('published_at')
            .only('title', 'slug')
            .first()
        )
        available_years = cache.get('blog_available_years')
        if available_years is None:
            available_years = list(
                Post.objects
                .filter(status='published')
                .dates('published_at', 'year', order='DESC')
            )
            cache.set('blog_available_years', available_years, 60 * 60)  # 1 hour

        context['available_years'] = available_years

        context['meta_title'] = self.object.title
        context['meta_description'] = self.object.meta_description or self.object.title
        context['meta_image'] = self.object.featured_image.url if self.object.featured_image else None
        context['canonical_url'] = self.request.build_absolute_uri(self.object.get_absolute_url())

        return context


class PostSearchView(PublishedPostMixin, OptimizedQuerysetMixin, ListView):
    model = Post
    template_name = 'blog/post_search.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        query = self.request.GET.get('q', '').strip()

        if query:
            # Search by title, meta description, section content, and authors
            queryset = queryset.filter(
                Q(title__icontains=query) |
                Q(meta_description__icontains=query) |
                Q(sections__content__icontains=query) |
                Q(authors__name__icontains=query) |
                Q(authors__bio__icontains=query)
            ).distinct()

        return queryset.order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        query = self.request.GET.get('q', '').strip()
        context['query'] = query
        context['result_count'] = self.get_queryset().count()

        return context


class PostArchiveView(PublishedPostMixin, OptimizedQuerysetMixin, ListView):
    """Post archives by year and month"""
    model = Post
    template_name = 'blog/post_archive.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()

        # Get the year from the URL
        year = self.kwargs.get('year')
        if year:
            queryset = queryset.filter(published_at__year=year)

        month = self.kwargs.get('month')
        if month:
            queryset = queryset.filter(published_at__month=month)

        return queryset.order_by('-published_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['year'] = self.kwargs.get('year')
        context['month'] = self.kwargs.get('month')

        if context['month']:
            persian_months = {
                1: 'فروردین', 2: 'اردیبهشت', 3: 'خرداد',
                4: 'تیر', 5: 'مرداد', 6: 'شهریور',
                7: 'مهر', 8: 'آبان', 9: 'آذر',
                10: 'دی', 11: 'بهمن', 12: 'اسفند'
            }
            context['month_name'] = f"ماه {context['month']}"

        context['available_years'] = Post.objects.filter(
            status='published'
        ).dates('published_at', 'year', order='DESC')

        return context


class PostPreviewView(AdminOnlyMixin, OptimizedQuerysetMixin, DetailView):
    """Post Preview (Admins Only)"""

    model = Post
    template_name = 'blog/post_preview.html'
    context_object_name = 'post'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        # Unlike the normal DetailView, this one gets all posts (even drafts)
        return Post.objects.select_related('author').prefetch_related(
            Prefetch('sections', queryset=PostSection.objects.order_by('order')),
            Prefetch('media', queryset=Media.objects.all())
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['is_preview'] = True
        context['sections'] = self.object.sections.all().order_by('order')

        return context


@method_decorator(csrf_exempt, name='dispatch')
class PostLikeView(View):

    def post(self, request, slug):
        try:
            post = Post.objects.get(slug=slug, status='published')
        except Post.DoesNotExist:
            return JsonResponse({'error': 'پست یافت نشد'}, status=404)

        ip_address = get_client_ip(request)

        like, created = PostLike.objects.get_or_create(
            post=post,
            ip_address=ip_address
        )

        if not created:

            like.delete()
            liked = False
        else:
            liked = True

        likes_count = post.get_likes_count()

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count
        })

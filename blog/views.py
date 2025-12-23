from django.contrib import messages
from django.db.models import Min, Max
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView
from django_ratelimit.decorators import ratelimit
from taggit.models import Tag

from blog.utils.jalali_filters import (
    filter_qs_by_jalali_year,
    filter_qs_by_jalali_month,
    jalali_month_choices, jalali_year_choices_from_min_max,
)
from .forms import CommentForm, ReplyForm
from .mixins import *
from .models import Post, PostLike, Comment
from .utils.comment_ip import get_or_create_commenter_ip


def get_client_ip(request):
    """Getting the user's real IP"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def real_ip(group, request):
    return request.META.get("REMOTE_ADDR")


class PostListView(PublishedPostMixin, OptimizedQuerysetMixin, ListView):
    """List of all published posts with filtering"""

    model = Post
    template_name = 'blog/post_list.html'
    context_object_name = 'posts'
    paginate_by = 5

    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(status='published', published_at__isnull=False)

        author = self.request.GET.get('author')
        if author:
            qs = qs.filter(authors__name=author)

        # Jalali year/month filters (minimal changes)
        year = self.request.GET.get('year')
        month = self.request.GET.get('month')

        if year and year.isdigit():
            jy = int(year)
            if month and month.isdigit():
                jm = int(month)
                if 1 <= jm <= 12:
                    qs = filter_qs_by_jalali_month(qs, jy, jm, field="published_at")
            else:
                qs = filter_qs_by_jalali_year(qs, jy, field="published_at")

        sort = self.request.GET.get('sort', '-published_at')
        allowed_sorts = {'-published_at', 'published_at', 'title', '-title', '-created_at', 'created_at'}
        if sort in allowed_sorts:
            qs = qs.order_by(sort)

        return qs.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['current_author'] = self.request.GET.get('author', '')
        context['current_year'] = self.request.GET.get('year', '')
        context['current_month'] = self.request.GET.get('month', '')
        context['current_sort'] = self.request.GET.get('sort', '-published_at')

        # months dropdown with Persian labels
        context['jalali_months'] = jalali_month_choices()

        # Jalali available years based on min/max published_at
        agg = (
            Post.objects
            .filter(status='published', published_at__isnull=False)
            .aggregate(
                min_dt=Min("published_at"),
                max_dt=Max("published_at"),
            )
        )

        available_years = jalali_year_choices_from_min_max(
            agg.get("min_dt"),
            agg.get("max_dt"),
        )

        context['available_years'] = available_years
        return context


class PostDetailView(PublishedPostMixin, DetailView):
    """Display details of a single post"""

    model = Post
    template_name = 'blog/post_detail.html'
    # template_name = 'blog/blog-details.html'
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

        # Comments
        context['comments'] = self.object.get_approved_comments()
        context['comments_count'] = self.object.get_approved_comments_count()
        context['comment_form'] = CommentForm()
        context['reply_form'] = ReplyForm()

        # Previous/Next posts
        context['previous_post'] = (
            Post.objects
            .filter(status='published', published_at__lt=self.object.published_at)
            .order_by('-published_at')
            .only('title', 'slug')
            .first()
        )

        context['next_post'] = (
            Post.objects
            .filter(status='published', published_at__gt=self.object.published_at)
            .order_by('published_at')
            .only('title', 'slug')
            .first()
        )

        # Related posts by tags (6 posts) - sorted by number of shared tags
        if self.object.tags.exists():
            # Get posts with shared tags and count the number of matching tags
            related_posts = (
                Post.objects
                .filter(tags__in=self.object.tags.all(), status='published')
                .exclude(pk=self.object.pk)
                .annotate(same_tags=Count('tags'))
                .distinct()
                .order_by('-same_tags', '-published_at')  # Sort by number of shared tags, then by date
                .select_related('editor')
                .prefetch_related('authors', 'tags')
                [:6]
            )
            context['related_posts'] = related_posts

        # SEO Meta
        context['meta_title'] = self.object.title
        context['meta_description'] = self.object.meta_description or self.object.title
        context['meta_image'] = self.object.featured_image.url if self.object.featured_image else None
        context['canonical_url'] = self.request.build_absolute_uri(self.object.get_absolute_url())

        return context


@method_decorator(
    ratelimit(key=real_ip, rate="5/d", method="POST", block=False),
    name="post",
)
class PostCommentView(View):
    """Handle comment submission"""

    def post(self, request, slug):
        if getattr(request, "limited", False):
            messages.error(
                request,
                "شما بیش از حد مجاز نظر ثبت کرده‌اید (حداکثر ۵ نظر در روز)."
            )
            return redirect("blog:post_detail", slug=slug)

        post = get_object_or_404(Post, slug=slug, status="published")

        ip = get_client_ip(request)
        commenter_ip = get_or_create_commenter_ip(ip)

        # Block check
        if commenter_ip.is_blocked:
            messages.error(request, "دسترسی شما به ثبت نظر توسط ادمین مسدود شده است.")
            return redirect("blog:post_detail", slug=slug)

        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.ip_address = ip
            comment.commenter_ip = commenter_ip
            comment.is_approved = False
            comment.save()

            messages.success(
                request,
                "نظر شما ثبت شد و پس از تایید ادمین نمایش داده خواهد شد."
            )
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)

        return redirect("blog:post_detail", slug=slug)


@method_decorator(
    ratelimit(key=real_ip, rate="5/d", method="POST", block=False),
    name="post",
)
class PostCommentReplyView(View):
    """Handle comment reply submission"""

    def post(self, request, slug, comment_id):
        if getattr(request, "limited", False):
            messages.error(
                request,
                "شما بیش از حد مجاز پاسخ ثبت کرده‌اید (حداکثر ۵ پاسخ در روز)."
            )
            return redirect("blog:post_detail", slug=slug)

        post = get_object_or_404(Post, slug=slug, status="published")
        parent_comment = get_object_or_404(
            Comment, id=comment_id, post=post, is_approved=True
        )

        ip = get_client_ip(request)
        commenter_ip = get_or_create_commenter_ip(ip)

        if commenter_ip.is_blocked:
            messages.error(request, "دسترسی شما به ثبت پاسخ توسط ادمین مسدود شده است.")
            return redirect("blog:post_detail", slug=slug)

        form = ReplyForm(request.POST)

        if form.is_valid():
            reply = form.save(commit=False)
            reply.post = post
            reply.parent = parent_comment
            reply.ip_address = ip
            reply.commenter_ip = commenter_ip
            reply.is_approved = False
            reply.save()

            messages.success(
                request,
                "پاسخ شما ثبت شد و پس از تایید ادمین نمایش داده خواهد شد."
            )
        else:
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, error)

        return redirect("blog:post_detail", slug=slug)


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
        is_liked = PostLike.objects.filter(post=post, ip_address=get_client_ip(request)).exists()

        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count,
            'is_liked': is_liked
        })


class PostsByTagView(PublishedPostMixin, OptimizedQuerysetMixin, ListView):
    model = Post
    template_name = 'blog/posts_by_tag.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs['slug'])
        return (
            Post.objects
            .filter(tags=self.tag, status='published')
            .select_related('editor')
            .prefetch_related('authors')
            .order_by('-published_at')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context

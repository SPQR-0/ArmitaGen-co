from django.urls import path

from . import views
from .views import PostLikeView

app_name = 'blog'

urlpatterns = [
    path('', views.PostListView.as_view(), name='post_list'),
    path('search/', views.PostSearchView.as_view(), name='post_search'),
    path('archive/<int:year>/', views.PostArchiveView.as_view(), name='post_archive_year'),
    path('archive/<int:year>/<int:month>/', views.PostArchiveView.as_view(), name='post_archive_month'),
    path('preview/<slug:slug>/', views.PostPreviewView.as_view(), name='post_preview'),
    path('<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('<slug:slug>/like/', PostLikeView.as_view(), name='post_like'),
    path('tags/<str:slug>/', views.PostsByTagView.as_view(), name='tag_posts'),
]

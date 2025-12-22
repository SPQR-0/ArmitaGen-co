from django.urls import path

from . import views

app_name = 'blog'

urlpatterns = [
    # Post URLs
    path('', views.PostListView.as_view(), name='post_list'),
    path('search/', views.PostSearchView.as_view(), name='post_search'),
    path('archive/<int:year>/', views.PostArchiveView.as_view(), name='post_archive_year'),
    path(
        'archive/<int:year>/<int:month>/',
        views.PostArchiveView.as_view(),
        name='post_archive_month'
    ),
    path('preview/<slug:slug>/', views.PostPreviewView.as_view(), name='post_preview'),
    path('tags/<str:slug>/', views.PostsByTagView.as_view(), name='tag_posts'),

    # Post Detail & Actions
    path('<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('<slug:slug>/like/', views.PostLikeView.as_view(), name='post_like'),
    # Comment URLs
    path('<slug:slug>/comment/', views.PostCommentView.as_view(), name='post_comment'),
    path(
        '<slug:slug>/comment/<int:comment_id>/reply/',
        views.PostCommentReplyView.as_view(),
        name='post_comment_reply'
    ),

]

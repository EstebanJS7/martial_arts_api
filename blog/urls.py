from django.urls import path
from .views import RatingView, BlogPostDetailView, BlogPostListView, CommentView

urlpatterns = [
    path('', BlogPostListView.as_view(), name='blogpost-list'),
    path('<int:pk>/', BlogPostDetailView.as_view(), name='blogpost-detail'),
    path('<int:pk>/comments/', CommentView.as_view(), name='comment-list-create'),
    path('<int:pk>/rate/', RatingView.as_view(), name='rating'),
]
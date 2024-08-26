from rest_framework import generics
from .models import BlogPost, Comment, Rating
from .serializers import BlogPostSerializer, CommentSerializer, RatingSerializer
from users.permissions import IsAuthorOrAdmin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

class BlogPostListView(generics.ListCreateAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer

class BlogPostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthorOrAdmin]

class BlogPostCreateView(generics.CreateAPIView):
    queryset = BlogPost.objects.all()
    serializer_class = BlogPostSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)        
    
class CommentView(generics.ListCreateAPIView):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Comment.objects.filter(blog_post_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, blog_post_id=self.kwargs['pk'])

class RatingView(generics.CreateAPIView):
    queryset = Rating.objects.all()
    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, blog_post_id=self.kwargs['pk'])

    def get_queryset(self):
        return Rating.objects.filter(blog_post_id=self.kwargs['pk'], user=self.request.user)
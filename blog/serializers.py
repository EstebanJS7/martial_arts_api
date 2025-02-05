from rest_framework import serializers
from .models import BlogPost, Comment, Rating

class CommentSerializer(serializers.ModelSerializer):
    # Puedes personalizar la representación del usuario, por ejemplo:
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user', 'content', 'created_at']

class RatingSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'user', 'score', 'created_at']

class BlogPostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    author = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'content',
            'author',
            'created_at',
            'comments',
            'ratings'
        ]
        read_only_fields = ['created_at', 'author']

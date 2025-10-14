from rest_framework import serializers
from .models import BlogPost, Comment, Rating

class CommentSerializer(serializers.ModelSerializer):
    # Información detallada del usuario
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Comment
        fields = ['id', 'user_id', 'user_name', 'user_email', 'content', 'created_at']

class RatingSerializer(serializers.ModelSerializer):
    # Información detallada del usuario
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Rating
        fields = ['id', 'user_id', 'user_name', 'user_email', 'score', 'created_at']

class BlogPostSerializer(serializers.ModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    ratings = RatingSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_email = serializers.CharField(source='author.email', read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    image = serializers.ImageField(
        max_length=None,
        use_url=True,
        allow_empty_file=False,
        required=False,
        help_text="Sube una imagen para el blog"
    )
    
    # Campos calculados
    total_comments = serializers.SerializerMethodField()
    total_ratings = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = BlogPost
        fields = [
            'id',
            'title',
            'content',
            'author_id',
            'author_name',
            'author_email',
            'created_at',
            'is_featured',
            'image',
            'comments',
            'ratings',
            'total_comments',
            'total_ratings',
            'average_rating'
        ]
        read_only_fields = ['created_at', 'author_id']
    
    def get_total_comments(self, obj):
        return obj.comments.count()
    
    def get_total_ratings(self, obj):
        return obj.ratings.count()
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        avg_rating = obj.ratings.aggregate(avg_rating=Avg('score'))['avg_rating']
        return round(avg_rating, 2) if avg_rating else 0

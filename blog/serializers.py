from rest_framework import serializers
from .models import BlogPost, Comment, Rating, Category, Tag

class CategorySerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'color', 'created_at', 'updated_at', 'posts_count']
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_posts_count(self, obj):
        return obj.posts.count()

class TagSerializer(serializers.ModelSerializer):
    posts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'color', 'created_at', 'posts_count']
        read_only_fields = ['slug', 'created_at']
    
    def get_posts_count(self, obj):
        return obj.posts.count()

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
    category = CategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    tags = TagSerializer(many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
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
            'category',
            'category_id',
            'tags',
            'tag_ids',
            'created_at',
            'updated_at',
            'is_featured',
            'image',
            'comments',
            'ratings',
            'total_comments',
            'total_ratings',
            'average_rating'
        ]
        read_only_fields = ['created_at', 'updated_at', 'author_id']
    
    def get_total_comments(self, obj):
        return obj.comments.count()
    
    def get_total_ratings(self, obj):
        return obj.ratings.count()
    
    def get_average_rating(self, obj):
        from django.db.models import Avg
        avg_rating = obj.ratings.aggregate(avg_rating=Avg('score'))['avg_rating']
        return round(avg_rating, 2) if avg_rating else 0
    
    def create(self, validated_data):
        # Extraer category_id y tag_ids
        category_id = validated_data.pop('category_id', None)
        tag_ids = validated_data.pop('tag_ids', [])
        
        # Crear el blog post
        blog_post = BlogPost.objects.create(**validated_data)
        
        # Asignar categoría si se proporciona
        if category_id:
            try:
                category = Category.objects.get(id=category_id)
                blog_post.category = category
                blog_post.save()
            except Category.DoesNotExist:
                pass
        
        # Asignar tags si se proporcionan
        if tag_ids:
            tags = Tag.objects.filter(id__in=tag_ids)
            blog_post.tags.set(tags)
        
        return blog_post
    
    def update(self, instance, validated_data):
        # Extraer category_id y tag_ids
        category_id = validated_data.pop('category_id', None)
        tag_ids = validated_data.pop('tag_ids', None)
        
        # Actualizar campos básicos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar categoría
        if category_id is not None:
            if category_id:
                try:
                    category = Category.objects.get(id=category_id)
                    instance.category = category
                except Category.DoesNotExist:
                    instance.category = None
            else:
                instance.category = None
        
        # Actualizar tags
        if tag_ids is not None:
            if tag_ids:
                tags = Tag.objects.filter(id__in=tag_ids)
                instance.tags.set(tags)
            else:
                instance.tags.clear()
        
        instance.save()
        return instance

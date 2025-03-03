from rest_framework import serializers
from .models import Resource, ResourceTag
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class ResourceTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceTag
        fields = ['id', 'name']

class ResourceAuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']

class ResourceListSerializer(serializers.ModelSerializer):
    author = ResourceAuthorSerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Resource
        fields = [
            'id', 'title', 'description', 'type', 'category', 'level',
            'thumbnail_url', 'created_at', 'author', 'views_count',
            'is_featured', 'is_premium'
        ]
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None

class ResourceDetailSerializer(serializers.ModelSerializer):
    author = ResourceAuthorSerializer(read_only=True)
    tags = ResourceTagSerializer(many=True, read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Resource
        fields = [
            'id', 'title', 'description', 'type', 'category', 'level',
            'url', 'file_url', 'thumbnail_url', 'file_size', 'duration',
            'created_at', 'updated_at', 'author', 'tags', 'views_count',
            'downloads_count', 'is_featured', 'is_premium'
        ]
        read_only_fields = ('created_at', 'updated_at', 'views_count', 'downloads_count')
    
    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return self.context['request'].build_absolute_uri(obj.thumbnail.url)
        return None
    
    def get_file_url(self, obj):
        if obj.file:
            return self.context['request'].build_absolute_uri(obj.file.url)
        return None

class ResourceCreateUpdateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=ResourceTag.objects.all(),
        many=True,
        required=False
    )
    
    class Meta:
        model = Resource
        exclude = ('author', 'created_at', 'updated_at', 'views_count', 'downloads_count')
    
    def create(self, validated_data):
        tags_data = validated_data.pop('tags', [])
        resource = Resource.objects.create(**validated_data)
        resource.tags.set(tags_data)
        return resource
    
    def update(self, instance, validated_data):
        tags_data = validated_data.pop('tags', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if tags_data is not None:
            instance.tags.set(tags_data)
            
        instance.save()
        return instance


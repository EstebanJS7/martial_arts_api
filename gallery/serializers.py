from rest_framework import serializers
from .models import Gallery, GalleryItem

class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ['id', 'title', 'description', 'created_at']
        read_only_fields = ['created_at']

class GalleryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryItem
        fields = ['id', 'gallery', 'media_type', 'image', 'video', 'description', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def validate(self, data):
        media_type = data.get('media_type')
        if media_type == 'image' and not data.get('image'):
            raise serializers.ValidationError("Image file is required when media_type is 'image'.")
        if media_type == 'video' and not data.get('video'):
            raise serializers.ValidationError("Video file is required when media_type is 'video'.")
        return data
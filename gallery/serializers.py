from rest_framework import serializers
from .models import Gallery, GalleryItem

class GallerySerializer(serializers.ModelSerializer):
    class Meta:
        model = Gallery
        fields = ['id', 'title', 'description', 'created_at']

class GalleryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryItem
        fields = ['id', 'gallery', 'media_type', 'image', 'video', 'description', 'uploaded_at']
        read_only_fields = ['uploaded_at']

    def validate(self, data):
        if data['media_type'] == 'image' and not data['image']:
            raise serializers.ValidationError("Image file is required when media_type is 'image'.")
        if data['media_type'] == 'video' and not data['video']:
            raise serializers.ValidationError("Video file is required when media_type is 'video'.")
        return data
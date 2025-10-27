from rest_framework import serializers
from .models import Gallery, GalleryItem

class GallerySerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    
    class Meta:
        model = Gallery
        fields = ['id', 'title', 'description', 'cover_image', 'created_at', 'items']
        read_only_fields = ['created_at']
    
    def get_items(self, obj):
        # Usar la relación inversa directamente
        items = obj.galleryitem_set.all().order_by('-uploaded_at')
        return GalleryItemSerializer(items, many=True, context=self.context).data

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
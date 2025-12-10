from django.contrib import admin
from .models import BlogPost, Comment, Rating, Category, Tag

# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'created_at', 'posts_count']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']
    
    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Posts'

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'color', 'created_at', 'posts_count']
    list_filter = ['created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']
    
    def posts_count(self, obj):
        return obj.posts.count()
    posts_count.short_description = 'Posts'

@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'is_featured', 'created_at', 'updated_at']
    list_filter = ['category', 'is_featured', 'created_at', 'updated_at']
    search_fields = ['title', 'content', 'author__email']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('title', 'content', 'author', 'image')
        }),
        ('Clasificación', {
            'fields': ('category', 'tags', 'is_featured')
        }),
        ('Fechas', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

admin.site.register(Comment)
admin.site.register(Rating)


from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

class BlogPost(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
    # Al definir related_name='comments', podemos acceder a los comentarios de un blog post con blog_post.comments.all()
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.email} on {self.blog_post.title}"

class Rating(models.Model):
    # Con related_name='ratings', podemos acceder a los ratings con blog_post.ratings.all()
    blog_post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Se puede agregar validación para score (por ejemplo, de 1 a 5)
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('blog_post', 'user')

    def __str__(self):
        return f"Rating by {self.user.email} on {self.blog_post.title}: {self.score}"

from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admins to access certain views.
    """
    def has_permission(self, request, view):
        return request.user and request.user.userprofile.role == 'admin'

class IsInstructorUser(permissions.BasePermission):
    """
    Custom permission to only allow instructors to access certain views.
    """
    def has_permission(self, request, view):
        return request.user and request.user.userprofile.role == 'instructor'
    
class IsAdminOrInstructor(permissions.BasePermission):
    """
    Custom permission to allow access to admins and instructors.
    """
    def has_permission(self, request, view):
        return request.user and request.user.userprofile.role in ['admin', 'instructor']
    
class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Object-level permission to only allow owners of an object to edit it.
    Assumes the model instance has an 'owner' attribute.
    """
    def has_object_permission(self, request, view, obj):
        # Permiso de solo lectura para cualquier solicitud segura
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permiso de escritura solo para el propietario del objeto
        return obj.user == request.user
    
class IsAuthorOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow authors of a blog post to edit or delete it.
    Admins have full access.
    """
    def has_object_permission(self, request, view, obj):
        # SAFE_METHODS are GET, HEAD or OPTIONS
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admins have full access
        if request.user.is_staff:
            return True

        # Only authors can edit or delete their own posts
        return obj.author == request.user
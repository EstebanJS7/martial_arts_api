from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso solo a administradores.
    """
    def has_permission(self, request, view):
        try:
            return request.user and request.user.userprofile.role == 'admin'
        except AttributeError:
            return False

class IsInstructorUser(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso solo a instructores.
    """
    def has_permission(self, request, view):
        try:
            return request.user and request.user.userprofile.role == 'instructor'
        except AttributeError:
            return False

class IsAdminOrInstructor(permissions.BasePermission):
    """
    Permiso personalizado para permitir el acceso a administradores e instructores.
    """
    def has_permission(self, request, view):
        try:
            return request.user and request.user.userprofile.role in ['admin', 'instructor']
        except AttributeError:
            return False

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permiso a nivel de objeto para permitir que solo el propietario pueda editarlo.
    Se asume que la instancia del modelo tiene un atributo 'user' que identifica al propietario.
    """
    def has_object_permission(self, request, view, obj):
        # Permiso de solo lectura para solicitudes seguras
        if request.method in permissions.SAFE_METHODS:
            return True

        # Permiso de escritura solo para el propietario del objeto
        return obj.user == request.user

class IsAuthorOrAdmin(permissions.BasePermission):
    """
    Permiso personalizado para permitir que solo el autor de un blog post o un administrador
    puedan editar o eliminar el post.
    """
    def has_object_permission(self, request, view, obj):
        # Permitir acceso en métodos seguros (GET, HEAD, OPTIONS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Los administradores tienen acceso completo
        if request.user.is_staff:
            return True

        # Solo el autor puede editar o eliminar su propio blog post
        return obj.author == request.user

from rest_framework import generics
from .models import UserProfile, CustomUser
from .serializers import UserProfileSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from rest_framework_simplejwt.views import TokenObtainPairView
from .throttling import (
    LoginRateThrottle,
    RegisterRateThrottle,
    PasswordResetRateThrottle,
    PasswordResetConfirmRateThrottle,
    BruteForceProtectionThrottle,
)
from .serializers import UserSerializer, PublicInstructorSerializer 
from .permissions import IsAdminUser, IsAdminOrInstructor
from .forms import EmailAuthenticationForm
from payments.models import Payment
import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from django.utils import timezone
from classes.models import Class
from blog.models import BlogPost

# Create your views here.

logger = logging.getLogger(__name__)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.userprofile
    

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer
    throttle_classes = [RegisterRateThrottle]
    
    def perform_create(self, serializer):
        # Crear el usuario
        # Los pagos se crearán automáticamente mediante la señal create_first_payments_for_student
        # en users/models.py cuando se cree el UserProfile con rol 'student'
        serializer.save()

class LoginView(APIView):
    """
    Vista de login con protección contra fuerza bruta y rate limiting.
    """
    throttle_classes = [LoginRateThrottle, BruteForceProtectionThrottle]
    permission_classes = (AllowAny,)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.brute_force_throttle = None
    
    def check_throttles(self, request):
        """
        Verifica los throttles y obtiene la instancia de BruteForceProtectionThrottle.
        """
        super().check_throttles(request)
        # Obtener la instancia de BruteForceProtectionThrottle para uso posterior
        for throttle in self.get_throttles():
            if isinstance(throttle, BruteForceProtectionThrottle):
                self.brute_force_throttle = throttle
                break
    
    def post(self, request, *args, **kwargs):
        form = EmailAuthenticationForm(data=request.data)
        if form.is_valid():
            user = form.get_user()
            refresh = RefreshToken.for_user(user)
            
            # Resetear intentos fallidos después de login exitoso
            if self.brute_force_throttle:
                self.brute_force_throttle.reset_failed_attempts(request)
            
            # Obtener el perfil del usuario
            try:
                user_profile = user.userprofile
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user_profile.role,
                    'dojo': user_profile.dojo.name if user_profile.dojo else None,
                    'dojo_id': user_profile.dojo.id if user_profile.dojo else None,
                }
            except UserProfile.DoesNotExist:
                # Si no existe el perfil, crear uno básico
                user_profile = UserProfile.objects.create(user=user)
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user_profile.role,
                    'dojo': user_profile.dojo.name if user_profile.dojo else None,
                    'dojo_id': user_profile.dojo.id if user_profile.dojo else None,
                }
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': user_data,
            })
        
        # Registrar intento fallido para protección contra fuerza bruta
        if self.brute_force_throttle:
            self.brute_force_throttle.record_failed_attempt(request)
        
        return Response(form.errors, status=400)
    
class LogoutView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=205)
        except Exception as e:
            return Response(status=400)
        
class UserListView(generics.ListCreateAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAdminUser]

class PasswordResetRequestView(APIView):
    """
    Vista para solicitar un restablecimiento de contraseña.
    Envía un correo electrónico con un enlace para restablecer la contraseña.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'success': False, 'message': 'El correo electrónico es requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = CustomUser.objects.get(email=email)
            
            # Generar token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Construir URL de restablecimiento
            frontend_url = settings.FRONTEND_URL
            reset_url = f"{frontend_url}/password-reset-confirm/{uid}/{token}"
            
            # Enviar correo electrónico
            subject = 'Restablecimiento de contraseña'
            message = f"""
            Hola,
            
            Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace para continuar:
            
            {reset_url}
            
            Si no solicitaste este restablecimiento, puedes ignorar este correo.
            
            Saludos,
            El equipo de Martial Arts
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            
            return Response(
                {'success': True, 'message': 'Se ha enviado un correo electrónico con instrucciones para restablecer tu contraseña'},
                status=status.HTTP_200_OK
            )
            
        except CustomUser.DoesNotExist:
            # Por seguridad, no revelamos si el correo existe o no
            return Response(
                {'success': True, 'message': 'Si el correo está registrado, recibirás instrucciones para restablecer tu contraseña'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error en solicitud de restablecimiento de contraseña: {str(e)}")
            return Response(
                {'success': False, 'message': 'Ocurrió un error al procesar tu solicitud'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PasswordResetConfirmView(APIView):
    """
    Vista para confirmar el restablecimiento de contraseña.
    Verifica el token y actualiza la contraseña del usuario.
    """
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetConfirmRateThrottle]
    
    def post(self, request):
        token = request.data.get('token')
        password = request.data.get('password')
        
        if not token or not password:
            return Response(
                {'success': False, 'message': 'Token y contraseña son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # El token debe tener el formato uid/token
            uid_token = token.split('/')
            if len(uid_token) != 2:
                return Response(
                    {'success': False, 'message': 'Token inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            uid = uid_token[0]
            token = uid_token[1]
            
            # Decodificar el uid
            user_id = force_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(pk=user_id)
            
            # Verificar el token
            if not default_token_generator.check_token(user, token):
                return Response(
                    {'success': False, 'message': 'El enlace ha expirado o es inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Actualizar la contraseña
            user.set_password(password)
            user.save()
            
            return Response(
                {'success': True, 'message': 'Tu contraseña ha sido actualizada correctamente'},
                status=status.HTTP_200_OK
            )
            
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {'success': False, 'message': 'El enlace ha expirado o es inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error en confirmación de restablecimiento de contraseña: {str(e)}")
            return Response(
                {'success': False, 'message': 'Ocurrió un error al procesar tu solicitud'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChangePasswordView(APIView):
    """
    Vista para cambiar la contraseña del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'success': False, 'message': 'Ambas contraseñas son requeridas'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not user.check_password(old_password):
            return Response(
                {'success': False, 'message': 'La contraseña actual es incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user.set_password(new_password)
        user.save()
        
        return Response(
            {'success': True, 'message': 'Contraseña actualizada correctamente'},
            status=status.HTTP_200_OK
        )

class UpdateUserRoleView(APIView):
    """
    Vista para actualizar el rol de un usuario.
    Solo accesible por administradores.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            new_role = request.data.get('role')
            
            if not new_role or new_role not in ['admin', 'instructor', 'student']:
                return Response(
                    {'success': False, 'message': 'Rol inválido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            user.userprofile.role = new_role
            user.userprofile.save()
            
            return Response(
                {'success': True, 'message': f'Rol actualizado a {new_role}'},
                status=status.HTTP_200_OK
            )
            
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

class InstructorStudentsView(generics.ListAPIView):
    """
    Vista para obtener la lista de estudiantes asignados a un instructor.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInstructor]
    
    def get_queryset(self):
        if self.request.user.userprofile.role == 'admin':
            # Los administradores pueden ver todos los estudiantes
            return CustomUser.objects.filter(userprofile__role='student')
        elif self.request.user.userprofile.role == 'instructor':
            # Los instructores solo ven sus estudiantes asignados
            instructor_dojo = self.request.user.userprofile.dojo
            return CustomUser.objects.filter(
                userprofile__role='student',
                userprofile__dojo=instructor_dojo
            )
        return CustomUser.objects.none()

class VerifyTokenView(APIView):
    """
    Vista para verificar si el token de autenticación es válido.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.userprofile.role,
                'dojo': user.userprofile.dojo.name if user.userprofile.dojo else None,
                'dojo_id': user.userprofile.dojo.id if user.userprofile.dojo else None,
            }
        })

class UserStatsView(APIView):
    """
    Vista para obtener estadísticas de usuarios.
    Solo accesible por administradores.
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        try:
            # Obtener estadísticas básicas
            total_users = UserProfile.objects.count()
            admin_count = UserProfile.objects.filter(role='admin').count()
            instructor_count = UserProfile.objects.filter(role='instructor').count()
            student_count = UserProfile.objects.filter(role='student').count()
            
            # Usuarios activos e inactivos
            active_users = UserProfile.objects.filter(user__is_active=True).count()
            inactive_users = UserProfile.objects.filter(user__is_active=False).count()
            
            # Nuevos usuarios este mes (simplificado)
            from django.utils import timezone
            from datetime import timedelta
            month_ago = timezone.now() - timedelta(days=30)
            new_users_this_month = UserProfile.objects.filter(
                enrollment_date__gte=month_ago.date()
            ).count()
            
            stats = {
                'total_users': total_users,
                'admin_count': admin_count,
                'instructor_count': instructor_count,
                'student_count': student_count,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'new_users_this_month': new_users_this_month,
            }
            
            return Response(stats, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de usuarios: {str(e)}")
            return Response(
                {'success': False, 'message': 'Error al obtener estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PublicInstructorListView(generics.ListAPIView):
    """
    Lista pública de instructores para la landing page.
    """
    serializer_class = PublicInstructorSerializer
    permission_classes = [AllowAny]
    throttle_classes = []  # Deshabilitar throttling para endpoints públicos

    def get_queryset(self):
        limit = self.request.query_params.get('limit')
        queryset = UserProfile.objects.filter(role='instructor').select_related('user').order_by('user__first_name')
        if limit:
            try:
                limit_value = int(limit)
                if limit_value > 0:
                    queryset = queryset[:limit_value]
            except (ValueError, TypeError):
                pass
        return queryset


class PublicUserStatsView(APIView):
    """
    Estadísticas públicas resumidas para la landing page.
    """
    permission_classes = [AllowAny]
    throttle_classes = []  # Deshabilitar throttling para endpoints públicos

    def get(self, request):
        current_time = timezone.now()
        students = UserProfile.objects.filter(role='student').count()
        instructors = UserProfile.objects.filter(role='instructor').count()
        total_classes = Class.objects.filter(is_cancelled=False).count()
        upcoming_classes = Class.objects.filter(is_cancelled=False, date__gte=current_time).count()
        blog_posts = BlogPost.objects.count()

        return Response(
            {
                'students': students,
                'instructors': instructors,
                'classes_total': total_classes,
                'upcoming_classes': upcoming_classes,
                'blog_posts': blog_posts,
            },
            status=status.HTTP_200_OK
        )


class ActivateUserView(APIView):
    """
    Vista para activar un usuario.
    Solo accesible por administradores.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # Activar el usuario
            user.is_active = True
            user.save()
            
            return Response(
                {'success': True, 'message': 'Usuario activado correctamente'},
                status=status.HTTP_200_OK
            )
            
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error activando usuario {user_id}: {str(e)}")
            return Response(
                {'success': False, 'message': 'Error al activar usuario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeactivateUserView(APIView):
    """
    Vista para desactivar un usuario.
    Solo accesible por administradores.
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # No permitir desactivar al usuario actual
            if user == request.user:
                return Response(
                    {'success': False, 'message': 'No puedes desactivar tu propia cuenta'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Desactivar el usuario
            user.is_active = False
            user.save()
            
            return Response(
                {'success': True, 'message': 'Usuario desactivado correctamente'},
                status=status.HTTP_200_OK
            )
            
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error desactivando usuario {user_id}: {str(e)}")
            return Response(
                {'success': False, 'message': 'Error al desactivar usuario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class DeleteUserView(APIView):
    """
    Vista para eliminar un usuario (soft delete).
    Solo accesible por administradores.
    """
    permission_classes = [IsAdminUser]
    
    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)
            
            # No permitir eliminar al usuario actual
            if user == request.user:
                return Response(
                    {'success': False, 'message': 'No puedes eliminar tu propia cuenta'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Soft delete - marcar como eliminado
            user.is_active = False
            user.email = f"deleted_{user_id}_{user.email}"
            user.save()
            
            return Response(
                {'success': True, 'message': 'Usuario eliminado correctamente'},
                status=status.HTTP_200_OK
            )
            
        except CustomUser.DoesNotExist:
            return Response(
                {'success': False, 'message': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error eliminando usuario {user_id}: {str(e)}")
            return Response(
                {'success': False, 'message': 'Error al eliminar usuario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
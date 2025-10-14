from rest_framework import generics
from .models import UserProfile, CustomUser
from .serializers import UserProfileSerializer, RegisterSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
# from rest_framework_simplejwt.views import TokenObtainPairView
from .throttling import LoginRateThrottle
from .serializers import UserSerializer 
from .permissions import IsAdminUser, IsAdminOrInstructor
from .forms import EmailAuthenticationForm
from payments.models import Payment
from payments.services import PaymentService 
import logging
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status

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
    
    def perform_create(self, serializer):
        # Crear el usuario
        user = serializer.save()
        
        # Intentar crear los pagos automáticos para el usuario hasta fin de año
        try:
            PaymentService.create_payments_for_remaining_year(user)
        except Exception as e:
            # Se registra el error pero no se impide el registro del usuario
            logger.error(f"Error creando pagos para el usuario {user.email}: {e}")

class LoginView(APIView):
    # Comentado temporalmente para eliminar dependencia de Redis
    # throttle_classes = [LoginRateThrottle]
    permission_classes = (AllowAny,)
    
    def post(self, request, *args, **kwargs):
        form = EmailAuthenticationForm(data=request.data)
        if form.is_valid():
            user = form.get_user()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
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
                'dojo': user.userprofile.dojo
            }
        })
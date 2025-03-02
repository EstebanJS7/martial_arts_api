
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
from .permissions import IsAdminUser
from .forms import EmailAuthenticationForm
from payments.models import Payment
from payments.services import PaymentService 
import logging
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
    throttle_classes = [LoginRateThrottle]
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
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
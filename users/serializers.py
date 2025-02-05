from rest_framework import serializers
from .models import UserProfile, CustomUser
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model, authenticate
from .validators import validate_password_custom
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        
class RegisterSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password_custom],
        error_messages={
            'required': _("Por favor ingrese una contraseña."),
        }
    )
    password2 = serializers.CharField(write_only=True, required=True)

    # Campos adicionales para el perfil del usuario
    dojo = serializers.CharField(write_only=True, required=True)
    belt_rank = serializers.CharField(write_only=True, required=True)
    city = serializers.CharField(write_only=True, required=True)
    address = serializers.CharField(write_only=True, required=True)
    phone_number = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = (
            'email', 'first_name', 'last_name', 'password', 'password2',
            'dojo', 'belt_rank', 'city', 'address', 'phone_number'
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        # Extraemos los datos adicionales para el perfil
        profile_data = {
            'dojo': validated_data.pop('dojo'),
            'belt_rank': validated_data.pop('belt_rank'),
            'city': validated_data.pop('city'),
            'address': validated_data.pop('address'),
            'phone_number': validated_data.pop('phone_number'),
        }
        # Utilizamos el método create_user del manager para crear el usuario
        user = CustomUser.objects.create_user(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password']
        )
        # Dado que ya existe una señal que crea automáticamente el UserProfile al crear el usuario,
        # asignamos o actualizamos los campos adicionales al perfil
        for field, value in profile_data.items():
            setattr(user.userprofile, field, value)
        user.userprofile.save()
        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

class CustomAuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(label="Email")
    password = serializers.CharField(
        label="Password",
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials', code='authorization')
        else:
            raise serializers.ValidationError('Must include "email" and "password"', code='authorization')

        attrs['user'] = user
        return attrs

from rest_framework import serializers
from .models import UserProfile, CustomUser
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model, authenticate
from .validators import validate_password_custom
from django.utils.translation import gettext_lazy as _
from contact.serializers import AcademySerializer

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    # Campos del usuario relacionado
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    # Campo dojo como ID de academia (para escritura) y objeto completo (para lectura)
    dojo_name = serializers.CharField(source='dojo.name', read_only=True, allow_null=True)
    dojo_id = serializers.IntegerField(source='dojo.id', read_only=True, allow_null=True)
    dojo_data = AcademySerializer(source='dojo', read_only=True, allow_null=True)
    # Campo belt_rank como ID de cinturón (para escritura) y objeto completo (para lectura)
    belt_rank_name = serializers.CharField(source='belt_rank.name', read_only=True, allow_null=True)
    belt_rank_id = serializers.IntegerField(source='belt_rank.id', read_only=True, allow_null=True)
    belt_rank_data = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = '__all__'
    
    def get_belt_rank_data(self, obj):
        """Retorna los datos completos del cinturón si existe"""
        if obj.belt_rank:
            from performance.serializers import BeltRankSerializer
            return BeltRankSerializer(obj.belt_rank).data
        return None


class PublicInstructorSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    dojo_name = serializers.CharField(source='dojo.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            'id',
            'first_name',
            'last_name',
            'email',
            'role',
            'belt_rank',
            'dojo',
            'dojo_name',
            'bio',
            'profile_picture',
            'social_media_links',
            'city',
            'country',
        )
        
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
    dojo = serializers.IntegerField(write_only=True, required=True, help_text='ID de la academia')
    belt_rank = serializers.IntegerField(write_only=True, required=True, help_text='ID del cinturón')
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
        dojo_id = validated_data.pop('dojo')
        belt_rank_id = validated_data.pop('belt_rank')
        profile_data = {
            'city': validated_data.pop('city'),
            'address': validated_data.pop('address'),
            'phone_number': validated_data.pop('phone_number'),
        }
        
        # Buscar la academia por ID
        from contact.models import Academy
        try:
            academy = Academy.objects.get(id=dojo_id, is_active=True)
            profile_data['dojo'] = academy
        except Academy.DoesNotExist:
            raise serializers.ValidationError({"dojo": "La academia seleccionada no existe o no está activa."})
        
        # Buscar el cinturón por ID
        from performance.models import BeltRank
        try:
            belt_rank = BeltRank.objects.get(id=belt_rank_id, is_active=True)
            profile_data['belt_rank'] = belt_rank
        except BeltRank.DoesNotExist:
            raise serializers.ValidationError({"belt_rank": "El cinturón seleccionado no existe o no está activo."})
        
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

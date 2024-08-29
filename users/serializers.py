from rest_framework import serializers
from .models import UserProfile, CustomUser
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from django.contrib.auth import get_user_model, authenticate

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
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    dojo = serializers.CharField(required=True)
    belt_rank = serializers.CharField(required=True)
    city = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    phone_number = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'password', 'password2', 'dojo', 'belt_rank', 'city', 'address', 'phone_number')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.save()
        # Crear el UserProfile asociado
        UserProfile.objects.create(
            user=user,
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            dojo=validated_data['dojo'],
            belt_rank=validated_data['belt_rank'],
            city=validated_data['city'],
            address=validated_data['address'],
            phone_number=validated_data['phone_number']
        )

        return user
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']

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
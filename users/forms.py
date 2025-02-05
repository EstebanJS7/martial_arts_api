from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from .models import CustomUser
from django.contrib.auth import authenticate

class EmailAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Reemplaza el campo 'username' por 'email' en el formulario
        self.fields['email'].required = True
        self.fields.pop('username', None)  # Eliminar el campo username si existe

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None:
                raise self.get_invalid_login_error()
        return self.cleaned_data

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')

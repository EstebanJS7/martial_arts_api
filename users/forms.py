from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm
from .models import CustomUser

class EmailAuthenticationForm(AuthenticationForm):
    # Cambiar 'username' a 'email' ya que has eliminado el campo 'username'
    username = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={"autofocus": True}))

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'first_name', 'last_name', 'is_active', 'is_staff')

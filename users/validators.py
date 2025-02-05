from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

def validate_password_custom(password):
    if len(password) < 8:
        raise ValidationError(
            _("Esta contraseña es demasiado corta. Debe contener al menos 8 caracteres."),
            code='password_too_short',
        )
    if password.isdigit():
        raise ValidationError(
            _("Esta contraseña es completamente numérica."),
            code='password_entirely_numeric',
        )
    # Puedes agregar más validaciones aquí

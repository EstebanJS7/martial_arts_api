from django.urls import path
from .views import contact_form_view

app_name = 'contact'

urlpatterns = [
    path('', contact_form_view, name='contact-form'),
]


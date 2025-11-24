from django.urls import path
from .views import contact_form_view
from .academy_views import AcademyListView, AcademyDetailView

app_name = 'contact'

urlpatterns = [
    path('', contact_form_view, name='contact-form'),
    # Endpoints para academias
    path('academies/', AcademyListView.as_view(), name='academy-list'),
    path('academies/<int:pk>/', AcademyDetailView.as_view(), name='academy-detail'),
]



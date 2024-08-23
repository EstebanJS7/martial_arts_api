from django.urls import path
from . import views
from .views import RegisterView
from .views import LoginView
from .views import LogoutView
from .views import UserListView

urlpatterns = [
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admin/users/', UserListView.as_view(), name='user-list'),
]
from django.urls import path
from . import views
from .views import RegisterView
from .views import LoginView
from .views import LogoutView
from .views import UserListView
from .views import PasswordResetRequestView, PasswordResetConfirmView
from .views import ChangePasswordView, UpdateUserRoleView, InstructorStudentsView, VerifyTokenView, UserStatsView, ActivateUserView, DeactivateUserView, DeleteUserView, PublicInstructorListView, PublicUserStatsView

urlpatterns = [
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('admin/users/', UserListView.as_view(), name='user-list'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('admin/update-role/<int:user_id>/', UpdateUserRoleView.as_view(), name='update-user-role'),
    path('admin/stats/', UserStatsView.as_view(), name='user-stats'),
    path('admin/activate/<int:user_id>/', ActivateUserView.as_view(), name='activate-user'),
    path('admin/deactivate/<int:user_id>/', DeactivateUserView.as_view(), name='deactivate-user'),
    path('admin/delete/<int:user_id>/', DeleteUserView.as_view(), name='delete-user'),
    path('instructor/students/', InstructorStudentsView.as_view(), name='instructor-students'),
    path('verify-token/', VerifyTokenView.as_view(), name='verify-token'),
    path('public/instructors/', PublicInstructorListView.as_view(), name='public-instructors'),
    path('public/stats/', PublicUserStatsView.as_view(), name='public-user-stats'),
]
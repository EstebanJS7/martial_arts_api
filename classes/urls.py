# urls.py
from django.urls import path
from .views import (
    ClassCreateView, 
    MultiClassCreateView,
    ClassListView, 
    ClassDetailView,
    MultiClassUpdateView,
    UserClassReservationCreateView,
    UserClassReservationCancelView,
    UserClassReservationUpdateView,
    UpcomingClassesView,
    UserClassesView,
    AllClassesView,
    ClassAttendanceListView,
    ClassAttendanceCreateUpdateView,
    ClassAttendanceBulkUpdateView,
    ClassTemplateListView,
    ClassTemplateDetailView,
    ClassDashboardView,
    ClassStatsView,
    ClassTrendsView,
    TopInstructorsView,
    PopularClassesView,
    ClassWaitlistListView,
    ClassWaitlistCreateView,
    ClassWaitlistDeleteView,
    ClassWaitlistConvertView,
    ClassQRCodeView,
    ClassQRDataView,
    QRCheckInView,
    ClassRecurringCreateView,
    ClassAttendanceHealthCheckView,
    ClassStatisticsDetailView,
    ClassReminderTriggerView,
)

urlpatterns = [
    path('create/', ClassCreateView.as_view(), name='class-create'),
    path('create-multiple/', MultiClassCreateView.as_view(), name='class-create-multiple'),
    path('list/', ClassListView.as_view(), name='class-list'),
    path('all/', AllClassesView.as_view(), name='all-classes'),
    path('<int:pk>/', ClassDetailView.as_view(), name='class-detail'),
    path('classes/bulk-update/', MultiClassUpdateView.as_view(), name='classes-bulk-update'),
    path('reserve/', UserClassReservationCreateView.as_view(), name='class-reserve'),
    path('reserve/<int:pk>/cancel/', UserClassReservationCancelView.as_view(), name='class-reservation-cancel'),
    path('reserve/<int:pk>/update/', UserClassReservationUpdateView.as_view(), name='class-reservation-update'),
    path('upcoming/', UpcomingClassesView.as_view(), name='upcoming-classes'),
    path('user-classes/', UserClassesView.as_view(), name='user-classes'),
    
    # Rutas para Asistencia de Clases
    path('<int:class_id>/attendance/', ClassAttendanceListView.as_view(), name='class-attendance-list'),
    path('<int:class_id>/attendance/mark/', ClassAttendanceCreateUpdateView.as_view(), name='class-attendance-mark'),
    path('<int:class_id>/attendance/bulk/', ClassAttendanceBulkUpdateView.as_view(), name='class-attendance-bulk'),
    
    # Rutas para Plantillas de Clases
    path('templates/', ClassTemplateListView.as_view(), name='class-template-list'),
    path('templates/<int:pk>/', ClassTemplateDetailView.as_view(), name='class-template-detail'),
    
    # Rutas para Dashboard de Estadísticas
    path('dashboard/', ClassDashboardView.as_view(), name='class-dashboard'),
    path('stats/monthly/', ClassStatsView.as_view(), name='class-stats-monthly'),
    path('stats/trends/', ClassTrendsView.as_view(), name='class-trends'),
    path('stats/top-instructors/', TopInstructorsView.as_view(), name='class-top-instructors'),
    path('stats/popular-classes/', PopularClassesView.as_view(), name='class-popular-classes'),
    
    # Rutas para Lista de Espera de Clases
    path('waitlist/', ClassWaitlistListView.as_view(), name='class-waitlist-list'),
    path('waitlist/create/', ClassWaitlistCreateView.as_view(), name='class-waitlist-create'),
    path('waitlist/<int:pk>/delete/', ClassWaitlistDeleteView.as_view(), name='class-waitlist-delete'),
    path('waitlist/<int:pk>/convert/', ClassWaitlistConvertView.as_view(), name='class-waitlist-convert'),
    
    # Rutas para Códigos QR de Check-in
    path('<int:class_id>/qr-code/', ClassQRCodeView.as_view(), name='class-qr-code'),
    path('<int:class_id>/qr-data/', ClassQRDataView.as_view(), name='class-qr-data'),
    path('qr-checkin/', QRCheckInView.as_view(), name='qr-checkin'),
    
    # Rutas avanzadas de gestión
    path('manage/recurring/', ClassRecurringCreateView.as_view(), name='class-recurring-create'),
    path('<int:class_id>/attendance/check/', ClassAttendanceHealthCheckView.as_view(), name='class-attendance-check'),
    path('<int:class_id>/statistics/', ClassStatisticsDetailView.as_view(), name='class-statistics-detail'),
    path('manage/reminders/', ClassReminderTriggerView.as_view(), name='class-reminders-trigger'),
]

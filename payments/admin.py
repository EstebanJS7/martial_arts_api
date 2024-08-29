from django.contrib import admin
from .models import Payment, CurrentQuota

admin.site.register(Payment)
admin.site.register(CurrentQuota)

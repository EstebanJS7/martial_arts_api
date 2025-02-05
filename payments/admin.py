from django.contrib import admin
from .models import Payment, QuotaConfig

class PaymentAdmin(admin.ModelAdmin):
    readonly_fields = ('due_date',)
    list_display = ('user', 'amount', 'amount_paid', 'due_date', 'is_paid', 'is_fully_paid')
    search_fields = ('user__email',)

admin.site.register(Payment, PaymentAdmin)
admin.site.register(QuotaConfig)

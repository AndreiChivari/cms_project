from django.contrib import admin
from .models import CerereAccesPortal, AccesPortalParte, JurnalAccesPortal

@admin.register(CerereAccesPortal)
class CerereAdmin(admin.ModelAdmin):
    list_display = ['nume_solicitant', 'dosar', 'stare', 'data_cererii', 'aprobata_de']
    list_filter = ['stare']
    search_fields = ['nume_solicitant', 'dosar__numar_unic']
    readonly_fields = ['data_cererii', 'data_procesarii']

@admin.register(AccesPortalParte)
class AccesAdmin(admin.ModelAdmin):
    list_display = ['parte', 'cerere', 'activ', 'data_expirare']
    list_filter = ['activ']
    readonly_fields = ['cod_acces', 'pin_hash']

@admin.register(JurnalAccesPortal)
class JurnalAdmin(admin.ModelAdmin):
    list_display = ['acces', 'timestamp', 'sectiune', 'ip_address']
    readonly_fields = ['timestamp']
from django.contrib import admin
from .models import ActUrmarire

class ActUrmarireAdmin(admin.ModelAdmin):
    list_display = ('titlu', 'tip', 'dosar', 'autor', 'data_incarcarii')
    list_filter = ('tip', 'data_incarcarii')
    search_fields = ('titlu', 'dosar__numar_unic') # Căutăm și după numărul dosarului!

admin.site.register(ActUrmarire, ActUrmarireAdmin)
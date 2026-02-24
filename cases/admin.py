from django.contrib import admin
from .models import Dosar, ParteImplicata

class ParteImplicataInline(admin.TabularInline):
    """
    Acest truc ne permite să adăugăm suspecți/martori direct de pe 
    pagina de creare a dosarului penal, fără să dăm click pe altă pagină.
    Dă foarte bine la prezentare!
    """
    model = ParteImplicata
    extra = 1 # Câte rânduri goale să arate implicit

class DosarAdmin(admin.ModelAdmin):
    list_display = ('numar_unic', 'stadiu', 'ofiter_caz', 'procuror_caz', 'data_inregistrarii')
    list_filter = ('stadiu', 'data_inregistrarii')
    search_fields = ('numar_unic', 'infractiune_cercetata')
    inlines = [ParteImplicataInline]

admin.site.register(Dosar, DosarAdmin)
admin.site.register(ParteImplicata)
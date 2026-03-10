from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva

class ParteImplicataInline(admin.TabularInline):
    """
    Acest truc ne permite să adăugăm suspecți/martori direct de pe 
    pagina de creare a dosarului penal, fără să dăm click pe altă pagină.
    Dă foarte bine la prezentare!
    """
    model = ParteImplicata
    extra = 1 # Câte rânduri goale să arate implicit

# 1. SECRETUL: DosarAdmin moștenește acum din SimpleHistoryAdmin!
# Astfel păstrezi și design-ul tău, și funcția de audit.
class DosarAdmin(SimpleHistoryAdmin):
    # Am șters 'stadiu' din ambele liste de mai jos:
    list_display = ('numar_unic', 'ofiter_caz', 'procuror_caz', 'data_inregistrarii')
    list_filter = ('data_inregistrarii',)
    search_fields = ('numar_unic', 'infractiune_cercetata')
    inlines = [ParteImplicataInline]

# 2. Înregistrăm o singură dată fiecare model
admin.site.register(Dosar, DosarAdmin)
admin.site.register(ParteImplicata, SimpleHistoryAdmin)
admin.site.register(Infractiune, SimpleHistoryAdmin)
admin.site.register(MasuraPreventiva, SimpleHistoryAdmin)

# ==========================================
# PANOU CENTRALIZAT PENTRU JURNALUL DE AUDIT
# ==========================================

class JurnalGlobalAdmin(admin.ModelAdmin):
    """
    Acesta este panoul de comandă centralizat pentru Audit.
    Afișează log-urile sub formă de tabel și adaugă filtrele complexe în dreapta.
    """
    # Ce coloane vedem în tabel
    list_display = ('__str__', 'history_date', 'history_user', 'history_type')
    
    # FILTRELE COMPLEXE (Apar în meniul din dreapta)
    list_filter = ('history_date', 'history_user', 'history_type')
    
    # Ordonăm cronologic, cele mai noi primele
    ordering = ('-history_date',)
    
    # SECURITATE MAXIMĂ: BLOCĂM ORICE MODIFICARE SAU ȘTERGERE DIN PANOU!
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

# 1. Panou specific pentru Dosare (caută după numărul dosarului)
class JurnalDosarAdmin(JurnalGlobalAdmin):
    search_fields = ('numar_unic',)

# 2. Panou specific pentru Părți Implicate (caută după nume sau CNP)
class JurnalParteAdmin(JurnalGlobalAdmin):
    search_fields = ('nume_complet', 'cnp')

# 3. Panou specific pentru Măsuri Preventive (caută după numele inculpatului)
class JurnalMasuraAdmin(JurnalGlobalAdmin):
    # Folosim dublu underscore (__) pentru a căuta în tabelul legat (ParteImplicata)
    search_fields = ('parte__nume_complet',)

# ÎNREGISTRĂM TABELELE ASCUNSE (FANTOMĂ) DIRECT PE PAGINA PRINCIPALĂ ADMIN
# Înregistrăm fiecare jurnal cu panoul lui inteligent
admin.site.register(Dosar.history.model, JurnalDosarAdmin)
admin.site.register(ParteImplicata.history.model, JurnalParteAdmin)
admin.site.register(MasuraPreventiva.history.model, JurnalMasuraAdmin)

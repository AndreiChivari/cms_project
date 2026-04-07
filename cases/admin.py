from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva, IstoricDesemnare, StadiuCercetare, SolutieDosar, Notificare
import csv
from django.http import HttpResponse

# --- EDITARE INLINE (Pe aceeași pagină) ---

class ParteImplicataInline(admin.TabularInline):
    model = ParteImplicata
    extra = 0 # Modificat la 0 ca să nu arate rânduri goale urâte dacă nu e nevoie

class InfractiuneInline(admin.TabularInline):
    model = Infractiune
    extra = 0

class StadiuCercetareInline(admin.TabularInline):
    model = StadiuCercetare
    extra = 0

# --- PANOU DOSAR AVANSAT ---

class DosarAdmin(SimpleHistoryAdmin):
    # Am adăugat o metodă personalizată care să afișeze și ID-ul intern pentru siguranță
    list_display = ('numar_unic', 'ofiter_caz', 'procuror_caz', 'data_inregistrarii', 'stadiu_curent_display')
    list_filter = ('data_inregistrarii', 'ofiter_caz') # Filtre laterale
    search_fields = ('numar_unic', 'infractiune_cercetata')
    
    # Magia: Toate aceste 3 tabele apar DEDESUBTUL detaliilor dosarului!
    inlines = [StadiuCercetareInline, InfractiuneInline, ParteImplicataInline]
    
    # ---------------------------------------------------------
    # ACȚIUNE PERSONALIZATĂ: EXPORTĂ DOSARELE SELECTATE ÎN CSV
    # ---------------------------------------------------------
    actions = ['export_as_csv']

    @admin.action(description='Exportă dosarele selectate (CSV)')
    def export_as_csv(self, request, queryset):
        """Permite selectarea a 10 dosare și descărcarea lor automată într-un fișier Excel/CSV"""
        meta = self.model._meta
        field_names = ['numar_unic', 'data_inregistrarii', 'infractiune_cercetata']

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename=raport_dosare.csv'
        writer = csv.writer(response)

        # Scriem capul de tabel
        writer.writerow(field_names)
        
        # Scriem datele pentru fiecare dosar selectat
        for obj in queryset:
            writer.writerow([getattr(obj, field) for field in field_names])

        return response

    # ---------------------------------------------------------
    # AFIȘARE CUSTOM ÎN TABEL (Coloană Generată Dinamic)
    # ---------------------------------------------------------
    def stadiu_curent_display(self, obj):
        """Afișează stadiul curent direct în tabelul mare din admin"""
        stadiu = obj.stadiu_curent
        return stadiu.get_tip_stadiu_display() if stadiu else "Nesetat"
    stadiu_curent_display.short_description = "Stadiu Curent"

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

@admin.register(Notificare)
class NotificareAdmin(admin.ModelAdmin):
    list_display = ('utilizator', 'mesaj', 'citita', 'data_crearii')
    list_filter = ('citita', 'data_crearii')
    search_fields = ('utilizator__username', 'mesaj', 'utilizator__first_name', 'utilizator__last_name')

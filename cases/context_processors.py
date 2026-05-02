from django.utils import timezone
from datetime import timedelta
from .models import Notificare
 
def notificari_globale(request):
    if not request.user.is_authenticated:
        return {'notificari_necitite': [], 'nr_notificari': 0}
 
    necitite = Notificare.objects.filter(
        utilizator=request.user,
        citita=False
    ).select_related()  # optimizare query
 
    # Grupare temporală
    azi       = timezone.now().date()
    ieri      = azi - timedelta(days=1)
 
    grup_azi      = []
    grup_ieri     = []
    grup_mai_vechi = []
 
    for n in necitite:
        data_notif = n.data_crearii.date()
        if data_notif == azi:
            grup_azi.append(n)
        elif data_notif == ieri:
            grup_ieri.append(n)
        else:
            grup_mai_vechi.append(n)
 
    return {
        'notificari_necitite': necitite,          # lista completă (pentru compatibilitate)
        'nr_notificari':       necitite.count(),
        'notif_azi':           grup_azi,
        'notif_ieri':          grup_ieri,
        'notif_mai_vechi':     grup_mai_vechi,
    }
 
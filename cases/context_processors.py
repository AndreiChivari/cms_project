from .models import Notificare

def notificari_globale(request):
    # Dacă utilizatorul e logat, îi căutăm notificările Necitite
    if request.user.is_authenticated:
        necitite = Notificare.objects.filter(utilizator=request.user, citita=False)
        return {
            'notificari_necitite': necitite,
            'nr_notificari': necitite.count()
        }
    # Dacă nu e logat (ex: pagina de login), nu returnăm nimic
    return {'notificari_necitite': [], 'nr_notificari': 0}
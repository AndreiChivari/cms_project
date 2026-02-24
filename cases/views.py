from django.shortcuts import render, get_object_or_404 # <--- Am adăugat get_object_or_404
from .models import Dosar

def lista_dosare(request):
    dosare = Dosar.objects.all().order_by('-data_inregistrarii')
    context = {'dosare': dosare}
    return render(request, 'cases/lista_dosare.html', context)

# FUNȚIA NOUĂ:
def detalii_dosar(request, pk):
    # Caută dosarul cu ID-ul respectiv. Dacă nu există (ex: cineva scrie manual /cases/999/), 
    # returnează automat o eroare 404 (Not Found), ceea ce este o practică excelentă de securitate!
    dosar = get_object_or_404(Dosar, pk=pk)
    
    context = {
        'dosar': dosar
    }
    
    return render(request, 'cases/detalii_dosar.html', context)
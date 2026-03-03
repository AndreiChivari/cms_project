import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva
from documents.forms import DocumentForm # Importăm formularul nou creat
from .forms import DosarForm, ParteImplicataForm, CreareDosarForm, InfractiuneForm, MasuraPreventivaForm
from documents.models import ActUrmarire
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import render_to_pdf
from django.http import HttpResponse # Adaugă și asta dacă nu există
from django.conf import settings # <--- Adaugă și asta sus la importuri
from datetime import date, timedelta # folosim pentru calculul alertelor


@login_required
def dashboard(request):
    utilizator = request.user
    
    # 1. Statistici Globale (toate dosarele din sistem)
    total_dosare = Dosar.objects.count()
    dosare_in_lucru = Dosar.objects.filter(Q(stadiu='POLITIE') | Q(stadiu='PROCUROR')).count()
    dosare_solutionate = Dosar.objects.filter(stadiu='SOLUTIONAT').count()
    
    # 2. Statistici Personale (Dosarele MELE)
    # Folosim Q objects pentru a spune: "Adu-mi dosarele unde sunt Ofițer SAU Procuror SAU Grefier"
    if utilizator.is_superuser or utilizator.rol == 'ADMIN':
        dosare_mele = total_dosare # Adminul vede tot
        dosarele_mele_lista = Dosar.objects.all().order_by('-data_inregistrarii')[:5] # Ultimele 5
    else:
        # Interogare complexă cu Q
        conditie_mea = Q(ofiter_caz=utilizator) | Q(procuror_caz=utilizator) | Q(grefier_caz=utilizator)
        dosare_mele = Dosar.objects.filter(conditie_mea).count()
        dosarele_mele_lista = Dosar.objects.filter(conditie_mea).order_by('-data_inregistrarii')[:5]
        
    # === LOGICA NOUĂ PENTRU ALERTE (10 ZILE) ===
    azi = date.today()
    prag_10_zile = azi + timedelta(days=10)

    # Găsim toate măsurile care expiră în max 10 zile, dar nu mai vechi de 5 zile de la expirare
    alerte_toate = MasuraPreventiva.objects.filter(
        data_sfarsit__lte=prag_10_zile,
        data_sfarsit__gte=azi - timedelta(days=5) 
    ).order_by('data_sfarsit')

    # Filtrăm ca fiecare să vadă doar dosarele lui (Polițist, Procuror sau Grefier)
    if request.user.is_superuser:
        alerte_masuri = alerte_toate
    else:
        alerte_masuri = alerte_toate.filter(
            Q(dosar__ofiter_caz=request.user) |
            Q(dosar__procuror_caz=request.user) |
            Q(dosar__grefier_caz=request.user)
        )
    # ============================================


    context = {
        'total_dosare': total_dosare,
        'dosare_in_lucru': dosare_in_lucru,
        'dosare_judecata': dosare_solutionate, # Păstrăm numele variabilei pt HTML, dar îi dăm datele noi
        'dosare_mele': dosare_mele,
        'dosarele_mele_lista': dosarele_mele_lista,
        'alerte_masuri': alerte_masuri, # <--- Trimitem alertele către HTML
    }
    
    return render(request, 'cases/dashboard.html', context)

@login_required
def adaugare_dosar(request):
    if request.method == 'POST':
        form = CreareDosarForm(request.POST)
        if form.is_valid():
            dosar_nou = form.save()
            return redirect('cases:detalii_dosar', pk=dosar_nou.pk)
    else:
        form = CreareDosarForm()
        
    context = {'form': form}
    return render(request, 'cases/adaugare_dosar.html', context)

@login_required
def lista_dosare(request):
    # 1. Luăm toate dosarele inițial
    dosare = Dosar.objects.all().order_by('-data_inregistrarii')
    
    # 2. Citim ce a scris utilizatorul în bara de căutare (dacă a scris ceva)
    # request.GET.get('nume_camp', 'valoare_default_daca_e_gol')
    query_text = request.GET.get('q', '') 
    stadiu_filtru = request.GET.get('stadiu', '')

    # 3. Aplicăm filtrul de text (Căutare în număr SAU infracțiune)
    if query_text:
        # icontains înseamnă "să conțină textul, ignorând majusculele/minusculele"
        dosare = dosare.filter(
            Q(numar_unic__icontains=query_text) | 
            Q(infractiune_cercetata__icontains=query_text)
        )

    # 4. Aplicăm filtrul de stadiu (Dropdown)
    if stadiu_filtru:
        dosare = dosare.filter(stadiu=stadiu_filtru)

    # --- COD NOU PENTRU PAGINARE ---
    # Împărțim rezultatele (dosare) în pagini de câte 10 (poți pune 2 sau 3 acum pentru testare!)
    paginator = Paginator(dosare, 10) 
    
    # Luăm numărul paginii curente din URL (ex: ?page=2)
    page_number = request.GET.get('page')
    
    # page_obj va conține DOAR dosarele de pe pagina curentă
    page_obj = paginator.get_page(page_number)  

    # Trimitem datele către HTML, INCLUSIV ce a căutat omul, ca să lăsăm textul în căsuță
    context = {
        'page_obj': page_obj,
        'query_text': query_text,
        'stadiu_filtru': stadiu_filtru,
        'stadii_posibile': Dosar.Stadiu.choices, # Trimitem opțiunile pentru dropdown
    }
    
    return render(request, 'cases/lista_dosare.html', context)

@login_required
def detalii_dosar(request, pk):
    dosar = get_object_or_404(Dosar, pk=pk)
    
    # Calculăm o singură dată dacă are drepturi, pentru a trimite către HTML
    poate_edita = dosar.are_drepturi_editare(request.user)
    
    form_document = DocumentForm()
    form_parte = ParteImplicataForm()
    form_infractiune = InfractiuneForm() # <--- 1. INIȚIALIZĂM NOUL FORMULAR

    # 1. Inițializăm formularul NOU, dându-i ID-ul dosarului
    form_masura = MasuraPreventivaForm(dosar_id=dosar.pk)
    
    if request.method == 'POST':
        if not poate_edita:
            raise PermissionDenied("Nu ai permisiunea de a modifica acest dosar.")
        # VERIFICARE 1: A apăsat butonul de adăugare Document?
        if 'btn_salveaza_document' in request.POST:
            form_document = DocumentForm(request.POST, request.FILES)
            if form_document.is_valid():
                document = form_document.save(commit=False)
                document.dosar = dosar
                document.autor = request.user
                document.save()
                return redirect('cases:detalii_dosar', pk=dosar.pk)
                
        # VERIFICARE 2: A apăsat butonul de adăugare Parte Implicată?
        elif 'btn_salveaza_parte' in request.POST:
            form_parte = ParteImplicataForm(request.POST)
            if form_parte.is_valid():
                parte = form_parte.save(commit=False)
                parte.dosar = dosar
                parte.save()
                return redirect('cases:detalii_dosar', pk=dosar.pk)
            
        # 2. LOGICA NOUĂ PENTRU SALVAREA INFRACȚIUNII
        elif 'btn_salveaza_infractiune' in request.POST:
            form_infractiune = InfractiuneForm(request.POST)
            if form_infractiune.is_valid():
                infractiune = form_infractiune.save(commit=False)
                infractiune.dosar = dosar  # Legăm infracțiunea de dosarul curent!
                infractiune.save()
                return redirect('cases:detalii_dosar', pk=dosar.pk)
            
        # 2. Logica pentru Măsuri Preventive
        elif 'btn_salveaza_masura' in request.POST:
            # Citim datele trimise și îi dăm din nou ID-ul dosarului pentru validare
            form_masura = MasuraPreventivaForm(request.POST, dosar_id=dosar.pk)
            if form_masura.is_valid():
                masura = form_masura.save(commit=False)
                masura.dosar = dosar
                masura.save()
                return redirect('cases:detalii_dosar', pk=dosar.pk)

    context = {
            'dosar': dosar,
            'form_document': form_document, # sau cum le-ai numit
            'form_parte': form_parte,
            'form_infractiune': form_infractiune, # <--- 3. TRIMITEM CĂTRE HTML
            'form_masura': form_masura, # <--- 3. Îl trimitem către HTML
            'poate_edita': poate_edita # <--- VERIFICĂ SĂ AI ACEASTĂ LINIE! Fără ea, HTML-ul crede că e False.
        }
    
    return render(request, 'cases/detalii_dosar.html', context)

@login_required
def editare_dosar(request, pk):
    # Găsim dosarul pe care vrem să-l edităm
    dosar = get_object_or_404(Dosar, pk=pk)

    # SECURITATE:
    if not dosar.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")
    
    if request.method == 'POST':
        # request.POST conține noile date. 
        # instance=dosar îi spune lui Django: "Nu crea un dosar nou, ci actualizează-l pe acesta!"
        form = DosarForm(request.POST, instance=dosar)
        if form.is_valid():
            form.save()
            # După salvare, trimitem utilizatorul înapoi pe pagina de detalii a dosarului
            return redirect('cases:detalii_dosar', pk=dosar.pk)
    else:
        # Dacă doar accesăm pagina, populăm formularul cu datele existente ale dosarului
        form = DosarForm(instance=dosar)
        
    context = {
        'form': form,
        'dosar': dosar
    }
    return render(request, 'cases/editare_dosar.html', context)

@login_required
def editare_parte(request, pk):
    # Găsim persoana după ID
    parte = get_object_or_404(ParteImplicata, pk=pk)
    # Reținem ID-ul dosarului pentru a ști unde să ne întoarcem
    dosar_id = parte.dosar.pk 

    # SECURITATE:
    if not parte.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")
    
    if request.method == 'POST':
        # Punem instance=parte pentru a suprascrie datele existente, nu a crea una nouă
        form = ParteImplicataForm(request.POST, instance=parte)
        if form.is_valid():
            form.save()
            return redirect('cases:detalii_dosar', pk=dosar_id)
    else:
        form = ParteImplicataForm(instance=parte)
        
    context = {'form': form, 'parte': parte}
    return render(request, 'cases/editare_parte.html', context)

@login_required
def stergere_parte(request, pk):
    parte = get_object_or_404(ParteImplicata, pk=pk)
    dosar_id = parte.dosar.pk
    
    # SECURITATE:
    if not parte.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")

    # Pentru ștergere, este o bună practică să cerem confirmare printr-un formular POST
    if request.method == 'POST':
        parte.delete() # Șterge efectiv din baza de date
        return redirect('cases:detalii_dosar', pk=dosar_id)
        
    context = {'parte': parte}
    return render(request, 'cases/stergere_parte.html', context)

@login_required
def editare_document(request, pk):
    document = get_object_or_404(ActUrmarire, pk=pk)
    dosar_id = document.dosar.pk

    if not document.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")
    
    if request.method == 'POST':
        # ATENȚIE: request.FILES este obligatoriu aici pentru a putea schimba PDF-ul/Word-ul!
        form = DocumentForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            form.save()
            return redirect('cases:detalii_dosar', pk=dosar_id)
    else:
        form = DocumentForm(instance=document)
        
    context = {'form': form, 'document': document}
    return render(request, 'cases/editare_document.html', context)

@login_required
def stergere_document(request, pk):
    document = get_object_or_404(ActUrmarire, pk=pk)
    dosar_id = document.dosar.pk

    if not document.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")
     
    if request.method == 'POST':
        # TRUC PENTRU LICENȚĂ: Django șterge înregistrarea din baza de date, 
        # dar în mod implicit NU șterge fișierul fizic de pe hard disk!
        # Mai jos îi spunem să șteargă și fișierul fizic, dacă există.
        if document.fisier:
            document.fisier.delete(save=False)
            
        document.delete() # Șterge înregistrarea din tabel
        return redirect('cases:detalii_dosar', pk=dosar_id)
        
    context = {'document': document}
    return render(request, 'cases/stergere_document.html', context)

# ... restul funcțiilor tale (lista_dosare, detalii_dosar, dashboard etc.) rămân exact la fel ...

@login_required
def generare_pdf_dosar(request, pk):
    dosar = get_object_or_404(Dosar, pk=pk)
    
    if not dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu aveți acces la vizualizarea acestui dosar.")

    context = {
        'dosar': dosar,
        'parti_implicate': dosar.parti_implicate.all(),
        'request': request,
    }
    
    pdf = render_to_pdf('cases/pdf_template.html', context)
    
    if pdf:
        nume_fisier = f"Fisa_Dosar_{dosar.numar_unic.replace('/', '_')}.pdf"
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nume_fisier}"'
        return response
        
    return HttpResponse("A apărut o eroare la generarea PDF-ului.", status=400)

@login_required
def stergere_masura(request, pk):
    # Găsim măsura în baza de date
    masura = get_object_or_404(MasuraPreventiva, pk=pk)
    dosar_id = masura.dosar.pk
    
    # Securitate: Verificăm dacă utilizatorul are drepturi pe dosarul respectiv
    if not masura.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu ai permisiunea de a șterge date din acest dosar.")
        
    # Dacă utilizatorul a apăsat "Da, șterge" (adică a trimis un POST)
    if request.method == 'POST':
        masura.delete()
        return redirect('cases:detalii_dosar', pk=dosar_id)
        
    # Dacă a dat doar click pe link, îi afișăm pagina de confirmare
    context = {
        'masura': masura,
        'dosar': masura.dosar
    }
    return render(request, 'cases/stergere_masura.html', context)
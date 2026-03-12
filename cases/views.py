import os
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva, IstoricDesemnare, StadiuCercetare, SolutieDosar, Notificare
from documents.forms import DocumentForm # Importăm formularul nou creat
from .forms import DosarForm, ParteImplicataForm, CreareDosarForm, InfractiuneForm, MasuraPreventivaForm, StadiuCercetareForm, SolutieDosarForm
from documents.models import ActUrmarire
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import render_to_pdf
from django.http import HttpResponse # Adaugă și asta dacă nu există
from django.conf import settings # <--- Adaugă și asta sus la importuri
from datetime import datetime, date, timedelta # folosim pentru calculul alertelor
from django.urls import reverse # folosim pentru a genera link-urile automate către dosare
from django.http import JsonResponse # folosim JavaScript (AJAX) pentru a sterge notificarile fara a da click pe ele si a nu reîncărca pagina
from django.contrib.auth import get_user_model
import io
import openpyxl
from openpyxl.styles import Font, Alignment

User = get_user_model()

@login_required
def dashboard(request):
    utilizator = request.user
    
    # 1. Statistici Globale (toate dosarele din sistem)
    total_dosare = Dosar.objects.count()
    
    # LOGICA NOUĂ PENTRU STATISTICI
    # Căutăm dosarele care au măcar o soluție bifată ca "FINALĂ".
    # Folosim .distinct() pentru că un dosar ar putea avea, teoretic, două soluții finale
    # (ex: disjungeri) și nu vrem să numărăm dosarul de două ori.
    dosare_solutionate = Dosar.objects.filter(
        stadii_cercetare__solutii__este_finala=True
    ).distinct().count()
    
    # Restul dosarelor sunt "în lucru" (fie abia înregistrate, fie cu stadii intermediare)
    dosare_in_lucru = total_dosare - dosare_solutionate
    
    # 2. Statistici Personale (Dosarele MELE)
    # Folosim Q objects pentru a spune: "Adu-mi dosarele unde sunt Ofițer SAU Procuror SAU Grefier"
    if utilizator.is_superuser or utilizator.rol == 'ADMIN':
        dosare_mele = total_dosare 
        dosarele_mele_lista = Dosar.objects.all().order_by('-data_inregistrarii')[:5] 
    else:
        # Interogare complexă cu Q
        conditie_mea = Q(ofiter_caz=utilizator) | Q(procuror_caz=utilizator) | Q(grefier_caz=utilizator)
        dosare_mele = Dosar.objects.filter(conditie_mea).count()
        dosarele_mele_lista = Dosar.objects.filter(conditie_mea).order_by('-data_inregistrarii')[:5]
        
    # === LOGICA PENTRU ALERTE MĂSURI PREVENTIVE ===
     # Găsim toate măsurile care expiră în max 10 zile, dar nu mai vechi de 5 zile de la expirare
    azi = date.today()
    prag_10_zile = azi + timedelta(days=10)

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
        'dosare_judecata': dosare_solutionate, # Păstrăm numele variabilei pt HTML ca să nu mai modifici acolo
        'dosare_mele': dosare_mele,
        'dosarele_mele_lista': dosarele_mele_lista,
        'alerte_masuri': alerte_masuri,
    }
    
    return render(request, 'cases/dashboard.html', context)

@login_required
def adaugare_dosar(request):
    if request.method == 'POST':
        form = CreareDosarForm(request.POST)
        if form.is_valid():
            dosar = form.save()

            # LOGICA: Creăm istoricul inițial
            if dosar.ofiter_caz:
                IstoricDesemnare.objects.create(dosar=dosar, utilizator=dosar.ofiter_caz, rol='Ofițer', data_desemnare=dosar.data_inregistrarii)
            if dosar.procuror_caz:
                IstoricDesemnare.objects.create(dosar=dosar, utilizator=dosar.procuror_caz, rol='Procuror', data_desemnare=dosar.data_inregistrarii)
            if dosar.grefier_caz:
                IstoricDesemnare.objects.create(dosar=dosar, utilizator=dosar.grefier_caz, rol='Grefier', data_desemnare=dosar.data_inregistrarii)

            # ==========================================
            # LOGICA NOUĂ: Notificări la Crearea Dosarului
            # ==========================================
            link_dosar = reverse('cases:detalii_dosar', args=[dosar.pk])
            mesaj_nou = f"Ai fost desemnat pe dosarul nou {dosar.numar_unic}."
            
            if dosar.ofiter_caz:
                Notificare.objects.create(utilizator=dosar.ofiter_caz, mesaj=mesaj_nou, link=link_dosar)
            if dosar.procuror_caz:
                Notificare.objects.create(utilizator=dosar.procuror_caz, mesaj=mesaj_nou, link=link_dosar)
            if dosar.grefier_caz:
                Notificare.objects.create(utilizator=dosar.grefier_caz, mesaj=mesaj_nou, link=link_dosar)

            return redirect('cases:detalii_dosar', pk=dosar.pk)
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

    # 1. Memorăm echipa VECHE înainte să fie modificată
    vechi_ofiter = dosar.ofiter_caz
    vechi_procuror = dosar.procuror_caz
    vechi_grefier = dosar.grefier_caz

    # SECURITATE:
    if not dosar.are_drepturi_editare(request.user):
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")
    
    if request.method == 'POST':
        # request.POST conține noile date. 
        # instance=dosar îi spune lui Django: "Nu crea un dosar nou, ci actualizează-l pe acesta!"
        form = DosarForm(request.POST, instance=dosar)
        if form.is_valid():
            # Preluăm data din noul câmp. Dacă grefierul a uitat să o pună, punem automat data de azi.
            data_schimbare = form.cleaned_data.get('data_schimbare_echipa') or date.today()
            
            nou_dosar = form.save() # Salvăm dosarul cu noua echipă

            # 2. Funcție internă care face schimbul curat pentru fiecare rol
            # Funcție internă care face schimbul curat pentru fiecare rol
            def actualizeaza_istoric(rol_nume, vechi_user, nou_user):
                if vechi_user != nou_user:
                    # Dacă exista cineva înainte, îi "închidem" mandatul
                    if vechi_user:
                        IstoricDesemnare.objects.filter(
                            dosar=nou_dosar, utilizator=vechi_user, rol=rol_nume, data_finalizare__isnull=True
                        ).update(data_finalizare=data_schimbare)
                    
                    # Creăm mandatul nou pentru noul venit
                    if nou_user:
                        IstoricDesemnare.objects.create(
                            dosar=nou_dosar, utilizator=nou_user, rol=rol_nume, data_desemnare=data_schimbare
                        )
                        # ==========================================
                        # LOGICA NOUĂ: Notificare pt Noul Venit
                        # ==========================================
                        link_dosar = reverse('cases:detalii_dosar', args=[nou_dosar.pk])
                        Notificare.objects.create(
                            utilizator=nou_user, 
                            mesaj=f"Ai preluat mandatul de {rol_nume} pe dosarul {nou_dosar.numar_unic}.", 
                            link=link_dosar
                        )

            # 3. Executăm verificarea pentru toți 3:
            actualizeaza_istoric('Ofițer', vechi_ofiter, nou_dosar.ofiter_caz)
            actualizeaza_istoric('Procuror', vechi_procuror, nou_dosar.procuror_caz)
            actualizeaza_istoric('Grefier', vechi_grefier, nou_dosar.grefier_caz)
            
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
    if not parte.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
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
    # Corectură: Verificăm drepturile pe dosar
    if not parte.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
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

@login_required
def editare_masura(request, pk):
    masura = get_object_or_404(MasuraPreventiva, pk=pk)
    
    # Securitate: Verificăm drepturile dosarului părinte
    if not masura.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu ai permisiunea de a edita date din acest dosar.")
        
    if request.method == 'POST':
        # Trimitem și `dosar_id` pentru ca formularul să știe să filtreze lista de persoane
        form = MasuraPreventivaForm(request.POST, instance=masura, dosar_id=masura.dosar.pk)
        if form.is_valid():
            form.save()
            return redirect('cases:detalii_dosar', pk=masura.dosar.pk)
    else:
        # Pre-completăm formularul cu datele existente
        form = MasuraPreventivaForm(instance=masura, dosar_id=masura.dosar.pk)
        
    context = {
        'form': form,
        'masura': masura,
        'dosar': masura.dosar
    }
    return render(request, 'cases/editare_masura.html', context)

@login_required
def editare_infractiune(request, pk):
    infractiune = get_object_or_404(Infractiune, pk=pk)
    
    if not infractiune.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu ai permisiunea de a edita date din acest dosar.")
        
    if request.method == 'POST':
        form = InfractiuneForm(request.POST, instance=infractiune)
        if form.is_valid():
            form.save()
            return redirect('cases:detalii_dosar', pk=infractiune.dosar.pk)
    else:
        form = InfractiuneForm(instance=infractiune)
        
    context = {
        'form': form,
        'infractiune': infractiune,
        'dosar': infractiune.dosar
    }
    return render(request, 'cases/editare_infractiune.html', context)

@login_required
def stergere_infractiune(request, pk):
    infractiune = get_object_or_404(Infractiune, pk=pk)
    dosar_id = infractiune.dosar.pk
    
    if not infractiune.dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu ai permisiunea de a șterge date din acest dosar.")
        
    if request.method == 'POST':
        infractiune.delete()
        return redirect('cases:detalii_dosar', pk=dosar_id)
        
    context = {
        'infractiune': infractiune,
        'dosar': infractiune.dosar
    }
    return render(request, 'cases/stergere_infractiune.html', context)

@login_required
def gestionare_stadii(request, pk):
    dosar = get_object_or_404(Dosar, pk=pk)
    
    # Securitate
    if not dosar.are_drepturi_editare(request.user) and not request.user.is_superuser:
        raise PermissionDenied("Nu ai permisiunea de a edita acest dosar.")

    form_stadiu = StadiuCercetareForm()
    form_solutie = SolutieDosarForm()

    if request.method == 'POST':
    # Funcție internă ajutătoare pentru a nu repeta codul de trimitere
        def trimite_notificare_colaborare(mesaj_actiune):
            link_dosar = reverse('cases:detalii_dosar', args=[dosar.pk])
            destinatari = [dosar.ofiter_caz, dosar.procuror_caz, dosar.grefier_caz]
            
            for destinatar in destinatari:
                # Trimitem doar dacă postul e ocupat ȘI utilizatorul nu este cel care a făcut modificarea
                if destinatar and destinatar != request.user:
                    Notificare.objects.create(utilizator=destinatar, mesaj=mesaj_actiune, link=link_dosar)

        # 1. Salvează Stadiu
        if 'salveaza_stadiu' in request.POST:
            stadiu_id = request.POST.get('stadiu_id')
            if stadiu_id:
                stadiu = get_object_or_404(StadiuCercetare, pk=stadiu_id, dosar=dosar)
                form_stadiu = StadiuCercetareForm(request.POST, instance=stadiu)
            else:
                form_stadiu = StadiuCercetareForm(request.POST)
                form_stadiu.instance.dosar = dosar
                
            if form_stadiu.is_valid():
                stadiu_salvat = form_stadiu.save()
                
                # LOGICĂ NOTIFICARE: Citim checkbox-ul
                if form_stadiu.cleaned_data.get('notifica_echipa'):
                    mesaj = f"{request.user.get_full_name() or request.user.username} a adăugat/modificat stadiul ({stadiu_salvat.get_tip_stadiu_display()}) pe dosarul {dosar.numar_unic}."
                    trimite_notificare_colaborare(mesaj)
                    
                return redirect('cases:gestionare_stadii', pk=dosar.pk)

        # 2. Salvează Soluție
        elif 'salveaza_solutie' in request.POST:
            solutie_id = request.POST.get('solutie_id')
            stadiu_parinte_id = request.POST.get('stadiu_parinte_id')
            
            if solutie_id:
                solutie = get_object_or_404(SolutieDosar, pk=solutie_id)
                form_solutie = SolutieDosarForm(request.POST, instance=solutie)
            else:
                form_solutie = SolutieDosarForm(request.POST)
                if stadiu_parinte_id:
                    form_solutie.instance.stadiu_id = stadiu_parinte_id
                    
            if form_solutie.is_valid():
                sol_salvata = form_solutie.save()
                
                # LOGICĂ NOTIFICARE: Citim checkbox-ul
                if form_solutie.cleaned_data.get('notifica_echipa'):
                    mesaj = f"{request.user.get_full_name() or request.user.username} a adăugat/modificat o soluție ({sol_salvata.get_tip_solutie_display()}) pe dosarul {dosar.numar_unic}."
                    trimite_notificare_colaborare(mesaj)
                    
                return redirect('cases:gestionare_stadii', pk=dosar.pk)

        # 3. Șterge Stadiu
        elif 'sterge_stadiu' in request.POST:
            stadiu_id = request.POST.get('stadiu_id')
            if stadiu_id:
                stadiu = get_object_or_404(StadiuCercetare, pk=stadiu_id, dosar=dosar)
                stadiu.delete()
                return redirect('cases:gestionare_stadii', pk=dosar.pk)
                
        # 4. Șterge Soluție
        elif 'sterge_solutie' in request.POST:
            solutie_id = request.POST.get('solutie_id')
            if solutie_id:
                solutie = get_object_or_404(SolutieDosar, pk=solutie_id)
                solutie.delete()
                return redirect('cases:gestionare_stadii', pk=dosar.pk)

    # Preluăm toate stadiile cu soluțiile lor atașate
    stadii = dosar.stadii_cercetare.all().prefetch_related('solutii')

    context = {
        'dosar': dosar,
        'form_stadiu': form_stadiu,
        'form_solutie': form_solutie,
        'stadii': stadii
    }
    return render(request, 'cases/gestionare_stadii.html', context)

@login_required
def citeste_notificare(request, pk):
    # Găsim notificarea (asigurându-ne că e a utilizatorului curent)
    notificare = get_object_or_404(Notificare, pk=pk, utilizator=request.user)
    # O marcăm ca citită
    notificare.citita = True
    notificare.save()
    # Îl redirecționăm către link-ul stocat (ex: /cases/4/)
    return redirect(notificare.link)

@login_required
def sterge_notificare_ajax(request, pk):
    if request.method == 'POST':
        notificare = get_object_or_404(Notificare, pk=pk, utilizator=request.user)
        notificare.citita = True
        notificare.save()
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=400)

@login_required
def generare_rapoarte(request):
    # Optimizare: aducem și infractiunile pentru a nu bloca baza de date
    dosare = Dosar.objects.select_related('ofiter_caz', 'procuror_caz', 'grefier_caz').prefetch_related(
        'stadii_cercetare__solutii',
        'parti_implicate',
        'masuri_preventive',
        'infractiuni' # <--- Adăugat pentru a încărca rapid articolele
    ).all().distinct()
    
    # 1. CAPTURĂM FILTRELE (Criteriile de căutare)
    data_inreg_start = request.GET.get('data_inreg_start')
    data_inreg_end = request.GET.get('data_inreg_end')
    procuror_id = request.GET.get('procuror')
    ofiter_id = request.GET.get('ofiter')
    
    # Filtre noi:
    act_normativ = request.GET.get('act_normativ')
    articol = request.GET.get('articol')
    stadiu = request.GET.get('stadiu')
    solutie = request.GET.get('solutie')
    
    # Aplicăm filtrele
    if data_inreg_start:
        dosare = dosare.filter(data_inregistrarii__gte=data_inreg_start)
    if data_inreg_end:
        dosare = dosare.filter(data_inregistrarii__lte=data_inreg_end)
    if procuror_id:
        dosare = dosare.filter(procuror_caz_id=procuror_id)
    if ofiter_id:
        dosare = dosare.filter(ofiter_caz_id=ofiter_id)
        
    # Aplicăm filtrele noi navigând prin relații
    if act_normativ:
        dosare = dosare.filter(infractiuni__act_normativ=act_normativ)
    if articol:
        dosare = dosare.filter(infractiuni__articol__icontains=articol)
    if stadiu:
        dosare = dosare.filter(stadii_cercetare__tip_stadiu=stadiu)
    if solutie:
        dosare = dosare.filter(stadii_cercetare__solutii__tip_solutie=solutie)

    # 2. CAPTURĂM COLOANELE SELECTATE PENTRU AFIȘARE
    def is_checked(nume_camp, implicit=False):
        if not request.GET: 
            return implicit
        return request.GET.get(nume_camp) == 'on'

    coloane = {
        'col_numar': is_checked('col_numar', True),
        'col_data_inreg': is_checked('col_data_inreg', True),
        
        # Am separat cele două concepte aici:
        'col_situatie_fapt': is_checked('col_situatie_fapt', True), 
        'col_incadrare': is_checked('col_incadrare', True),
        
        'col_ofiter': is_checked('col_ofiter', True),
        'col_procuror': is_checked('col_procuror', True),
        'col_stadiu_curent': is_checked('col_stadiu_curent', True),
        'col_data_stadiu': is_checked('col_data_stadiu', False),
        'col_solutie_finala': is_checked('col_solutie_finala', False),
        'col_data_solutie': is_checked('col_data_solutie', False),
        'col_parti': is_checked('col_parti', False),
        'col_masuri': is_checked('col_masuri', False),
    }

    # ==========================================
    # LOGICA DE EXPORT EXCEL NATIV (.XLSX)
    # ==========================================
    if 'export_excel' in request.GET:
        # 1. Creăm un fișier Excel în memorie
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Raport Dosare"
        
        def curata_text(text):
            if not text: return "-"
            return str(text).replace('\n', ' ').replace('\r', ' ').strip()
        
        # 2. Generăm și scriem Capul de Tabel (Headers)
        headers = []
        if coloane['col_numar']: headers.append("Numar Unic")
        if coloane['col_data_inreg']: headers.append("Data Inreg.")
        if coloane['col_situatie_fapt']: headers.append("Situatie Fapt")
        if coloane['col_incadrare']: headers.append("Incadrare Juridica")
        if coloane['col_ofiter']: headers.append("Ofiter de Caz")
        if coloane['col_procuror']: headers.append("Procuror de Caz")
        if coloane['col_stadiu_curent']: headers.append("Stadiu Curent")
        if coloane['col_data_stadiu']: headers.append("Data Stadiu")
        if coloane['col_solutie_finala']: headers.append("Solutie Finala")
        if coloane['col_data_solutie']: headers.append("Data Solutie")
        if coloane['col_parti']: headers.append("Parti Implicate")
        if coloane['col_masuri']: headers.append("Masuri Preventive")
        
        ws.append(headers)
        
        # Stilizăm capul de tabel (bold și centrat)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.fill = openpyxl.styles.PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
            
        # 3. Scriem datele (Rândurile)
        for dosar in dosare:
            row = []
            stadiu = dosar.stadii_cercetare.first()
            solutie = stadiu.solutii.first() if stadiu else None
            
            if coloane['col_numar']: 
                row.append(curata_text(dosar.numar_unic))
            if coloane['col_data_inreg']: 
                row.append(dosar.data_inregistrarii.strftime("%d.%m.%Y") if dosar.data_inregistrarii else "-")
            if coloane['col_situatie_fapt']: 
                row.append(curata_text(dosar.infractiune_cercetata))
            if coloane['col_incadrare']: 
                incadrari = " | ".join([f"art. {i.articol} - {i.get_act_normativ_display()}" for i in dosar.infractiuni.all()])
                row.append(curata_text(incadrari))
            if coloane['col_ofiter']: 
                row.append(curata_text(dosar.ofiter_caz.get_full_name() if dosar.ofiter_caz else "-"))
            if coloane['col_procuror']: 
                row.append(curata_text(dosar.procuror_caz.get_full_name() if dosar.procuror_caz else "-"))
            if coloane['col_stadiu_curent']: 
                row.append(curata_text(stadiu.get_tip_stadiu_display() if stadiu else "Neinceput"))
            if coloane['col_data_stadiu']: 
                row.append(stadiu.data_incepere.strftime("%d.%m.%Y") if stadiu and stadiu.data_incepere else "-")
            if coloane['col_solutie_finala']: 
                row.append(curata_text(solutie.get_tip_solutie_display() if solutie else "-"))
            if coloane['col_data_solutie']: 
                row.append(solutie.data_solutiei.strftime("%d.%m.%Y") if solutie and solutie.data_solutiei else "-")
            if coloane['col_parti']: 
                parti = " | ".join([f"{p.nume_complet} ({p.get_calitate_procesuala_display()})" for p in dosar.parti_implicate.all()])
                row.append(curata_text(parti))
            if coloane['col_masuri']: 
                masuri = " | ".join([f"{m.get_tip_masura_display()} (exp. {m.data_sfarsit.strftime('%d.%m.%Y')})" for m in dosar.masuri_preventive.all() if m.data_sfarsit])
                row.append(curata_text(masuri))
                
            ws.append(row)
            
        # 4. Ajustăm lățimea coloanelor automat pentru a arăta bine
        for col in ws.columns:
            max_length = 0
            column_letter = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 60) # Limităm lățimea maximă la 60
            ws.column_dimensions[column_letter].width = adjusted_width

        # 5. Salvăm în memoria serverului
        virtual_workbook = io.BytesIO()
        wb.save(virtual_workbook)
        virtual_workbook.seek(0)
        
        # 6. Trimitem fișierul către browser cu formatul corect de .xlsx
        response = HttpResponse(
            virtual_workbook, 
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="Raport_Dosare_{datetime.now().strftime("%Y-%m-%d")}.xlsx"'
        
        return response
    # ==========================================

    # Extragem opțiunile din modele pentru a popula automat dropdown-urile din HTML
    context = {
        'dosare': dosare,
        'coloane': coloane,
        'lista_procurori': User.objects.filter(rol='PROCUROR'),
        'lista_ofiteri': User.objects.filter(rol='POLITIST'),
        'acte_normative': Infractiune._meta.get_field('act_normativ').choices,
        'stadii_choices': StadiuCercetare._meta.get_field('tip_stadiu').choices,
        'solutii_choices': SolutieDosar._meta.get_field('tip_solutie').choices,
    }
    
    return render(request, 'cases/rapoarte.html', context)
import hashlib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from cases.models import Dosar, ParteImplicata, Notificare
from .models import (
    CerereAccesPortal, AccesPortalParte,
    JurnalAccesPortal, genereaza_pin
)
from .forms import (
    CerereAccesForm, LoginPortalForm,
    AprobareCerereForm, RespingereCerereForm
)

# PORTAL PUBLIC (fără @login_required)

def portal_cerere(request):
    """Formularul public de solicitare acces."""
    if request.method == 'POST':
        form = CerereAccesForm(request.POST)
        if form.is_valid():
            dosar = form.cleaned_data['dosar']
            parte = form.cleaned_data['parte']

            cerere = CerereAccesPortal.objects.create(
                dosar=dosar,
                parte=parte,
                nume_solicitant=parte.nume_complet,
                cnp_solicitant=form.cleaned_data['cnp'],
                email_solicitant=form.cleaned_data['email'],
                motiv_solicitare=form.cleaned_data['motiv'],
            )

            # Notificare internă pentru procurorul dosarului
            if dosar.procuror_caz:
                link_cerere = reverse(
                    'cases:detalii_dosar', args=[dosar.pk]
                ) + '#cereri-portal'
                Notificare.objects.create(
                    utilizator=dosar.procuror_caz,
                    mesaj=(
                        f"Cerere nouă de acces portal pentru dosarul "
                        f"{dosar.numar_unic} de la "
                        f"{parte.nume_complet} "
                        f"({parte.get_calitate_procesuala_display()})"
                    ),
                    link=link_cerere
                )

            return render(request, 'portal/cerere_trimisa.html', {
                'dosar_numar': dosar.numar_unic,
                'email': form.cleaned_data['email']
            })
    else:
        form = CerereAccesForm()

    return render(request, 'portal/cerere_acces.html', {'form': form})


def portal_login(request):
    """Autentificarea în portal cu număr dosar + cod + PIN."""
    eroare = None

    if request.method == 'POST':
        form = LoginPortalForm(request.POST)
        if form.is_valid():
            numar_dosar = form.cleaned_data['numar_dosar'].strip().upper()
            cod_acces = form.cleaned_data['cod_acces'].strip().upper()
            pin_introdus = form.cleaned_data['pin'].strip()

            try:
                dosar = Dosar.objects.get(numar_unic=numar_dosar)
                acces = AccesPortalParte.objects.get(
                    cerere__dosar=dosar,
                    cod_acces=cod_acces,
                    activ=True,
                    data_expirare__gte=timezone.now().date()
                )

                # Verificăm PIN-ul (comparat ca hash)
                pin_hash = hashlib.sha256(
                    pin_introdus.encode('utf-8')
                ).hexdigest()

                if acces.pin_hash == pin_hash:
                    # Salvăm în sesiune
                    request.session['portal_acces_id'] = acces.pk
                    request.session['portal_dosar_id'] = dosar.pk

                    # Jurnal
                    JurnalAccesPortal.objects.create(
                        acces=acces,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        sectiune='Autentificare portal'
                    )

                    return redirect('portal:dosar_parte')
                else:
                    eroare = "Date de acces incorecte. Verificați codul și PIN-ul primite prin email."

            except (Dosar.DoesNotExist, AccesPortalParte.DoesNotExist):
                eroare = "Date de acces incorecte sau accesul a expirat."
    else:
        form = LoginPortalForm()

    return render(request, 'portal/login.html', {
        'form': form,
        'eroare': eroare
    })


def portal_dosar(request):
    """Vizualizarea dosarului pentru parte — necesită sesiune activă."""
    acces_id = request.session.get('portal_acces_id')
    if not acces_id:
        return redirect('portal:login')

    acces = get_object_or_404(
        AccesPortalParte,
        pk=acces_id,
        activ=True,
        data_expirare__gte=timezone.now().date()
    )
    dosar = acces.cerere.dosar

    # Jurnal
    JurnalAccesPortal.objects.create(
        acces=acces,
        ip_address=request.META.get('REMOTE_ADDR'),
        sectiune='Vizualizare dosar'
    )

    context = {
        'dosar': dosar,
        'parte': acces.parte,
        'acces': acces,
        'stadiu_curent': dosar.stadiu_curent,
        'solutie_curenta': dosar.solutie_curenta,
        'termene': dosar.termene_procedurale.filter(
            indeplinit=False
        ).order_by('data_limita'),
        'documente': acces.documente_accesibile.all(),
        'data_expirare': acces.data_expirare,
    }

    return render(request, 'portal/dosar_parte.html', context)


def portal_logout(request):
    request.session.flush()
    return redirect('portal:login')


# GESTIONARE INTERNĂ (necesită @login_required)

@login_required
def aprobare_cerere(request, pk):
    """Aprobarea sau respingerea unei cereri — doar procuror."""
    cerere = get_object_or_404(CerereAccesPortal, pk=pk)
    dosar = cerere.dosar

    # Verificăm că e procurorul dosarului sau admin
    utilizator = request.user
    este_procuror_dosar = dosar.procuror_caz == utilizator
    este_admin = utilizator.is_superuser or getattr(utilizator, 'rol', '') == 'ADMIN'

    if not (este_procuror_dosar or este_admin):
        raise PermissionDenied(
            "Doar procurorul dosarului poate procesa cererile de acces portal."
        )

    if cerere.stare != CerereAccesPortal.Stare.IN_ASTEPTARE:
        messages.warning(request, "Această cerere a fost deja procesată.")
        return redirect('cases:detalii_dosar', pk=dosar.pk)

    # Detectăm dacă e făptuitor (acces interzis)
    este_faptuitor = (
        cerere.parte and
        cerere.parte.calitate_procesuala == 'FAPTUITOR'
    )

    if request.method == 'POST':
        actiune = request.POST.get('actiune')

        if actiune == 'respinge':
            form_respingere = RespingereCerereForm(request.POST)
            if form_respingere.is_valid():
                cerere.stare = CerereAccesPortal.Stare.RESPINSA
                cerere.aprobata_de = utilizator
                cerere.data_procesarii = timezone.now()
                cerere.motiv_respingere = form_respingere.cleaned_data['motiv']
                cerere.motiv_respingere_detalii = form_respingere.cleaned_data.get('detalii')
                cerere.save()

                # Email de respingere
                _trimite_email_respingere(cerere)

                messages.success(
                    request,
                    f"Cererea lui {cerere.nume_solicitant} a fost respinsă."
                )
                return redirect('cases:detalii_dosar', pk=dosar.pk)

        elif actiune == 'aproba' and not este_faptuitor:
            form_aprobare = AprobareCerereForm(request.POST, dosar=dosar)
            if form_aprobare.is_valid():
                pin_clar = genereaza_pin()
                pin_hash = hashlib.sha256(
                    pin_clar.encode('utf-8')
                ).hexdigest()

                acces = AccesPortalParte.objects.create(
                    cerere=cerere,
                    parte=cerere.parte,
                    pin_hash=pin_hash,
                    data_expirare=form_aprobare.cleaned_data['data_expirare'],
                )
                acces.documente_accesibile.set(
                    form_aprobare.cleaned_data['documente_selectate']
                )

                cerere.stare = CerereAccesPortal.Stare.APROBATA
                cerere.aprobata_de = utilizator
                cerere.data_procesarii = timezone.now()
                cerere.save()

                # Email cu datele de acces
                _trimite_email_aprobare(cerere, acces, pin_clar)

                messages.success(
                    request,
                    f"Cererea a fost aprobată. Datele de acces au fost "
                    f"trimise la {cerere.email_solicitant}."
                )
                return redirect('cases:detalii_dosar', pk=dosar.pk)

    form_aprobare = AprobareCerereForm(dosar=dosar)
    form_respingere = RespingereCerereForm()

    context = {
        'cerere': cerere,
        'dosar': dosar,
        'form_aprobare': form_aprobare,
        'form_respingere': form_respingere,
        'este_faptuitor': este_faptuitor,
    }
    return render(request, 'portal/aprobare_cerere.html', context)


@login_required
def revocare_acces(request, pk):
    """Revocarea unui acces activ."""
    acces = get_object_or_404(AccesPortalParte, pk=pk)
    dosar = acces.cerere.dosar

    utilizator = request.user
    este_procuror_dosar = dosar.procuror_caz == utilizator
    este_admin = utilizator.is_superuser or getattr(utilizator, 'rol', '') == 'ADMIN'

    if not (este_procuror_dosar or este_admin):
        raise PermissionDenied("Nu aveți permisiunea de a revoca acest acces.")

    if request.method == 'POST':
        acces.activ = False
        acces.save()
        messages.success(
            request,
            f"Accesul lui {acces.parte.nume_complet} a fost revocat."
        )

    return redirect('cases:detalii_dosar', pk=dosar.pk)


# FUNCȚII AJUTĂTOARE EMAIL

def _trimite_email_aprobare(cerere, acces, pin_clar):
    portal_url = settings.SITE_URL + reverse('portal:login')
    mesaj = f"""Stimate/Stimată {cerere.nume_solicitant},

Cererea dumneavoastră de acces la dosarul nr. {cerere.dosar.numar_unic} a fost aprobată.

Date de acces la Portalul Electronic al Dosarelor:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Număr dosar : {cerere.dosar.numar_unic}
  Cod de acces: {acces.cod_acces}
  PIN         : {pin_clar}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Accesul este valabil până la: {acces.data_expirare.strftime('%d.%m.%Y')}
Link portal: {portal_url}

Vă rugăm să nu comunicați aceste date către terți.
Accesul dumneavoastră este înregistrat conform legii.

Cu stimă,
Sistemul Informatic de Evidență a Dosarelor Penale"""

    send_mail(
        subject=f"Acces aprobat - Dosar {cerere.dosar.numar_unic}",
        message=mesaj,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cerere.email_solicitant],
        fail_silently=False,
    )


def _trimite_email_respingere(cerere):
    motiv_display = cerere.get_motiv_respingere_display() if cerere.motiv_respingere else "Nespecificat"
    detalii = f"\nDetalii: {cerere.motiv_respingere_detalii}" if cerere.motiv_respingere_detalii else ""

    mesaj = f"""Stimate/Stimată {cerere.nume_solicitant},

Cererea dumneavoastră de acces la dosarul nr. {cerere.dosar.numar_unic} a fost respinsă.

Motiv: {motiv_display}{detalii}

Dacă apreciaţi că această decizie este eronată, vă puteți adresa direct la sediul parchetului.

Cu stimă,
Sistemul Informatic de Evidență a Dosarelor Penale"""

    send_mail(
        subject=f"Cerere respinsă - Dosar {cerere.dosar.numar_unic}",
        message=mesaj,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[cerere.email_solicitant],
        fail_silently=False,
    )
import qrcode
import urllib.parse
import base64
from io import BytesIO
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_otp.plugins.otp_totp.models import TOTPDevice
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from .models import CustomUser
from django.conf import settings


@login_required
def setup_2fa(request):
    # Găsim sau creăm dispozitivul pentru utilizator
    device, created = TOTPDevice.objects.get_or_create(
        user=request.user, 
        name="default",
        defaults={'confirmed': False}
)
    
    # Dacă formularul a fost trimis (utilizatorul a introdus codul de pe telefon)
    if request.method == 'POST':
        token = request.POST.get('token')
        
        # device.verify_token() face magia matematică și verifică codul
        if device.verify_token(token):
            device.confirmed = True
            device.save()
            
            # Marcăm utilizatorul ca având 2FA activat (dacă ai adăugat câmpul la Pasul 5)
            request.user.totp_activ = True
            request.user.save()
            messages.success(request, "Autentificarea în 2 pași a fost activată cu succes!")
            return redirect('/cases/dashboard/')
        else:
            messages.error(request, "Codul introdus este incorect sau a expirat. Mai încearcă.")

    # Logica pentru GET (generarea codului QR)
    # url = device.config_url
    # url = url.replace('otpauth://totp/', f'otpauth://totp/CMS Penal:{request.user.username}?')

    # Extragem cheia secretă din baza de date în format Base32 (necesar pentru Authenticator)
    secret_b32 = base64.b32encode(device.bin_key).decode('utf-8')
    
    # Formatăm numele care va apărea în aplicația de pe telefon (ex: "CMS Penal: andrei")
    issuer = urllib.parse.quote("CMS Penal")
    account_name = urllib.parse.quote(request.user.username)
    
    # Construim URL-ul standardizat corect
    url = f"otpauth://totp/{issuer}:{account_name}?secret={secret_b32}&issuer={issuer}&digits=6&period=30"

    # Generăm imaginea codului QR în memorie RAM
    qr = qrcode.QRCode(version=1, box_size=8, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Transformăm imaginea în Base64 pentru a o putea trimite direct în HTML
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    context = {
        'qr_code': img_str,
        'device': device,
    }
    return render(request, 'accounts/setup_2fa.html', context)

# 1. FUNCȚIA NOUĂ DE LOGIN
def custom_login(request):
    if request.method == 'POST':
        # Folosim formularul standard Django pentru a valida username-ul și parola
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            
            # Verificăm dacă utilizatorul are 2FA activat (câmpul din modelul CustomUser)
            if hasattr(user, 'totp_activ') and user.totp_activ:
                
                # ---MSesiunea Pending ---
                # NU îl logăm încă. Îi salvăm ID-ul în sesiune și calea "backend"-ului.
                request.session['pending_user_id'] = user.id
                request.session['pending_user_backend'] = user.backend
                
                # Salvăm și parametrul "next" (dacă a vrut să acceseze o anumită pagină)
                if request.GET.get('next'):
                    request.session['next_url'] = request.GET.get('next')
                    
                # Îl trimitem la pagina de introducere a codului de 6 cifre
                return redirect('accounts:verify_2fa')
            else:
                # --- DACĂ NU ARE 2FA ACTIVAT ---
                # Dacă e Procuror sau Admin, îl lăsăm să se logheze dar îl FORȚĂM să-și activeze 2FA
                if user.rol in getattr(settings, 'MANDATORY_2FA_ROLES', []):
                    login(request, user)
                    messages.warning(request, "Atenție! Politica de securitate vă obligă să activați Autentificarea în 2 pași pentru rolul dumneavoastră.")
                    return redirect('accounts:setup_2fa')
                else:
                    # Pentru politisti sau grefieri (dacă nu vrem să fie obligatoriu pentru ei), logare normală
                    login(request, user)
                    next_url = request.GET.get('next', 'cases:dashboard')
                    return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})


# 2. FUNCȚIA CARE VERIFICĂ CODUL LA LOGARE
def verify_2fa(request):
    # Căutăm utilizatorul în "cutia temporară" (sesiune)
    pending_user_id = request.session.get('pending_user_id')
    
    if not pending_user_id:
        # Dacă cineva accesează linkul direct, fără să introducă parola înainte, îl trimitem la login
        return redirect('login')
        
    user = CustomUser.objects.get(id=pending_user_id)
    
    if request.method == 'POST':
        token = request.POST.get('token')
        
        # Căutăm dispozitivul confirmat al acestui utilizator
        from django_otp.plugins.otp_totp.models import TOTPDevice
        device = TOTPDevice.objects.filter(user=user, name="default", confirmed=True).first()
        
        if device and device.verify_token(token):
            # Îi dăm accesul real în platformă.
            user.backend = request.session.get('pending_user_backend') # Restabilim backend-ul
            login(request, user)
            
            # Curățăm datele temporare din sesiune
            del request.session['pending_user_id']
            del request.session['pending_user_backend']
            
            # Verificăm dacă voia să meargă undeva anume înainte de logare
            next_url = request.session.pop('next_url', 'cases:dashboard')
            return redirect(next_url)
            
        else:
            messages.error(request, "Codul introdus este incorect sau a expirat.")
            
    return render(request, 'accounts/verify_2fa.html', {'utilizator': user})
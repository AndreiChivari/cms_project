from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class Force2FAMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Utilizatorii nelogaţi - tratăm prin @login_required)
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 2. Verificăm dacă e un rol cu 2FA obligatoriu și NU îl are activat
        rol_utilizator = getattr(request.user, 'rol', None)
        are_2fa = getattr(request.user, 'totp_activ', False)
        
        if rol_utilizator in getattr(settings, 'MANDATORY_2FA_ROLES', []) and not are_2fa:
            
            # Lista de pagini pe care are voie să le acceseze fără 2FA
            allowed_urls = [
                reverse('accounts:setup_2fa'),
                reverse('logout'),
            ]
            
            # Permitem și încărcarea resurselor statice (CSS, imagini din navbar etc.)
            if request.path.startswith('/static/') or request.path.startswith('/media/'):
                return self.get_response(request)
            
            # Dacă dă click pe orice altă pagină (Dashboard, Dosare, etc.), îl trimitem înapoi la setup 2FA
            if request.path not in allowed_urls:
                return redirect('accounts:setup_2fa')

        # Dacă trece de toate verificările de mai sus, îl lăsăm să acceseze pagina dorită
        return self.get_response(request)
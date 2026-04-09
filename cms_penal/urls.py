"""
URL configuration for cms_penal project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings # pentru a accesa MEDIA_URL
from django.conf.urls.static import static # pentru a servi fișierele
from django.views.generic import RedirectView # pentru redirecționarea de pe /
from django.contrib.auth.views import LogoutView # Importăm Logout pentru a-l avea separat

# Importăm funcția noastră nouă de login din aplicația accounts
from accounts.views import custom_login

urlpatterns = [
    # Redirecționare de la rădăcină ('/') către dashboard
    path('', RedirectView.as_view(url='/cases/dashboard/', permanent=False), name='index'),

    path('admin/', admin.site.urls),
    path('cases/', include('cases.urls')),

    # --- AICI AM FĂCUT MODIFICAREA ---
    # Am înlocuit auth_views.LoginView cu funcția noastră custom_login.
    # Acum, oricine accesează /conturi/login/ trece automat prin verificarea 2FA.
    path('conturi/login/', custom_login, name='login'),

    # Deconectarea (logout) - am adăugat next_page pentru a te trimite la login după ieșire
    path('conturi/logout/', LogoutView.as_view(next_page='/conturi/login/'), name='logout'),

    # Rutele built-in Django rămân active pentru alte funcții (ex. resetare parolă pe viitor)
    path('conturi/', include('django.contrib.auth.urls')),

    # Rutele pentru gestionarea 2FA (activează și verifică) din aplicația accounts
    path('cont/', include('accounts.urls')),
]

# Condiție care adaugă ruta pentru fișiere doar în modul de dezvoltare
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
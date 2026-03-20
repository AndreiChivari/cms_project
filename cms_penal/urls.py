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
from django.conf import settings # Adăugat pentru a accesa MEDIA_URL
from django.conf.urls.static import static # Adăugat pentru a servi fișierele
from django.views.generic import RedirectView #  pentru redirecționarea de pe /
from django.contrib.auth import views as auth_views

urlpatterns = [
    # 1. Rezolvăm eroarea 404: 
    # Oricine intră pe "adresa goală" (/) este trimis la /cases/dashboard/
    path('', RedirectView.as_view(url='/cases/dashboard/', permanent=False), name='index'),

    path('admin/', admin.site.urls),
    path('cases/', include('cases.urls')),

    # Redirect. Dacă utilizatorul e deja logat, va fi trimis spre dashboard (/cases/dashboard/)
    path('conturi/login/', auth_views.LoginView.as_view(
        redirect_authenticated_user=True,
        next_page='/cases/dashboard/' # Aici îi spunem UNDE să-l trimită
    ), name='login'),

    # RUTA NOUĂ PENTRU AUTENTIFICARE
    # Va adăuga automat rute precum /conturi/login/, /conturi/logout/
    path('conturi/', include('django.contrib.auth.urls')),
]

# Această condiție adaugă ruta pentru fișiere doar în modul de dezvoltare (DEBUG = True) / necesar si pentru container LXC
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
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
from django.views.generic import RedirectView #  pentru redirecționarea de pe /
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Redirecționare de la rădăcină ('/') către dashboard
    path('', RedirectView.as_view(url='/cases/dashboard/', permanent=False), name='index'),

    path('admin/', admin.site.urls),
    path('cases/', include('cases.urls')),

    # Ruta după autentificare: dacă încercăm să accesăm pagina de login, dar suntem deja autentificați, vom fi redirecționați către dashboard
    path('conturi/login/', auth_views.LoginView.as_view(
        redirect_authenticated_user=True,
        next_page='/cases/dashboard/'
    ), name='login'),

    # 
    path('conturi/', include('django.contrib.auth.urls')),
]

# Condiție care adaugă ruta pentru fișiere doar în modul de dezvoltare (DEBUG = True) / necesar si pentru container LXC
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
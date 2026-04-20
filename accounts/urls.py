from django.urls import path
from django.urls import path, reverse_lazy # reverse_lazy pentru a direcționa utilizatorul corect de la un pas la altul
from django.contrib.auth import views as auth_views # view-urile native de securitate
from . import views

app_name = 'accounts' # pentru a genera linkuri dinamice

urlpatterns = [
    # Rutele pentru autentificare și 2FA
    path('login/', views.custom_login, name='login'),
    path('2fa/verifica/', views.verify_2fa, name='verify_2fa'),
    path('2fa/activeaza/', views.setup_2fa, name='setup_2fa'),

    # Ruta pentru schimbarea parolei (view-urile native Django, dar cu template-uri personalizate)
    path('parola/schimba/', auth_views.PasswordChangeView.as_view(
        template_name='accounts/schimba_parola.html',
        success_url='/cont/parola/schimba/succes/'
    ), name='schimba_parola'),
    
    path('parola/schimba/succes/', auth_views.PasswordChangeDoneView.as_view(
        template_name='accounts/schimba_parola_succes.html'
    ), name='schimba_parola_succes'),

    # Rute pentru resetarea parolei
    # 1. Formularul unde introducem adresa de email
    path('parola/resetare/', auth_views.PasswordResetView.as_view(
        template_name='accounts/resetare_parola.html',
        email_template_name='accounts/email_resetare_parola.html', # Conținutul email-ului
        subject_template_name='accounts/email_resetare_parola_subiect.txt', # Titlul email-ului
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),

    # 2. Pagina care afişează "Verifică-ți mailul"
    path('parola/resetare/trimis/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/resetare_parola_trimis.html'
    ), name='password_reset_done'),

    # 3. Pagina unde utilizatorul introduce noua parolă (ajunge aici din link-ul de pe email)
    path('parola/resetare/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/resetare_parola_confirmare.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),

    # 4. Mesajul de succes final
    path('parola/resetare/finalizat/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/resetare_parola_complet.html'
    ), name='password_reset_complete'),
]
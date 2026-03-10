from django.urls import path
from . import views

app_name = 'cases' # Util pentru a genera linkuri dinamice mai târziu

urlpatterns = [
    # Adăugăm ruta pentru dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Această rută reprezintă adresa de bază: http://127.0.0.1:8000/cases/
    path('', views.lista_dosare, name='lista_dosare'),

    # Ruta pentru ADAUGARE
    path('adauga/', views.adaugare_dosar, name='adaugare_dosar'), # <--- RUTA NOUĂ AICI

    # Ruta NOUĂ pentru detaliile unui singur dosar
    # <int:pk> îi spune lui Django să aștepte un număr întreg (Primary Key) în URL
    path('<int:pk>/', views.detalii_dosar, name='detalii_dosar'),

    # RUTA NOUĂ PENTRU PDF:
    path('<int:pk>/pdf/', views.generare_pdf_dosar, name='generare_pdf_dosar'),

    # Ruta NOUĂ pentru editare: ex. /cases/1/editeaza/
    path('<int:pk>/editeaza/', views.editare_dosar, name='editare_dosar'),

    # Rutele NOI pentru Părți Implicate
    # Observă că aici folosim ID-ul persoanei (pk), nu al dosarului
    path('parte/<int:pk>/editeaza/', views.editare_parte, name='editare_parte'),
    path('parte/<int:pk>/sterge/', views.stergere_parte, name='stergere_parte'),

    # Rutele NOI pentru Documente
    path('document/<int:pk>/editeaza/', views.editare_document, name='editare_document'),
    path('document/<int:pk>/sterge/', views.stergere_document, name='stergere_document'),

    # Rute noi pentru stergerea si modificarea masurilor
    path('masura/<int:pk>/sterge/', views.stergere_masura, name='stergere_masura'),
    path('masura/<int:pk>/editeaza/', views.editare_masura, name='editare_masura'),

    # Rute pentru actiunile Infracțiunii
    path('infractiune/<int:pk>/editeaza/', views.editare_infractiune, name='editare_infractiune'),
    path('infractiune/<int:pk>/sterge/', views.stergere_infractiune, name='stergere_infractiune'),

    # Ruta pentru gestionarea stadiilor
    path('<int:pk>/stadii/', views.gestionare_stadii, name='gestionare_stadii'),

    # Ruta pentru notificari
    path('notificare/<int:pk>/', views.citeste_notificare, name='citeste_notificare'),

    # Ruta pentru stergerea notificarilor
    path('notificare/sterge/<int:pk>/', views.sterge_notificare_ajax, name='sterge_notificare_ajax'),
]
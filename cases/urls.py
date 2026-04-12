from django.urls import path
from . import views

app_name = 'cases' # pentru a genera linkuri dinamice 

urlpatterns = [
    # Adăugăm ruta pentru dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Această rută reprezintă adresa de bază: http://127.0.0.1:8000/cases/
    path('', views.lista_dosare, name='lista_dosare'),

    # Ruta pentru ADAUGARE
    path('adauga/', views.adaugare_dosar, name='adaugare_dosar'),

    # Ruta  pentru detaliile unui singur dosar
    # <int:pk> - (Primary Key) în URL
    path('<int:pk>/', views.detalii_dosar, name='detalii_dosar'),

    # RUTA PENTRU PDF
    path('<int:pk>/pdf/', views.generare_pdf_dosar, name='generare_pdf_dosar'),

    # Ruta pentru editare: ex. /cases/1/editeaza/
    path('<int:pk>/editeaza/', views.editare_dosar, name='editare_dosar'),

    # Rutele pentru Părți Implicate
    path('parte/<int:pk>/editeaza/', views.editare_parte, name='editare_parte'),
    path('parte/<int:pk>/sterge/', views.stergere_parte, name='stergere_parte'),

    # Rutele pentru Documente
    path('document/<int:pk>/editeaza/', views.editare_document, name='editare_document'),
    path('document/<int:pk>/sterge/', views.stergere_document, name='stergere_document'),

    # Rute pentru stergerea si modificarea masurilor
    path('masura/<int:pk>/sterge/', views.stergere_masura, name='stergere_masura'),
    path('masura/<int:pk>/editeaza/', views.editare_masura, name='editare_masura'),

    # Rute pentru termene procedurale
    path('termen/<int:pk>/editeaza/', views.editare_termen, name='editare_termen'),
    path('termen/<int:pk>/sterge/', views.stergere_termen, name='stergere_termen'),

    # Rute pentru actiunile Infracțiunii
    path('infractiune/<int:pk>/editeaza/', views.editare_infractiune, name='editare_infractiune'),
    path('infractiune/<int:pk>/sterge/', views.stergere_infractiune, name='stergere_infractiune'),

    # Ruta pentru gestionarea stadiilor
    path('<int:pk>/stadii/', views.gestionare_stadii, name='gestionare_stadii'),

    # Ruta pentru notificari
    path('notificare/<int:pk>/', views.citeste_notificare, name='citeste_notificare'),

    # Ruta pentru stergerea notificarilor
    path('notificare/sterge/<int:pk>/', views.sterge_notificare_ajax, name='sterge_notificare_ajax'),

    # Ruta pentru rapoarte
    path('rapoarte/', views.generare_rapoarte, name='rapoarte'),

    # Ruta pentru stergerea unui membru
    path('istoric-echipa/<int:pk>/sterge/', views.stergere_istoric_echipa, name='stergere_istoric_echipa'),

    # Ruta pentru harta infractionalitatii
    path('harta/', views.harta_infractionalitatii, name='harta'),

    # Ruta pentru testarea API-ului OCR
    path('api/test-ocr/', views.test_ocr_api, name='test_ocr_api'),

    # Ruta pentru interfața grafică OCR de test (pagina HTML)
    path('test-ocr/', views.pagina_test_ocr, name='pagina_test_ocr'),

    # Ruta pentru analiza relațională
    path('analiza-conexiuni/', views.graf_relational, name='graf_relational'),
    path('api/graf-relational/', views.date_graf_relational, name='api_graf_relational'),

    # Ruta pentru procesarului formularului din modal
    path('dosar/<int:pk>/genereaza-act/', views.genereaza_act, name='genereaza_act'),

    # Ruta pentru semnarea digitală a actelor
    path('act/<int:pk_act>/semneaza/', views.semneaza_act, name='semneaza_act'),

    # Rute pentru Calendar
    path('calendar/', views.calendar_view, name='calendar'), # Pagina HTML
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'), # Datele JSON pentru API-un api_calendar_events din views.py
    path('calendar/adauga/', views.adaugare_termen_calendar, name='adaugare_termen_calendar'),
]
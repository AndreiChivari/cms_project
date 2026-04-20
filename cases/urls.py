from django.urls import include, path
from . import views

app_name = 'cases' # pentru a genera linkuri dinamice 

urlpatterns = [
    # Ruta pentru Dashboard - Afișează panoul de control principal
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Ruta pentru adresa de bază - Lista tuturor dosarelor
    path('', views.lista_dosare, name='lista_dosare'),

    # Ruta pentru adăugarea unui Dosar
    path('adauga/', views.adaugare_dosar, name='adaugare_dosar'),

    # Ruta pentru editarea unui Dosar
    path('<int:pk>/editeaza/', views.editare_dosar, name='editare_dosar'),

    # Ruta pentru detaliile unui singur Dosar - Afișează informații complete despre dosar
    path('<int:pk>/', views.detalii_dosar, name='detalii_dosar'),

    # Ruta pentru PDF - Generează și descarcă PDF-ul dosarului
    path('<int:pk>/pdf/', views.generare_pdf_dosar, name='generare_pdf_dosar'),

    # Rutele pentru Părțile implicate - Editare și ștergere a unei persoane din dosar
    path('parte/<int:pk>/editeaza/', views.editare_parte, name='editare_parte'),
    path('parte/<int:pk>/sterge/', views.stergere_parte, name='stergere_parte'),

    # Rutele pentru Documente - Editare și ștergere a documentelor atașate
    path('document/<int:pk>/editeaza/', views.editare_document, name='editare_document'),
    path('document/<int:pk>/sterge/', views.stergere_document, name='stergere_document'),

    # Rute pentru stergerea si modificarea Măsurilor preventive - Gestionarea măsurilor preventive
    path('masura/<int:pk>/sterge/', views.stergere_masura, name='stergere_masura'),
    path('masura/<int:pk>/editeaza/', views.editare_masura, name='editare_masura'),

    # Rute pentru Termene procedurale - Editare și ștergere a termenelor
    path('termen/<int:pk>/editeaza/', views.editare_termen, name='editare_termen'),
    path('termen/<int:pk>/sterge/', views.stergere_termen, name='stergere_termen'),

    # Rute pentru actiunile Infracțiunii - Editare și ștergere a infracțiunilor
    path('infractiune/<int:pk>/editeaza/', views.editare_infractiune, name='editare_infractiune'),
    path('infractiune/<int:pk>/sterge/', views.stergere_infractiune, name='stergere_infractiune'),

    # Ruta pentru gestionarea stadiilor - Gestionează stadiile de cercetare ale dosarului
    path('<int:pk>/stadii/', views.gestionare_stadii, name='gestionare_stadii'),

    # Ruta pentru notificări - Marchează o notificare ca citită
    path('notificare/<int:pk>/', views.citeste_notificare, name='citeste_notificare'),

    # Ruta pentru ştergerea notificărilor - Ștergere asincronă a notificării
    path('notificare/sterge/<int:pk>/', views.sterge_notificare_ajax, name='sterge_notificare_ajax'),

    # Ruta pentru Rapoarte - Generează rapoarte pe baza dosarelor
    path('rapoarte/', views.generare_rapoarte, name='rapoarte'),

    # Ruta pentru ştergerea unui membru - Ștergere din istoricul de desemnări
    path('istoric-echipa/<int:pk>/sterge/', views.stergere_istoric_echipa, name='stergere_istoric_echipa'),

    # Ruta pentru harta infractionalitatii - Afișează harta cu infracțiunile localizate
    path('harta/', views.harta_infractionalitatii, name='harta'),

    # Ruta pentru testarea API-ului OCR - API endpoint pentru funcționalitatea OCR
    path('api/test-ocr/', views.test_ocr_api, name='test_ocr_api'),

    # Ruta pentru interfața grafică OCR de test - Pagina HTML pentru testare OCR
    path('test-ocr/', views.pagina_test_ocr, name='pagina_test_ocr'),

    # Ruta pentru Analiza relațională - Graful de relații și API pentru date
    path('analiza-conexiuni/', views.graf_relational, name='graf_relational'),
    path('api/graf-relational/', views.date_graf_relational, name='api_graf_relational'),

    # Ruta pentru generarea Actelor procedurale
    path('dosar/<int:pk>/genereaza-act/', views.genereaza_act, name='genereaza_act'),

    # Ruta pentru Semnarea digitală a actelor 
    path('act/<int:pk_act>/semneaza/', views.semneaza_act, name='semneaza_act'),

    # Ruta pentru descărcarea documentelor - Descarcă documentul (original sau semnat)
    path('document/<int:pk>/descarca/<str:tip_fisier>/', views.descarca_document, name='descarca_document'),

    # Rute pentru Calendar - Afișează calendarul cu termene și măsuri preventive
    path('calendar/', views.calendar_view, name='calendar'), # Pagina HTML
    path('api/calendar-events/', views.api_calendar_events, name='api_calendar_events'),
    path('calendar/adauga/', views.adaugare_termen_calendar, name='adaugare_termen_calendar'),

    # Ruta pentru toggle îndeplinit termen procedural - Marchează/demarchează termen ca îndeplinit
    path('calendar/termen/<int:pk>/toggle/', views.toggle_termen_indeplinit, name='toggle_termen_indeplinit'),

    # Ruta pentru toggle îndeplinit măsură - Marchează/demarchează măsură ca îndeplinită
    path('calendar/masura/<int:pk>/toggle/', views.toggle_masura_indeplinita, name='toggle_masura_indeplinita'),
]
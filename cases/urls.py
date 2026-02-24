from django.urls import path
from . import views

app_name = 'cases' # Util pentru a genera linkuri dinamice mai târziu

urlpatterns = [
    # Această rută reprezintă adresa de bază: http://127.0.0.1:8000/cases/
    path('', views.lista_dosare, name='lista_dosare'),

    # Ruta NOUĂ pentru detaliile unui singur dosar
    # <int:pk> îi spune lui Django să aștepte un număr întreg (Primary Key) în URL
    path('<int:pk>/', views.detalii_dosar, name='detalii_dosar'),
]
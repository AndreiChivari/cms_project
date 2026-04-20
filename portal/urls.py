from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.portal_login, name='login'),
    path('cerere/', views.portal_cerere, name='cerere'),
    path('dosar/', views.portal_dosar, name='dosar_parte'),
    path('logout/', views.portal_logout, name='logout'),
    path('cerere/<int:pk>/procesa/', views.aprobare_cerere, name='aprobare_cerere'),
    path('acces/<int:pk>/revocare/', views.revocare_acces, name='revocare_acces'),
]
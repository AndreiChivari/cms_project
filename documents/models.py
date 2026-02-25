from django.db import models
from django.conf import settings
from cases.models import Dosar

class ActUrmarire(models.Model):
    class TipDocument(models.TextChoices):
        ORDONANTA = 'ORDONANTA', 'Ordonanță'
        REFERAT = 'REFERAT', 'Referat'
        DECLARATIE = 'DECLARATIE', 'Declarație'
        PROCES_VERBAL = 'PROCES_VERBAL', 'Proces-Verbal'
        ALTUL = 'ALTUL', 'Alt tip de act'

    # Titlul documentului (ex: Ordonanță de reținere pt 24h)
    titlu = models.CharField(max_length=255)
    tip = models.CharField(max_length=20, choices=TipDocument.choices, default=TipDocument.ORDONANTA)
    
    # Legătura cu dosarul penal (un dosar poate avea mai multe acte)
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='documente')
    
    # Cine a încărcat/emis documentul
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Aici se salvează efectiv fișierul. 'upload_to' creează foldere automat în funcție de an și lună!
    fisier = models.FileField(upload_to='acte_penale/%Y/%m/')
    
    data_incarcarii = models.DateTimeField(auto_now_add=True)
    descriere_scurta = models.TextField(blank=True, null=True, help_text="Rezumatul actului (opțional)")

    class Meta:
        verbose_name = "Act de Urmărire Penală"
        verbose_name_plural = "Acte de Urmărire Penală"
        ordering = ['-data_incarcarii']

    def __str__(self):
        return f"{self.get_tip_display()} - {self.titlu} ({self.dosar.numar_unic})"
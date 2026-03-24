from django.db import models
from django.conf import settings
from cases.models import Dosar
from django.utils import timezone # Pentru a putea modifica data inregistrarii

class ActUrmarire(models.Model):
    class TipDocument(models.TextChoices):
        ORDONANTA = 'ORDONANTA', 'Ordonanță'
        REFERAT = 'REFERAT', 'Referat'
        DECLARATIE = 'DECLARATIE', 'Declarație'
        PROCES_VERBAL = 'PROCES_VERBAL', 'Proces-Verbal'
        ALTUL = 'ALTUL', 'Alt tip de act'

    # Titlul documentului (ex: Ordonanță de reținere pt 24h)
    titlu = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Lăsați gol dacă titlul coincide cu tipul documentului"
    )

# ==========================================
    # CÂMPURI NOI PENTRU DATE COMPLETE
    # ==========================================
    data_documentului = models.DateField(
        default=timezone.now,
        verbose_name="Data emiterii documentului",
        help_text="Data emiterii/întocmirii documentului"
    )
    
    data_inregistrarii = models.DateField(
        default=timezone.now,
        verbose_name="Data înregistrării",
        help_text="Data atribuirii numărului de intrare/înregistrare"
    )

    tip = models.CharField(max_length=50, choices=TipDocument.choices, default=TipDocument.ORDONANTA)
    
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

    def are_drepturi_editare(self, utilizator):
        # 1. Dacă utilizatorul este cel care a încărcat documentul, are voie
        if self.autor == utilizator:
            return True
            
        # 2. Dacă utilizatorul face parte din echipa curentă a dosarului, are voie
        echipa = [self.dosar.ofiter_caz, self.dosar.procuror_caz, self.dosar.grefier_caz]
        if utilizator in echipa:
            return True
            
        # Altfel, nu are drepturi
        return False
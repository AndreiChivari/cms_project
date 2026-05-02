from django.db import models
from django.conf import settings
from cases.models import Dosar
from django.utils import timezone
import os
import uuid
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# REGULILE DE GESTIONARE A DOCUMENTELOR ÎNCĂRCATE

# Regulile de denumire a fișierelor
def cale_upload_document(instance, filename):
    """
    Generează o cale unică și sigură pentru fiecare fișier încărcat.
    Format: documente/dosar_<ID>/<UUID>.<extensie>
    """
    ext = filename.split('.')[-1].lower() # Extragem extensia (ex: 'pdf')
    nume_nou = f"{uuid.uuid4().hex}.{ext}" # Generăm un șir unic de 32 caractere
    
    # Organizăm fișierele în foldere specifice fiecărui dosar pentru ordine
    folder_dosar = f"dosar_{instance.dosar.id}" if instance.dosar else "nesortate"
    
    return os.path.join('documente', folder_dosar, nume_nou)

# Validarea tipului de fișier
def valideaza_extensie_document(value):
    """ Stabileşte formatul fişierelor permise la încărcare. """
    extensii_permise = ['.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png']
    ext = os.path.splitext(value.name)[1].lower()
    
    if ext not in extensii_permise:
        raise ValidationError(f"Format neacceptat: {ext}. Fișierele permise sunt: PDF, DOC, DOCX, JPG, PNG.")

# Verificarea dimensiunii fişierelor
def valideaza_dimensiune_document(value):
    """Limitează mărimea fișierului la 10 MB pentru a preveni umplerea serverului."""
    limita_mb = 10
    if value.size > limita_mb * 1024 * 1024:
        raise ValidationError(f"Fișierul este prea mare ({value.size // (1024*1024)}MB). Limita maximă este de {limita_mb}MB.")

class ActUrmarire(models.Model):
    class TipDocument(models.TextChoices):
        ORDONANTA = 'ORDONANTA', 'Ordonanță'
        REFERAT = 'REFERAT', 'Referat'
        DECLARATIE = 'DECLARATIE', 'Declarație'
        PROCES_VERBAL = 'PROCES_VERBAL', 'Proces-Verbal'
        ALTUL = 'ALTUL', 'Alt tip de act'

    titlu = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text="Lăsați gol dacă titlul coincide cu tipul documentului"
    )
    # Data emiterii și data înregistrării pot fi diferite
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

    # Tipul documentului (ex: Ordonanță, Referat etc.)
    tip = models.CharField(max_length=50, choices=TipDocument.choices, default=TipDocument.ORDONANTA)
    
    # Legătura cu dosarul penal (un dosar poate avea mai multe acte)
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='documente')
    
    # Cine a încărcat/emis documentul
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    # Fișierul încărcat - cu regulile de denumire și validare
    fisier = models.FileField(
        upload_to=cale_upload_document, # funcția de denumire
        validators=[valideaza_extensie_document, valideaza_dimensiune_document], # restricțiile
        verbose_name="Fișier Document"
    )
    
    data_incarcarii = models.DateTimeField(auto_now_add=True)
    descriere_scurta = models.TextField(blank=True, null=True, help_text="Rezumatul actului (opțional)")

    # GESTIONAREA SEMNĂTURILOR DIGITALE
    fisier_semnat = models.FileField(
        upload_to='documente/semnate/%Y/%m/', 
        null=True, blank=True,
        help_text="Varianta finală, securizată cu semnătură digitală"
    )
    este_semnat = models.BooleanField(default=False)
    semnat_de = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='acte_semnate_de_mine'
    )
    data_semnarii = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Act de Urmărire Penală"
        verbose_name_plural = "Acte de Urmărire Penală"
        ordering = ['-data_incarcarii']

    def __str__(self):
        return f"{self.get_tip_display()} - {self.titlu} ({self.dosar.numar_unic})"

    def are_drepturi_editare(self, utilizator):
        # 1. Utlizatorul care a încărcat documentul are drepturi de editare
        if self.autor == utilizator:
            return True
            
        # 2. Utilizatorul care face parte din echipa curentă a dosarului are drepturi de editare
        echipa = [self.dosar.ofiter_caz, self.dosar.procuror_caz, self.dosar.grefier_caz]
        if utilizator in echipa:
            return True
            
        # 3. Ceilalți utilizatori nu au drepturi de editare (nici adminul nu are drepturi, pentru a proteja integritatea documentelor)
        return False
    
class TrimiterePrinEmail(models.Model):
    document = models.ForeignKey(
        ActUrmarire,
        on_delete=models.CASCADE,
        related_name='trimiteri_email'
    )
    trimis_de = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='emailuri_trimise'
    )
    trimis_la = models.DateTimeField(auto_now_add=True)
    email_destinatar = models.EmailField()
    nume_destinatar = models.CharField(max_length=200)
    subiect = models.CharField(max_length=255)
    mesaj = models.TextField(blank=True)
    reusit = models.BooleanField(default=True)
    varianta_trimisa = models.CharField(
        max_length=10,
        choices=[('original', 'Original'), ('semnat', 'Semnat')],
        default='original'
    )

    class Meta:
        verbose_name = "Trimitere email document"
        verbose_name_plural = "Trimiteri email documente"
        ordering = ['-trimis_la']

    def __str__(self):
        return f"{self.document.titlu} → {self.email_destinatar} ({self.trimis_la.strftime('%d.%m.%Y')})"
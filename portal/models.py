import secrets
from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from cases.models import Dosar, ParteImplicata
from documents.models import ActUrmarire


def genereaza_cod():
    import string
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(4))


def genereaza_pin():
    return str(secrets.randbelow(9000) + 1000)


class CerereAccesPortal(models.Model):
    class Stare(models.TextChoices):
        IN_ASTEPTARE = 'IN_ASTEPTARE', 'În așteptare'
        APROBATA = 'APROBATA', 'Aprobată'
        RESPINSA = 'RESPINSA', 'Respinsă'

    class MotivRespingere(models.TextChoices):
        CALITATE = 'CALITATE', 'Calitate procesuală incompatibilă cu accesul la dosar'
        FAZA = 'FAZA', 'Dosarul se află într-o fază incompatibilă cu consultarea'
        INCOMPLETE = 'INCOMPLETE', 'Date de identificare incomplete sau incorecte'
        ALTUL = 'ALTUL', 'Alt motiv'

    dosar = models.ForeignKey(
        Dosar, on_delete=models.CASCADE,
        related_name='cereri_acces_portal'
    )
    parte = models.ForeignKey(
        ParteImplicata, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cereri_acces_portal',
        help_text="Completat automat la validarea CNP-ului"
    )
    nume_solicitant = models.CharField(max_length=200)
    cnp_solicitant = models.CharField(max_length=13)
    email_solicitant = models.EmailField()
    motiv_solicitare = models.TextField(
        verbose_name="Motivul solicitării",
        help_text="Descrieți pe scurt motivul pentru care solicitați accesul la dosar"
    )
    data_cererii = models.DateTimeField(auto_now_add=True)

    stare = models.CharField(
        max_length=20,
        choices=Stare.choices,
        default=Stare.IN_ASTEPTARE
    )
    aprobata_de = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='cereri_portal_procesate'
    )
    data_procesarii = models.DateTimeField(null=True, blank=True)
    motiv_respingere = models.CharField(
        max_length=20,
        choices=MotivRespingere.choices,
        null=True, blank=True
    )
    motiv_respingere_detalii = models.TextField(
        null=True, blank=True,
        verbose_name="Detalii suplimentare (opțional)"
    )

    history = HistoricalRecords(verbose_name="Istoric Cerere Portal")

    class Meta:
        verbose_name = "Cerere Acces Portal"
        verbose_name_plural = "Cereri Acces Portal"
        ordering = ['-data_cererii']

    def __str__(self):
        return f"Cerere {self.nume_solicitant} - {self.dosar.numar_unic} [{self.get_stare_display()}]"


class AccesPortalParte(models.Model):
    cerere = models.OneToOneField(
        CerereAccesPortal,
        on_delete=models.CASCADE,
        related_name='acces_generat'
    )
    parte = models.ForeignKey(
        ParteImplicata,
        on_delete=models.CASCADE,
        related_name='acces_portal'
    )
    documente_accesibile = models.ManyToManyField(
        ActUrmarire,
        blank=True,
        related_name='accese_portal',
        verbose_name="Documente accesibile"
    )
    cod_acces = models.CharField(
        max_length=20, unique=True,
        default=genereaza_cod
    )
    pin_hash = models.CharField(max_length=128)
    data_expirare = models.DateField()
    activ = models.BooleanField(default=True)

    history = HistoricalRecords(verbose_name="Istoric Acces Portal")

    class Meta:
        verbose_name = "Acces Portal Parte"
        verbose_name_plural = "Accese Portal Părți"

    def __str__(self):
        return f"Acces {self.parte.nume_complet} - {self.cerere.dosar.numar_unic}"


class JurnalAccesPortal(models.Model):
    acces = models.ForeignKey(
        AccesPortalParte,
        on_delete=models.CASCADE,
        related_name='jurnal'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    sectiune = models.CharField(max_length=100, default='Vizualizare dosar')

    class Meta:
        verbose_name = "Jurnal Acces Portal"
        verbose_name_plural = "Jurnal Accese Portal"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.acces.parte.nume_complet} - {self.timestamp:%d.%m.%Y %H:%M}"
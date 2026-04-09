from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # Definim opțiunile pentru roluri folosind TextChoices (foarte elegant și ușor de citit)
    class Role(models.TextChoices):
        PROCUROR = 'PROCUROR', 'Procuror'
        POLITIST = 'POLITIST', 'Ofițer de Poliție Judiciară'
        GREFIER = 'GREFIER', 'Grefier'
        ADMIN = 'ADMIN', 'Administrator Sistem'

    # Adăugăm noile noastre câmpuri
    rol = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.POLITIST,
        help_text="Rolul utilizatorului în sistemul de management al dosarelor."
    )
    
    grad_profesional = models.CharField(
        max_length=100, 
        blank=True, 
        null=True,
        help_text="Ex: Inspector principal, Comisar șef"
    )
    
    unitate = models.CharField(
        max_length=150, 
        blank=True, 
        null=True,
        help_text="Ex: Parchetul de pe lângă Judecătoria Sector 1 / SIC Brașov"
    )

    totp_activ = models.BooleanField(default=False, verbose_name="2FA Activ")

    def __str__(self):
        # Așa va fi afișat utilizatorul în panoul de administrare
        nume_complet = self.get_full_name()
        if nume_complet:
            return f"{nume_complet} ({self.get_rol_display()} - {self.unitate})"
        return f"{self.username} ({self.get_rol_display()})"
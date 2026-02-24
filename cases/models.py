from django.db import models
from django.conf import settings # Folosim asta pentru a importa modelul de User corect

class Dosar(models.Model):
    class Stadiu(models.TextChoices):
        IN_LUCRU = 'IN_LUCRU', 'În lucru la Poliție'
        LA_PROCUROR = 'LA_PROCUROR', 'Înaintat la Procuror'
        CLASAT = 'CLASAT', 'Clasat'
        TRIMIS_IN_JUDECATA = 'TRIMIS_IN_JUDECATA', 'Trimis în judecată'
        SUSPENDAT = 'SUSPENDAT', 'Suspendat'

    # Datele de identificare ale dosarului
    numar_unic = models.CharField(max_length=50, unique=True, help_text="Ex: 123/P/2026")
    data_inregistrarii = models.DateField(auto_now_add=True) # Se completează automat la creare
    infractiune_cercetata = models.TextField(help_text="Descrierea faptei și încadrarea juridică (ex: Furt calificat, art. 229 C.pen)")
    
    stadiu = models.CharField(max_length=20, choices=Stadiu.choices, default=Stadiu.IN_LUCRU)

    # Legătura cu anchetatorii (Chei externe către modelul de Utilizator)
    # Folosim related_name pentru a putea accesa ulterior toate dosarele unui polițist cu: politist.dosare_instrumentate.all()
    ofiter_caz = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='dosare_instrumentate'
    )
    
    procuror_caz = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='dosare_supravegheate'
    )

    class Meta:
        verbose_name = "Dosar Penal"
        verbose_name_plural = "Dosare Penale"
        ordering = ['-data_inregistrarii'] # Sortează descrescător după dată

    def __str__(self):
        return f"Dosar nr. {self.numar_unic}"


class ParteImplicata(models.Model):
    class Calitate(models.TextChoices):
        SUSPECT = 'SUSPECT', 'Suspect'
        INCULPAT = 'INCULPAT', 'Inculpat'
        PARTE_VATAMATA = 'PARTE_VATAMATA', 'Parte Vătămată'
        PARTE_CIVILA = 'PARTE_CIVILA', 'Parte Civilă'
        MARTOR = 'MARTOR', 'Martor'

    # Legătura către dosar. Când un dosar e șters, se șterg și părțile implicate din el (CASCADE)
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='parti_implicate')
    
    nume_complet = models.CharField(max_length=150)
    cnp = models.CharField(max_length=13, blank=True, null=True, verbose_name="CNP")
    calitate_procesuala = models.CharField(max_length=20, choices=Calitate.choices)
    mentiuni = models.TextField(blank=True, null=True, help_text="Alte date de contact, antecedente, etc.")

    class Meta:
        verbose_name = "Parte Implicată"
        verbose_name_plural = "Părți Implicate"

    def __str__(self):
        return f"{self.nume_complet} ({self.get_calitate_procesuala_display()}) - {self.dosar.numar_unic}"
from django.db import models
from django.conf import settings # Folosim asta pentru a importa modelul de User corect
from datetime import date # Folosim pentru calculul alertelor

class Dosar(models.Model):
# 1. Rescriem stadiile (doar 3 variante)
    class Stadiu(models.TextChoices):
        POLITIE = 'POLITIE', 'În lucru la Poliție'
        PROCUROR = 'PROCUROR', 'În lucru la Procuror'
        SOLUTIONAT = 'SOLUTIONAT', 'Soluționat'

    # 2. Creăm variantele pentru soluții/propuneri
    class Solutie(models.TextChoices):
        TRIMITERE = 'TRIMITERE', 'Trimitere în judecată'
        CLASARE = 'CLASARE', 'Clasare'
        RENUNTARE = 'RENUNTARE', 'Renunțare la urmărirea penală'
        DECLINARE = 'DECLINARE', 'Declinare'
        SUSPENDARE = 'SUSPENDARE', 'Suspendare'
        TRECERE = 'TRECERE', 'Trecere la alt organ'

    # Datele de identificare ale dosarului
    numar_unic = models.CharField(max_length=50, unique=True, help_text="Ex: 123/P/2026")
    data_inregistrarii = models.DateField(auto_now_add=True) # Se completează automat la creare
    infractiune_cercetata = models.TextField(help_text="Descrierea faptei și încadrarea juridică (ex: Furt calificat, art. 229 C.pen)")
    
    # 3. Actualizăm coloana stadiu
    stadiu = models.CharField(
        max_length=20, 
        choices=Stadiu.choices, 
        default=Stadiu.POLITIE
    )
    
    # 4. Adăugăm coloanele noi
    tip_solutie = models.CharField(
        max_length=20, 
        choices=Solutie.choices, 
        null=True, 
        blank=True
    )
    data_solutiei = models.DateField(null=True, blank=True)

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

    # --- CÂMPUL NOU ---
    grefier_caz = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='dosare_gestionate'
    )

    class Meta:
        verbose_name = "Dosar Penal"
        verbose_name_plural = "Dosare Penale"
        ordering = ['-data_inregistrarii'] # Sortează descrescător după dată

    def are_drepturi_editare(self, utilizator):
        # 1. Dacă nu este logat, clar nu are acces
        if not utilizator.is_authenticated:
            return False
            
        # 2. Adminul sau Superuser-ul au acces total
        if utilizator.is_superuser or utilizator.rol == 'ADMIN':
            return True
            
        # 3. METODA SIGURĂ: Comparăm ID-ul utilizatorului logat cu ID-urile anchetatorilor
        # Folosim "_id" la final pentru a lua direct numărul din baza de date, fără a mai face interogări extra
        utilizator_id = utilizator.pk
        
        echipa_dosar_ids = [
            self.ofiter_caz_id, 
            self.procuror_caz_id, 
            self.grefier_caz_id
        ]
        
        # Dacă ID-ul meu se află în lista ID-urilor de pe dosar, am acces!
        if utilizator_id in echipa_dosar_ids:
            return True
            
        return False

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
    
class Infractiune(models.Model):
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='infractiuni')
    incadrare_juridica = models.CharField(max_length=255, help_text="Ex: Furt calificat")
    articol_penal = models.CharField(max_length=100, help_text="Ex: art. 228-229 C.pen.")
    data_comiterii = models.DateField(null=True, blank=True, help_text="Data presupusei fapte")

    def __str__(self):
        return f"{self.incadrare_juridica} ({self.articol_penal})"
    
class MasuraPreventiva(models.Model):
    class TipMasura(models.TextChoices):
        RETINERE = 'RETINERE', 'Reținere (24h)'
        AREST_PREVENTIV = 'AREST_PREVENTIV', 'Arest Preventiv'
        AREST_DOMICILIU = 'AREST_DOMICILIU', 'Arest la Domiciliu'
        CONTROL_JUDICIAR = 'CONTROL_JUDICIAR', 'Control Judiciar'
        CONTROL_JUDICIAR_CAUTIUNE = 'CONTROL_JUDICIAR_CAUTIUNE', 'Control Judiciar pe Cauțiune'

    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='masuri_preventive')
    parte = models.ForeignKey(ParteImplicata, on_delete=models.CASCADE, related_name='masuri_preventive')
    
    tip_masura = models.CharField(max_length=50, choices=TipMasura.choices)
    durata_zile = models.PositiveIntegerField(help_text="Numărul de zile (ex: 30)")
    data_inceput = models.DateField()
    data_sfarsit = models.DateField()

    def __str__(self):
        return f"{self.get_tip_masura_display()} - {self.parte.nume_complet}"
    
    # ADĂUGĂM ASTA:
    @property
    def zile_ramase(self):
        if self.data_sfarsit:
            return (self.data_sfarsit - date.today()).days
        return 0
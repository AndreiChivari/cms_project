from simple_history.models import HistoricalRecords
from django.db import models
from django.conf import settings # Folosim asta pentru a importa modelul de User corect
from datetime import date # Folosim pentru calculul alertelor
from django.utils import timezone # Pentru a putea modifica data inregistrarii
from geopy.geocoders import Nominatim

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
    # 1. Eliminăm auto_now_add=True și îi dăm un default pe care utilizatorul îl poate schimba
    data_inregistrarii = models.DateField(
        default=timezone.now, 
        verbose_name="Data Înregistrării"
    )
    infractiune_cercetata = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Situația de Fapt (Rezumat)",
        help_text="Descrierea faptei pe scurt (opțional)"
    )
    
    # # 3. Actualizăm coloana stadiu
    # stadiu = models.CharField(
    #     max_length=20, 
    #     choices=Stadiu.choices, 
    #     default=Stadiu.POLITIE
    # )
    
    # # 4. Adăugăm coloanele noi
    # tip_solutie = models.CharField(
    #     max_length=20, 
    #     choices=Solutie.choices, 
    #     null=True, 
    #     blank=True
    # )
    # data_solutiei = models.DateField(null=True, blank=True)

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
    
    history = HistoricalRecords(verbose_name="Istoric Dosar") # <--- PĂSTREAZĂ ISTORICUL DOSARULUI

    @property
    def stadiu_curent(self):
        # Ne asigurăm că ia mereu ultimul stadiu adăugat (după dată și id)
        return self.stadii_cercetare.order_by('-data_incepere', '-id').first()

    @property
    def solutie_curenta(self):
        stadiu = self.stadiu_curent
        if not stadiu:
            return None
            
        # 1. Verificăm mai întâi dacă există o soluție FINALĂ pe acest stadiu
        solutie_finala = stadiu.solutii.filter(este_finala=True).first()
        if solutie_finala:
            return solutie_finala
            
        # 2. Dacă nu e finalizată, returnăm absolut ultima propunere (soluție) adăugată cronologic
        return stadiu.solutii.order_by('-data_solutiei', '-id').first()

class ParteImplicata(models.Model):
    class Calitate(models.TextChoices):
        FAPTUITOR = 'FAPTUITOR', 'Făptuitor'
        SUSPECT = 'SUSPECT', 'Suspect'
        INCULPAT = 'INCULPAT', 'Inculpat'
        PARTE_VATAMATA = 'PARTE_VATAMATA', 'Persoană vătămată'
        PARTE_CIVILA = 'PARTE_CIVILA', 'Parte civilă'
        MARTOR = 'MARTOR', 'Martor'

    # Legătura către dosar. Când un dosar e șters, se șterg și părțile implicate din el (CASCADE)
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='parti_implicate')
    
    nume_complet = models.CharField(max_length=150)
    cnp = models.CharField(max_length=13, blank=True, null=True, verbose_name="CNP")
    adresa = models.CharField(max_length=255, blank=True, null=True, verbose_name="Adresă")
    calitate_procesuala = models.CharField(max_length=20, choices=Calitate.choices)
    mentiuni = models.TextField(blank=True, null=True, help_text="Alte date de contact, antecedente, etc.")
    serie_ci = models.CharField(max_length=10, blank=True, null=True, verbose_name="Serie C.I.")
    numar_ci = models.CharField(max_length=20, blank=True, null=True, verbose_name="Număr C.I.")

    class Meta:
        verbose_name = "Parte Implicată"
        verbose_name_plural = "Părți Implicate"

    def __str__(self):
        return f"{self.nume_complet} ({self.get_calitate_procesuala_display()}) - {self.dosar.numar_unic}"
    
    history = HistoricalRecords() # <--- PĂSTREAZĂ ISTORICUL PĂRȚILOR
    
class Infractiune(models.Model):
    # Standardizăm actele normative frecvente din România
    class ActNormativ(models.TextChoices):
        CP = 'CP', 'Codul Penal'
        CPP = 'CPP', 'Codul de Procedură Penală'
        OUG195 = 'OUG195_2002', 'Codul Rutier (OUG 195/2002)'
        L143 = 'L143_2000', 'Trafic de droguri (Legea 143/2000)'
        L241 = 'L241_2005', 'Evaziune fiscală (Legea 241/2005)'
        L50 = 'L50_1991', 'Disciplina în construcții (Legea 50/1991)'
        L217 = 'L217_2003', 'Prevenirea şi combaterea violenţei în familie (Legea 217/2003)'
        L123 = 'L123_2012', 'Legea energiei electrice şi a gazelor naturale (Legea 123/2012)'
        ALTUL = 'ALTUL', 'Alt act normativ'

    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='infractiuni')
    
    # Doar Actul Normativ este obligatoriu
    act_normativ = models.CharField(max_length=50, choices=ActNormativ.choices, default=ActNormativ.CP)
    
    # Restul sunt opționale (blank=True, null=True)
    articol = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: 228 alin. 1")
    incadrare_juridica = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: Furt calificat")
    data_comiterii = models.DateField(null=True, blank=True, help_text="Data presupusei fapte")

    # 1. Câmpurile pentru hartă
    adresa_comiterii = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Locul săvârșirii faptei",
        help_text="Ex: Strada Mureșenilor nr. 1, Brașov"
    )
    # Acestea vor fi completate automat - le lăsăm blank/null
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    history = HistoricalRecords(verbose_name="Istoric Infracțiune")

    class Meta:
        verbose_name = "Infracțiune"
        verbose_name_plural = "Infracțiuni"

    def __str__(self):
        # Construim o afișare frumoasă în funcție de ce date avem completate
        text = self.get_act_normativ_display()
        if self.articol:
            text = f"art. {self.articol} {text}"
        if self.incadrare_juridica:
            text = f"{self.incadrare_juridica} ({text})"
        return text
    
    # 2. Suprascriem metoda save() pentru a genera coordonatele automat
    def save(self, *args, **kwargs):
        # Verificăm dacă ofițerul a introdus o adresă
        if self.adresa_comiterii:
            # Inițializăm geolocatorul (necesită un 'user_agent' ca să știe cine face cererea)
            geolocator = Nominatim(user_agent="cms_penal_licenta")
            
            try:
                # Căutăm adresa
                locatie = geolocator.geocode(self.adresa_comiterii)
                if locatie:
                    self.latitudine = locatie.latitude
                    self.longitudine = locatie.longitude
            except Exception as e:
                # Dacă pică serverul de hărți sau adresa e invalidă, salvăm oricum infracțiunea, dar fără coordonate
                print(f"Eroare la geocoding: {e}")
                
        # Apelăm metoda save() standard a lui Django pentru a finaliza salvarea
        super().save(*args, **kwargs)

class MasuraPreventiva(models.Model):
    class TipMasura(models.TextChoices):
        RETINERE = 'RETINERE', 'Reținere (24h)'
        AREST_PREVENTIV = 'AREST_PREVENTIV', 'Arest preventiv'
        AREST_DOMICILIU = 'AREST_DOMICILIU', 'Arest la domiciliu'
        CONTROL_JUDICIAR = 'CONTROL_JUDICIAR', 'Control judiciar'
        CONTROL_JUDICIAR_CAUTIUNE = 'CONTROL_JUDICIAR_CAUTIUNE', 'Control judiciar pe cauțiune'

    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='masuri_preventive')
    parte = models.ForeignKey(ParteImplicata, on_delete=models.CASCADE, related_name='masuri_preventive')
    
    tip_masura = models.CharField(max_length=50, choices=TipMasura.choices)
    durata_zile = models.PositiveIntegerField(help_text="Numărul de zile (ex: 30)")
    data_inceput = models.DateField()
    data_sfarsit = models.DateField()

    class Meta:
        verbose_name = "Măsură Preventivă"
        verbose_name_plural = "Măsuri Preventive"

    def __str__(self):
        return f"{self.get_tip_masura_display()} - {self.parte.nume_complet}"
    
    # ADĂUGĂM ASTA:
    @property
    def zile_ramase(self):
        if self.data_sfarsit:
            return (self.data_sfarsit - date.today()).days
        return 0
    
    history = HistoricalRecords(verbose_name="Istoric Măsură Preventivă") # <--- PĂSTREAZĂ ISTORICUL MĂSURILOR


class IstoricDesemnare(models.Model):
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='istoric_desemnari')
    
    # Folosim get_user_model() dacă l-ai importat deja sus, sau direct referința către User
    utilizator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Păstrăm funcția clară: Polițist, Procuror, Grefier
    rol = models.CharField(max_length=50) 
    
    data_desemnare = models.DateField(help_text="Data de la care a preluat dosarul")
    data_finalizare = models.DateField(null=True, blank=True, help_text="Data la care a predat dosarul")

    class Meta:
        verbose_name = "Istoric Desemnare"
        verbose_name_plural = "Istoric Desemnări"
        # Secretul: am adăugat '-id' ca a doua regulă de sortare
        ordering = ['-data_desemnare', '-id']

    def __str__(self):
        return f"{self.rol} - {self.utilizator} ({self.data_desemnare} -> {self.data_finalizare or 'Prezent'})"

class StadiuCercetare(models.Model):
    class TipStadiu(models.TextChoices):
        EXAMINARE = 'EXAMINARE', 'Examinare sesizare'
        UP_INCEPUTA = 'UP_INCEPUTA', 'Urmărire penală începută'
        AP_MASCATA = 'AP_MASCATA', 'Acțiune penală pusă în mișcare'

    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='stadii_cercetare')
    tip_stadiu = models.CharField(max_length=50, choices=TipStadiu.choices, default=TipStadiu.EXAMINARE)
    data_incepere = models.DateField(help_text="Data începerii stadiului")
    
    history = HistoricalRecords(verbose_name="Istoric Stadiu")

    class Meta:
        verbose_name = "Stadiu Urmărire"
        verbose_name_plural = "Stadii Urmărire"
        ordering = ['-data_incepere'] # Cele mai noi primele

    def __str__(self):
        return f"{self.get_tip_stadiu_display()} ({self.data_incepere})"


class SolutieDosar(models.Model):
    class Emitent(models.TextChoices):
        ORGAN_CERCETARE = 'ORGAN', 'Organ de cercetare'
        PROCUROR = 'PROCUROR', 'Procuror'

    class TipSolutie(models.TextChoices):
        RECHIZITORIU = 'RECHIZITORIU', 'Rechizitoriu'
        ACORD = 'ACORD', 'Acord de recunoaștere a vinovăției'
        # Clasări (Art. 16 CPP)
        CLASARE_A = 'CLASARE_A', 'Clasare - art. 16 alin. 1 lit. a) fapta nu există'
        CLASARE_B = 'CLASARE_B', 'Clasare - art. 16 alin. 1 lit. b) fapta nu e prevăzută de lege ori nu a fost săvârşită cu vinovăţie'
        CLASARE_C = 'CLASARE_C', 'Clasare - art. 16 alin. 1 lit. c) nu există probe'
        CLASARE_D = 'CLASARE_D', 'Clasare - art. 16 alin. 1 lit. d) există o cauză justificativă sau de neimputabilitate'
        CLASARE_E = 'CLASARE_E', 'Clasare - art. 16 alin. 1 lit. e) lipseşte plângerea prealabilă, autorizarea sau sesizarea ori o altă condiţie'
        CLASARE_F = 'CLASARE_F', 'Clasare - art. 16 alin. 1 lit. f) a intervenit amnistia sau prescripţia, decesul persoanei fizice sau radierea persoanei juridice'
        CLASARE_G = 'CLASARE_G', 'Clasare - art. 16 alin. 1 lit. g) retragerea plângerii prealabile, împăcarea ori încheierea unui acord de mediere'
        CLASARE_H = 'CLASARE_H', 'Clasare - art. 16 alin. 1 lit. h) există o cauză de nepedepsire'
        CLASARE_I = 'CLASARE_I', 'Clasare - art. 16 alin. 1 lit. i) există autoritate de lucru judecat'
        CLASARE_J = 'CLASARE_J', 'Clasare - art. 16 alin. 1 lit. j) a intervenit un transfer de proceduri cu un alt stat'
        # Altele
        RENUNTARE = 'RENUNTARE', 'Renunțare la urmărirea penală'
        DECLINARE = 'DECLINARE', 'Declinare de competență'
        TRECERE = 'TRECERE', 'Trecere la alt organ'
        RESTITUIRE = 'RESTITUIRE', 'Restituire la organul de cercetare'
        ALTA = 'ALTA', 'Altă soluție'

    stadiu = models.ForeignKey(StadiuCercetare, on_delete=models.CASCADE, related_name='solutii')
    stabilita_de = models.CharField(max_length=20, choices=Emitent.choices, default=Emitent.ORGAN_CERCETARE)
    tip_solutie = models.CharField(max_length=50, choices=TipSolutie.choices)
    data_solutiei = models.DateField()
    este_finala = models.BooleanField(default=False, help_text="Bifează dacă aceasta este decizia finală a procurorului")

    history = HistoricalRecords(verbose_name="Istoric Soluție")

    class Meta:
        verbose_name = "Soluție Dosar"
        verbose_name_plural = "Soluții Dosar"
        ordering = ['-data_solutiei']

    def __str__(self):
        return f"{self.get_tip_solutie_display()} - {self.get_stabilita_de_display()}"

class Notificare(models.Model):
    # Legăm notificarea de utilizatorul care trebuie să o primească
    utilizator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificari')

    # Conținutul notificării
    mesaj = models.CharField(max_length=255)
    link = models.CharField(max_length=255, help_text="URL-ul către dosarul vizat")

    # Starea notificării
    citita = models.BooleanField(default=False)
    data_crearii = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_crearii'] # Cele mai noi apar primele
        verbose_name = "Notificare"
        verbose_name_plural = "Notificări"

    def __str__(self):
        stare = "Citită" if self.citita else "NOUĂ"
        return f"[{stare}] {self.utilizator} - {self.mesaj}"
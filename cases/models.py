from simple_history.models import HistoricalRecords
from django.db import models
from django.conf import settings
from datetime import date
from django.utils import timezone
from geopy.geocoders import Nominatim
from cryptography.fernet import Fernet
import hmac
import hashlib

class EncryptedTextField(models.TextField):
    """Câmp custom care criptează transparent datele la salvarea în baza de date."""
    
    def get_prep_value(self, value):
        # Se execută chiar înainte de a scrie în baza de date (INSERT/UPDATE)
        value = super().get_prep_value(value)
        if value:
            f = Fernet(settings.ENCRYPTION_KEY)
            return f.encrypt(value.encode('utf-8')).decode('utf-8')
        return value

    def from_db_value(self, value, expression, connection):
        # Se execută la extragerea datelor din baza de date (SELECT)
        if value:
            try:
                f = Fernet(settings.ENCRYPTION_KEY)
                return f.decrypt(value.encode('utf-8')).decode('utf-8')
            except Exception:
                # Lăsăm datele vechi necriptate dacă decriptarea eșuează 
                return value
        return value

class Dosar(models.Model):
    """
    Modelul pentru un dosar penal. Conține informații generale despre dosar, legături către 
    echipa de cercetare și metode de verificare a drepturilor de editare.
    """
    
    class Stadiu(models.TextChoices):
        POLITIE = 'POLITIE', 'În lucru la Poliție'
        PROCUROR = 'PROCUROR', 'În lucru la Procuror'
        SOLUTIONAT = 'SOLUTIONAT', 'Soluționat'

    # Opţiunile pentru soluții/propuneri
    class Solutie(models.TextChoices):
        TRIMITERE = 'TRIMITERE', 'Trimitere în judecată'
        CLASARE = 'CLASARE', 'Clasare'
        RENUNTARE = 'RENUNTARE', 'Renunțare la urmărirea penală'
        DECLINARE = 'DECLINARE', 'Declinare'
        SUSPENDARE = 'SUSPENDARE', 'Suspendare'
        TRECERE = 'TRECERE', 'Trecere la alt organ'

    numar_unic = models.CharField(max_length=50, unique=True, help_text="Ex: 123/P/2026")

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
    
    # ForeignKey (1-la-mulți): mai multe dosare pot avea același ofițer; la ștergerea utilizatorului, câmpul devine NULL.
    ofiter_caz = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='dosare_instrumentate'
    )
    
    # ForeignKey (1-la-mulți): mai multe dosare pot avea același procuror; la ștergerea utilizatorului, câmpul devine NULL.
    procuror_caz = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='dosare_supravegheate'
    )

    # ForeignKey (1-la-mulți): mai multe dosare pot avea același grefier; la ștergerea utilizatorului, câmpul devine NULL.
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

    # Metodă de verificare a drepturilor de editare pentru un utilizator
    def are_drepturi_editare(self, utilizator):
        # 1. Dacă nu este logat, nu are acces
        if not utilizator.is_authenticated:
            return False
            
        # 2. Adminul are acces total
        if utilizator.is_superuser or utilizator.rol == 'ADMIN':
            return True
            
        # 3.Comparăm ID-ul utilizatorului logat cu ID-urile membrilor
        utilizator_id = utilizator.pk
        
        echipa_dosar_ids = [
            self.ofiter_caz_id, 
            self.procuror_caz_id, 
            self.grefier_caz_id
        ]
        
        # Dacă ID-ul se află în lista ID-urilor de pe dosar, avem acces
        if utilizator_id in echipa_dosar_ids:
            return True
            
        return False

    def __str__(self):
        return f"Dosar nr. {self.numar_unic}"
    
    history = HistoricalRecords(verbose_name="Istoric Dosar")

    @property
    def stadiu_curent(self):
        # Luăm ultimul stadiu adăugat (după dată și id)
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
            
        # 2. Dacă nu e finalizată, returnăm ultima propunere (soluție) adăugată cronologic
        return stadiu.solutii.order_by('-data_solutiei', '-id').first()

class ParteImplicata(models.Model):
    """
    Modelul pentru o parte implicată într-un dosar penal. 

    Conține datele de identificare și calitatea procesuală.
    """

    class Calitate(models.TextChoices):
        FAPTUITOR = 'FAPTUITOR', 'Făptuitor'
        SUSPECT = 'SUSPECT', 'Suspect'
        INCULPAT = 'INCULPAT', 'Inculpat'
        PARTE_VATAMATA = 'PARTE_VATAMATA', 'Persoană vătămată'
        PARTE_CIVILA = 'PARTE_CIVILA', 'Parte civilă'
        MARTOR = 'MARTOR', 'Martor'

    # ForeignKey (1-la-mulți): un dosar are mai multe părți implicate; la ștergerea dosarului, părțile se șterg în cascadă.
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='parti_implicate')
    
    nume_complet = models.CharField(max_length=150)
    cnp = EncryptedTextField(blank=True, null=True, verbose_name="CNP")
    
    # Blind Index-ul - hash HMAC-SHA256 al CNP-ului, permite căutări rapide fără a decripta toate înregistrările.
    cnp_hash = models.CharField(max_length=64, blank=True, null=True, editable=False)

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
    
    # Suprascriem salvarea pentru a genera hash-ul automat
    def save(self, *args, **kwargs):
        if self.cnp:
            # Creăm un hash ireversibil (HMAC-SHA256) din CNP-ul introdus
            secret = settings.SECRET_KEY.encode('utf-8')
            self.cnp_hash = hmac.new(secret, self.cnp.encode('utf-8'), hashlib.sha256).hexdigest()
        else:
            self.cnp_hash = None
        super().save(*args, **kwargs)
    
    history = HistoricalRecords()
    
class Infractiune(models.Model):
    """ 
    Modelul pentru o infracțiune cercetată într-un dosar penal. Conține detalii despre actul normativ, data comiterii și locația faptei. 
    De asemenea, generează automat coordonatele geografice pe baza adresei comiterii faptei. 
    """

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

    # ForeignKey (1-la-mulți): un dosar poate avea mai multe infracțiuni; la ștergerea dosarului, infracțiunile se șterg în cascadă.
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='infractiuni')
    
    # Doar actul normativ este obligatoriu, celelalte câmpuri sunt opționale
    act_normativ = models.CharField(max_length=50, choices=ActNormativ.choices, default=ActNormativ.CP)
    
    articol = models.CharField(max_length=50, blank=True, null=True, help_text="Ex: 228 alin. 1")
    incadrare_juridica = models.CharField(max_length=255, blank=True, null=True, help_text="Ex: Furt calificat")
    data_comiterii = models.DateField(null=True, blank=True, help_text="Data presupusei fapte")

    # Câmpurile pentru hartă
    adresa_comiterii = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        verbose_name="Locul săvârșirii faptei",
        help_text="Ex: Strada Mureșenilor nr. 1, Brașov"
    )

    # Vor fi completate automat în funcţie de adresă - le lăsăm blank/null
    latitudine = models.FloatField(null=True, blank=True)
    longitudine = models.FloatField(null=True, blank=True)

    history = HistoricalRecords(verbose_name="Istoric Infracțiune")

    class Meta:
        verbose_name = "Infracțiune"
        verbose_name_plural = "Infracțiuni"

    def __str__(self):
        # Construim un text descriptiv pentru infracțiune, combinând actul normativ, articolul și încadrările juridice dacă sunt disponibile
        text = self.get_act_normativ_display()
        if self.articol:
            text = f"art. {self.articol} {text}"
        if self.incadrare_juridica:
            text = f"{self.incadrare_juridica} ({text})"
        return text
    
    # Suprascriem metoda save() pentru a genera coordonatele automat
    def save(self, *args, **kwargs):
        # Verificăm dacă am introdus o adresă
        if self.adresa_comiterii:
            # Inițializăm geolocatorul (folosim un 'user_agent' pentru a evita blocarea de către serverul de hărți)
            geolocator = Nominatim(user_agent="cms_penal_licenta")
            
            try:
                # Căutăm adresa
                locatie = geolocator.geocode(self.adresa_comiterii)
                if locatie:
                    self.latitudine = locatie.latitude
                    self.longitudine = locatie.longitude
            except Exception as e:
                # Dacă serverul de hărți nu e funcţional sau adresa e invalidă, salvăm infracțiunea, dar fără coordonate
                print(f"Eroare la geocoding: {e}")
                
        # Apelăm metoda save() standard pentru a finaliza salvarea
        super().save(*args, **kwargs)

class MasuraPreventiva(models.Model):
    """
    Modelul pentru măsurile preventive dispuse într-un dosar penal. 
    
    Conține tipul măsurii, durata și datele de început și sfârșit. 
    De asemenea, are un câmp boolean folosit pentru alerte.
    """

    class TipMasura(models.TextChoices):
        RETINERE = 'RETINERE', 'Reținere (24h)'
        AREST_PREVENTIV = 'AREST_PREVENTIV', 'Arest preventiv'
        AREST_DOMICILIU = 'AREST_DOMICILIU', 'Arest la domiciliu'
        CONTROL_JUDICIAR = 'CONTROL_JUDICIAR', 'Control judiciar'
        CONTROL_JUDICIAR_CAUTIUNE = 'CONTROL_JUDICIAR_CAUTIUNE', 'Control judiciar pe cauțiune'

    # ForeignKey (1-la-mulți): un dosar poate avea mai multe măsuri preventive; la ștergerea dosarului, măsurile se șterg în cascadă.
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='masuri_preventive')

    # ForeignKey (1-la-mulți): o parte implicată poate avea mai multe măsuri preventive; la ștergerea părții, măsurile se șterg în cascadă.
    parte = models.ForeignKey(ParteImplicata, on_delete=models.CASCADE, related_name='masuri_preventive')
    
    tip_masura = models.CharField(max_length=50, choices=TipMasura.choices)
    durata_zile = models.PositiveIntegerField(help_text="Numărul de zile (ex: 30)")
    data_inceput = models.DateField()
    data_sfarsit = models.DateField()
    indeplinit = models.BooleanField(default=False, verbose_name="Îndeplinit")

    class Meta:
        verbose_name = "Măsură Preventivă"
        verbose_name_plural = "Măsuri Preventive"

    def __str__(self):
        return f"{self.get_tip_masura_display()} - {self.parte.nume_complet}"
    
    @property
    def zile_ramase(self):
        if self.data_sfarsit:
            return (self.data_sfarsit - date.today()).days
        return 0
    
    history = HistoricalRecords(verbose_name="Istoric Măsură Preventivă")


class IstoricDesemnare(models.Model):
    """
    Modelul pentru istoricul de desemnări ale dosarului. 
    
    Fiecare înregistrare reprezintă o perioadă în care un utilizator a fost desemnat în dosar într-un anumit rol (ofițer, procuror, grefier.
    Conține datele de început și sfârșit ale desemnării, precum și rolul utilizatorului în acea perioadă.
    """

    # ForeignKey (1-la-mulți): un dosar poate avea mai multe înregistrări în istoric; la ștergerea dosarului, istoricul se șterge în cascadă.
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='istoric_desemnari')
    
    # ForeignKey (1-la-mulți): un utilizator poate apărea în mai multe desemnări; la ștergerea utilizatorului, înregistrările se șterg în cascadă.
    utilizator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    rol = models.CharField(max_length=50) 
    
    data_desemnare = models.DateField(help_text="Data de la care a preluat dosarul")
    data_finalizare = models.DateField(null=True, blank=True, help_text="Data la care a predat dosarul")

    class Meta:
        verbose_name = "Istoric Desemnare"
        verbose_name_plural = "Istoric Desemnări"
        ordering = ['-data_desemnare', '-id']

    def __str__(self):
        return f"{self.rol} - {self.utilizator} ({self.data_desemnare} -> {self.data_finalizare or 'Prezent'})"

class StadiuCercetare(models.Model):
    """ Modelul pentru stadiile de cercetare ale unui dosar penal. Conține tipul stadiului și data începerii acestuia. """
    class TipStadiu(models.TextChoices):
        EXAMINARE = 'EXAMINARE', 'Examinare sesizare'
        UP_INCEPUTA = 'UP_INCEPUTA', 'Urmărire penală începută'
        AP_MASCATA = 'AP_MASCATA', 'Acțiune penală pusă în mișcare'

    # ForeignKey (1-la-mulți): un dosar poate avea mai multe stadii de cercetare; la ștergerea dosarului, stadiile se șterg în cascadă.
    dosar = models.ForeignKey(Dosar, on_delete=models.CASCADE, related_name='stadii_cercetare')
    tip_stadiu = models.CharField(max_length=50, choices=TipStadiu.choices, default=TipStadiu.EXAMINARE)
    data_incepere = models.DateField(help_text="Data începerii stadiului")
    
    history = HistoricalRecords(verbose_name="Istoric Stadiu")

    class Meta:
        verbose_name = "Stadiu Urmărire"
        verbose_name_plural = "Stadii Urmărire"
        ordering = ['-data_incepere']

    def __str__(self):
        return f"{self.get_tip_stadiu_display()} ({self.data_incepere})"


class SolutieDosar(models.Model):
    """
    Modelul pentru soluțiile/propunerile privind un dosar penal.

    Fiecare soluție este legată de un stadiu de cercetare și conține informații despre tipul soluției, data acesteia și cine a stabilit-o.
    """

    class Emitent(models.TextChoices):
        ORGAN_CERCETARE = 'ORGAN', 'Organ de cercetare'
        PROCUROR = 'PROCUROR', 'Procuror'

    class TipSolutie(models.TextChoices):
        RECHIZITORIU = 'RECHIZITORIU', 'Rechizitoriu'
        ACORD = 'ACORD', 'Acord de recunoaștere a vinovăției'
        CLASARE_A = 'CLASARE_A', 'Clasare - art. 16 alin. 1 lit. a) fapta nu există'
        CLASARE_B = 'CLASARE_B', 'Clasare - art. 16 alin. 1 lit. b) fapta nu e prevăzută de lege ori nu a fost săvârşită cu vinovăţie'
        CLASARE_C = 'CLASARE_C', 'Clasare - art. 16 alin. 1 lit. c) nu există probe'
        CLASARE_D = 'CLASARE_D', 'Clasare - art. 16 alin. 1 lit. d) există o cauză justificativă sau de neimputabilitate'
        CLASARE_E = 'CLASARE_E', 'Clasare - art. 16 alin. 1 lit. e) lipseşte plângerea prealabilă, autorizarea sau sesizarea ori o altă condiţie'
        CLASARE_F = 'CLASARE_F', 'Clasare - art. 16 alin. 1 lit. f) a intervenit amnistia sau prescripţia, decesul persoanei fizice sau radierea persoanei juridice'
        CLASARE_G = 'CLASARE_G', 'Clasare - art. 16 alin. 1 lit. g) retragerea plângerii prealabile, împăcarea ori încheierea unui acord de mediere'
        CLASARE_H = 'CLASARE_H', 'Clasare - art. 16 alin. 1 lit. h) există o cauză de nepedepsire'
        CLASARE_I = 'CLASARE_I', 'Clasare - art. 16 alin. 1 lit. i) există autoritate de lucru judecat'
        RENUNTARE = 'RENUNTARE', 'Renunțare la urmărirea penală'
        DECLINARE = 'DECLINARE', 'Declinare de competență'
        TRECERE = 'TRECERE', 'Trecere la alt organ'
        RESTITUIRE = 'RESTITUIRE', 'Restituire la organul de cercetare'
        ALTA = 'ALTA', 'Altă soluție'

    # ForeignKey (1-la-mulți): un stadiu poate avea mai multe soluții/propuneri; la ștergerea stadiului, soluțiile se șterg în cascadă.
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
    """ 
    Modelul pentru notificările generate de sistem pentru utilizatori. 
    
    Conține mesajul notificării, link-ul către dosarul vizat și starea de citire. 
    """

    # ForeignKey (1-la-mulți): un utilizator poate primi mai multe notificări; la ștergerea utilizatorului, notificările se șterg în cascadă.
    utilizator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificari')

    # Conținutul notificării
    mesaj = models.CharField(max_length=255)
    link = models.CharField(max_length=255, help_text="URL-ul către dosarul vizat")

    # Starea notificării
    citita = models.BooleanField(default=False)
    data_crearii = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data_crearii'] # Cele mai noi sunt afişate primele
        verbose_name = "Notificare"
        verbose_name_plural = "Notificări"

    def __str__(self):
        stare = "Citită" if self.citita else "NOUĂ"
        return f"[{stare}] {self.utilizator} - {self.mesaj}"
    

class TermenProcedural(models.Model):
    """
    Modelul pentru termenele procedurale asociate unui dosar penal.

    Fiecare termen procedural este legat de un dosar și conține informații despre tipul termenului, data limită, ora (opțional) și detalii suplimentare.
    """

    TIP_TERMEN_CHOICES = [
        ('PRESCRIPTIE_GEN', 'Prescripție'),
        ('NOTA', 'Notă de dispoziţii'),
        ('INSTANTA', 'Termen instanță (Contestație durată proces)'),
        ('AUDIERE', 'Audiere'),
        ('ALTUL', 'Alt tip de termen procedural'),
    ]

    # ForeignKey (1-la-mulți): un dosar poate avea mai multe termene procedurale; la ștergerea dosarului, termenele se șterg în cascadă.
    dosar = models.ForeignKey(
        'Dosar', 
        on_delete=models.CASCADE, 
        related_name='termene_procedurale'
    )

    # Titlu scurt pentru calendar
    titlu = models.CharField(
        max_length=150,
        blank=True, # Îl lăsăm opțional în formular
        default='', # Folosim pentru a evita erori de câmp gol pentru datele existente
        verbose_name="Titlu (Scurt)",
        help_text="Ex: Audiere martor Popescu. Dacă e lăsat gol, se va genera automat."
    )
    tip_termen = models.CharField(
        max_length=20, 
        choices=TIP_TERMEN_CHOICES, 
        verbose_name="Tip Termen"
    )
    data_limita = models.DateField(
        verbose_name="Dată Limită / Scadență"
    )

    # Oră opțională
    ora = models.TimeField(
        blank=True,
        null=True,
        verbose_name="Oră (Opțional)",
        help_text="Lăsați gol pentru evenimente care durează toată ziua (ex: Prescripție)"
    )
    indeplinit = models.BooleanField(
        default=False,
        verbose_name="Îndeplinit",
        help_text="Bifați dacă activitatea a fost realizată"
    )
    detalii = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Detalii / Observații",
        help_text="Ex: Judecătoria Brașov a stabilit termen pentru finalizarea urmăririi penale."
    )
    adaugat_la = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Termen Procedural"
        verbose_name_plural = "Termene Procedurale"
        ordering = ['data_limita', 'ora'] # Ordonăm după data limită (cele mai urgente apar primele)

    def __str__(self):
        return f"{self.get_tip_termen_display()} - {self.dosar.numar_unic}"

    # Proprietate calculată dinamic pentru a afișa câte zile au rămas până la termenul procedural
    @property
    def zile_ramase(self):
        if self.data_limita:
            return (self.data_limita - date.today()).days
        return 0
    
    def save(self, *args, **kwargs):
        # Auto-completare - dacă utilizatorul nu a pus un titlu, generăm automat unul bazat pe tipul termenului și numărul dosarului
        if not self.titlu:
            self.titlu = f"{self.get_tip_termen_display()} ({self.dosar.numar_unic})"
        super().save(*args, **kwargs)
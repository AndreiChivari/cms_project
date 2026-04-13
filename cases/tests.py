from django.test import TestCase
from datetime import date, timedelta
from django.utils import timezone
from cases.models import Dosar, StadiuCercetare, SolutieDosar
from cases.forms import ParteImplicataForm, MasuraPreventivaForm, CreareDosarForm, StadiuCercetareForm, SolutieDosarForm

class ValidariParteImplicataTest(TestCase):
    
    def test_cnp_mai_mic_de_13_cifre_este_respins(self):
        """Verifică dacă un CNP cu 12 cifre declanșează eroare."""
        data={
            'nume_complet': 'Ion Popescu',
            'cnp': '123456789012', # Greşit: 12 cifre
            'calitate_procesuala': 'SUSPECT'
        }
        formular = ParteImplicataForm(data=data)
        self.assertFalse(formular.is_valid())
        self.assertIn('cnp', formular.errors)
        self.assertTrue(any('exact 13 cifre' in eroare for eroare in formular.errors['cnp']))

    def test_cnp_cu_litere_este_respins(self):
        """Verifică dacă un CNP care conține litere este respins."""
        data={
            'nume_complet': 'Maria Ionescu',
            'cnp': '123456789012A', # Greşit: 13 caractere, dar conține o literă
            'calitate_procesuala': 'VICTIMA'
        }
        formular = ParteImplicataForm(data=data)
        self.assertFalse(formular.is_valid())
        self.assertIn('cnp', formular.errors)


class ValidariMasuriPreventiveTest(TestCase):
    
    def test_data_sfarsit_inaintea_datei_inceput(self):
        """Verifică regula cronologică: o măsură nu poate expira înainte să înceapă."""
        azi = date.today()
        acum_5_zile = azi - timedelta(days=5)

        formular = MasuraPreventivaForm(data={
            'tip_masura': 'CONTROL_JUDICIAR',
            'data_inceput': azi,
            'data_sfarsit': acum_5_zile,
        })
        
        self.assertFalse(formular.is_valid())
        self.assertIn('data_sfarsit', formular.errors)

class ValidariDosarTest(TestCase):
    
    def test_format_numar_dosar_fara_indicativ(self):
        """Verifică dacă formularul respinge un număr care nu conține /P/."""
        formular = CreareDosarForm(data={
            'numar_unic': '123/A/2026', # Greșit: A în loc de P
            'data_inregistrarii': date.today(),
            'infractiune_cercetata': 'Furt',
        })
        self.assertFalse(formular.is_valid())
        self.assertIn('numar_unic', formular.errors)
        self.assertTrue(any('indicativul standard' in err for err in formular.errors['numar_unic']))

    def test_an_dosar_absurd(self):
        """Verifică logica matematică a anului (trebuie să fie între 1990 și 2100)."""
        formular = CreareDosarForm(data={
            'numar_unic': '123/P/9999', # Greșit: anul 9999
            'data_inregistrarii': date.today(),
        })
        self.assertFalse(formular.is_valid())
        self.assertIn('numar_unic', formular.errors)


class ValidariProceduraleTest(TestCase):
    
    def setUp(self):
        """
        Funcția setUp rulează AUTOMAT înaintea fiecărui test.
        Aici creăm datele de bază în 'baza de date fantomă' de care au nevoie formularele.
        """
        # Creăm un dosar înregistrat acum 10 zile
        self.dosar = Dosar.objects.create(
            numar_unic='100/P/2023',
            data_inregistrarii=date.today() - timedelta(days=10)
        )
        # Creăm un stadiu început acum 5 zile
        self.stadiu = StadiuCercetare.objects.create(
            dosar=self.dosar,
            tip_stadiu='UP_INCEPUTA',
            data_incepere=date.today() - timedelta(days=5)
        )

    def test_stadiu_nu_poate_incepe_inaintea_dosarului(self):
        """Verifică imposibilitatea începerii urmăririi penale înainte de deschiderea dosarului."""
        formular = StadiuCercetareForm(data={
            'tip_stadiu': 'AP_MASCATA',
            'data_incepere': date.today() - timedelta(days=20) # Acum 20 de zile (dosarul are doar 10)
        })
        # Legăm formularul de dosarul creat în setUp()
        formular.instance.dosar = self.dosar
        
        self.assertFalse(formular.is_valid())
        self.assertIn('data_incepere', formular.errors)

    def test_nu_pot_exista_doua_solutii_finale(self):
        """Verifică interdicția de a adăuga două soluții finale în același dosar."""
        
        # 1. Salvăm direct o soluție FINALĂ pe acest stadiu
        SolutieDosar.objects.create(
            stadiu=self.stadiu,
            stabilita_de='PROCUROR',
            tip_solutie='CLASARE_A',
            data_solutiei=date.today() - timedelta(days=2),
            este_finala=True # Prima soluție finală
        )
        
        # 2. Încercăm să mai adăugăm UNA NOUĂ prin formular
        formular = SolutieDosarForm(data={
            'stabilita_de': 'PROCUROR',
            'tip_solutie': 'RENUNTARE',
            'data_solutiei': date.today(),
            'este_finala': True # Încercăm a doua soluție finală
        })
        formular.instance.stadiu = self.stadiu
        
        # 3. Ne așteptăm ca sistemul să blocheze formularul
        self.assertFalse(formular.is_valid())
        self.assertIn('este_finala', formular.errors)
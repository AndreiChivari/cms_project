from django import forms
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva, StadiuCercetare, SolutieDosar, TermenProcedural
from django.contrib.auth import get_user_model #  modelul de utilizator
from django.core.exceptions import ValidationError
from django.db.models import Q

User = get_user_model() # Preluăm modelul de utilizator pentru a face filtrarile

class DosarForm(forms.ModelForm):
    # Câmp "virtual" - nu se salvează direct în tabelul Dosar, îl folosim pentru Istoric
    data_schimbare_echipa = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Data desemnării noului membru",
        help_text="Completează doar dacă modifici organul de cercetare, procurorul sau grefierul."
    )
    
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'infractiune_cercetata', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        
        # Etichete personalizate care vor apărea în HTML
        labels = {
            'ofiter_caz': 'Poliţist',
            'procuror_caz': 'Procuror',
            'grefier_caz': 'Grefier',
        }

        widgets = {
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'infractiune_cercetata': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ofiter_caz': forms.Select(attrs={'class': 'form-select'}),
            'procuror_caz': forms.Select(attrs={'class': 'form-select'}),
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(DosarForm, self).__init__(*args, **kwargs)
        self.fields['numar_unic'].disabled = True

        # Filtrarea dropdown-urilor
        if 'ofiter_caz' in self.fields:
            self.fields['ofiter_caz'].queryset = User.objects.filter(rol='POLITIST')
            # Formatăm afișarea (Afișează numele complet; dacă nu e completat, afișează username-ul)
            self.fields['ofiter_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
            
        if 'procuror_caz' in self.fields:
            self.fields['procuror_caz'].queryset = User.objects.filter(rol='PROCUROR')
            self.fields['procuror_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
            
            
        if 'grefier_caz' in self.fields:
            self.fields['grefier_caz'].queryset = User.objects.filter(rol='GREFIER')
            self.fields['grefier_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username

    def clean(self):
        cleaned_data = super().clean()
        data_schimbare = cleaned_data.get('data_schimbare_echipa')
        
        # Preluăm data înregistrării (fie din formular, dacă o edităm acum, fie din baza de date)
        data_inreg = cleaned_data.get('data_inregistrarii') or self.instance.data_inregistrarii
        
        # 1. Verificăm dacă s-a modificat MĂCAR UNUL dintre membrii echipei
        echipa_modificata = any(camp in self.changed_data for camp in ['ofiter_caz', 'procuror_caz', 'grefier_caz'])
        
        if echipa_modificata:
            if not data_schimbare:
                self.add_error('data_schimbare_echipa', "🛑 Este obligatoriu să alegeți data desemnării deoarece ați modificat un membru al echipei!")
            else:
                # VALIDARE: Data preluării nu poate fi înaintea dosarului
                if data_inreg and data_schimbare < data_inreg:
                    self.add_error('data_schimbare_echipa', f"Data noului mandat ({data_schimbare.strftime('%d.%m.%Y')}) nu poate fi anterioară înregistrării dosarului ({data_inreg.strftime('%d.%m.%Y')}).")
                
                # VALIDARE: Data preluării >= Data ultimei modificări din istoric
                if self.instance.pk:
                    ultima_desemnare = self.instance.istoric_desemnari.order_by('-data_desemnare').first() 
                    
                    if ultima_desemnare and data_schimbare < ultima_desemnare.data_desemnare:
                        self.add_error('data_schimbare_echipa', f"Eroare cronologică: Precedenta modificare a echipei s-a făcut pe {ultima_desemnare.data_desemnare.strftime('%d.%m.%Y')}. Data nouă trebuie să fie cel puțin egală cu aceasta.")
        
        return cleaned_data

class CreareDosarForm(forms.ModelForm):
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'data_inregistrarii', 'infractiune_cercetata', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        
        labels = {
            'ofiter_caz': 'Poliţist',
            'procuror_caz': 'Procuror',
            'grefier_caz': 'Grefier',
        }
        
        widgets = {
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123/P/2026'}),
            'data_inregistrarii': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'infractiune_cercetata': forms.Textarea(attrs={'rows': 3}),
            'ofiter_caz': forms.Select(attrs={'class': 'form-select'}),
            'procuror_caz': forms.Select(attrs={'class': 'form-select'}),
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}),
        }

    # iltrarea dropdown-urilor
    def __init__(self, *args, **kwargs):
        super(CreareDosarForm, self).__init__(*args, **kwargs)
        if 'ofiter_caz' in self.fields:
            self.fields['ofiter_caz'].queryset = User.objects.filter(rol='POLITIST')
            # Formatăm afișarea (Afișează numele complet; dacă nu e completat, afișează username-ul)
            self.fields['ofiter_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
            
        if 'procuror_caz' in self.fields:
            self.fields['procuror_caz'].queryset = User.objects.filter(rol='PROCUROR')
            self.fields['procuror_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username
            
        if 'grefier_caz' in self.fields:
            self.fields['grefier_caz'].queryset = User.objects.filter(rol='GREFIER')
            self.fields['grefier_caz'].label_from_instance = lambda obj: obj.get_full_name() or obj.username

    def clean_numar_unic(self):
        numar = self.cleaned_data.get('numar_unic')

        if numar:
            # AUTO-CORECȚIE: Litere mari și fără spații
            numar = numar.upper().strip()

            # VALIDARE: Verificăm prezența lui '/P/'
            if '/P/' not in numar:
                raise ValidationError("Numărul dosarului trebuie să conțină indicativul standard '/P/'. Ex: 123/P/2026")

            # Tăiem textul în două folosind '/P/' 
            bucati = numar.split('/P/')
            
            # Ne asigurăm că există fix două bucăți (să nu fi pus /P/ de două ori din greșeală)
            if len(bucati) != 2:
                raise ValidationError("Formatul este incorect. Asigurați-vă că folosiți indicativul '/P/' o singură dată.")

            numar_dosar = bucati[0] # Ce e înainte de /P/ (ex: '123')
            anul_dosar = bucati[1]  # Ce e după /P/ (ex: '2026')

            # VALIDARE: Partea din față să fie STRICT NUMĂR
            if not numar_dosar.isdigit():
                raise ValidationError(f"Numărul dosarului trebuie să conțină doar cifre. Aţi introdus litere/simboluri: '{numar_dosar}'")

            # VALIDARE: Anul să fie STRICT 4 CIFRE
            if not anul_dosar.isdigit() or len(anul_dosar) != 4:
                raise ValidationError(f"Anul trebuie să fie format din exact 4 cifre. Aţi introdus: '{anul_dosar}'")
                
            # siguranță logică pentru an
            an_cifre = int(anul_dosar)
            if an_cifre < 1990 or an_cifre > 2100:
                raise ValidationError(f"Anul {an_cifre} nu este valid!")

        return numar

class ParteImplicataForm(forms.ModelForm):
    class Meta:
        model = ParteImplicata
        # Nu includem 'dosar' pentru că îl legăm în spate (în views.py)
        fields = ['nume_complet', 'calitate_procesuala', 'cnp', 'adresa', 'mentiuni', 'serie_ci', 'numar_ci']
        
        widgets = {
            'nume_complet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nume și Prenume', 'id': 'input-nume'}),
            'calitate_procesuala': forms.Select(attrs={'class': 'form-select'}),
            'cnp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cod Numeric Personal', 'id': 'input-cnp'}),
            'serie_ci': forms.TextInput(attrs={'class': 'form-control', 'id': 'input-serie'}),
            'numar_ci': forms.TextInput(attrs={'class': 'form-control', 'id': 'input-numar'}),
            'adresa': forms.TextInput(attrs={'class': 'form-control', 'id': 'input-adresa'}),
            'mentiuni': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Date de contact, antecedente etc.'}),
        }

class InfractiuneForm(forms.ModelForm):
    class Meta:
        model = Infractiune
        fields = ['act_normativ', 'articol', 'incadrare_juridica', 'adresa_comiterii', 'data_comiterii']
        
        labels = {
            'act_normativ': 'Act Normativ',
            'articol': 'Articol',
            'incadrare_juridica': 'Încadrare Juridică',
            'adresa_comiterii': 'Locul săvârșirii faptei (Adresa)',
            'data_comiterii': 'Data săvârşirii faptei',
        }
        
        widgets = {
            'act_normativ': forms.Select(attrs={'class': 'form-select'}),
            'articol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 228 alin. 1'}),
            'incadrare_juridica': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Furt calificat'}),
            'adresa_comiterii': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Piața Sfatului nr. 1, Brașov'}),
            'data_comiterii': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class MasuraPreventivaForm(forms.ModelForm):
    class Meta:
        model = MasuraPreventiva
        fields = ['parte', 'tip_masura', 'durata_zile', 'data_inceput', 'data_sfarsit']
        widgets = {
            'data_inceput': forms.DateInput(attrs={'type': 'date'}),
            'data_sfarsit': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        # Extragem ID-ul dosarului trimis din views.py
        dosar_id = kwargs.pop('dosar_id', None)
        super(MasuraPreventivaForm, self).__init__(*args, **kwargs)
        
        # Filtrăm lista de persoane ca să apară doar cele din dosarul curent
        if dosar_id:
            self.fields['parte'].queryset = ParteImplicata.objects.filter(dosar_id=dosar_id)

class StadiuCercetareForm(forms.ModelForm):
    # Câmp virtual pentru notificări
    notifica_echipa = forms.BooleanField(
        required=False, 
        label="🔔 Notifică echipa de caz despre această modificare",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = StadiuCercetare
        fields = ['tip_stadiu', 'data_incepere']
        widgets = {
            'tip_stadiu': forms.Select(attrs={'class': 'form-select'}),
            'data_incepere': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        }

    def clean(self):
        cleaned_data = super().clean()
        tip_stadiu = cleaned_data.get('tip_stadiu')
        data_incepere = cleaned_data.get('data_incepere')
        
        # Preluăm dosarul în siguranță
        try:
            dosar = self.instance.dosar
        except:
            dosar = None

        if not tip_stadiu or not data_incepere or not dosar:
            return cleaned_data # Dacă lipsesc date, lăsăm validarea standard să preia

        # VALIDARE: Niciun stadiu înaintea înregistrării dosarului
        if data_incepere < dosar.data_inregistrarii:
            self.add_error('data_incepere', f"Data stadiului ({data_incepere.strftime('%d.%m.%Y')}) nu poate fi înaintea înregistrării dosarului ({dosar.data_inregistrarii.strftime('%d.%m.%Y')}).")

        # Căutăm ultimul stadiu existent (excluzându-l pe cel curent, dacă suntem la editare)
        if self.instance.pk:
            ultimul_stadiu = dosar.stadii_cercetare.exclude(pk=self.instance.pk).order_by('-data_incepere', '-id').first()
        else:
            ultimul_stadiu = dosar.stadii_cercetare.order_by('-data_incepere', '-id').first()

        if ultimul_stadiu:
            # VALIDARE: Cronologia Stadiilor
            if data_incepere < ultimul_stadiu.data_incepere:
                self.add_error('data_incepere', f"Data trebuie să fie consecutivă. Ultimul stadiu a fost pe {ultimul_stadiu.data_incepere.strftime('%d.%m.%Y')}.")

            # VALIDARE: Succesiunea Logică
            # chei din models.py (clasa TipStadiu)
            ORDINE_STADII = {
                'EXAMINARE': 1,
                'UP_INCEPUTA': 2,
                'AP_MASCATA': 3,
            }
            
            rang_nou = ORDINE_STADII.get(tip_stadiu, 0)
            rang_vechi = ORDINE_STADII.get(ultimul_stadiu.tip_stadiu, 0)

            if rang_nou > 0 and rang_vechi > 0 and rang_nou < rang_vechi:
                self.add_error('tip_stadiu', f"Procedural incorect: Nu poți adăuga acest stadiu după '{ultimul_stadiu.get_tip_stadiu_display()}'.")

        return cleaned_data

class SolutieDosarForm(forms.ModelForm):
    # Câmp virtual pentru notificări
    notifica_echipa = forms.BooleanField(
        required=False, 
        label="🔔 Notifică echipa de caz despre această modificare",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = SolutieDosar
        fields = ['stabilita_de', 'tip_solutie', 'data_solutiei', 'este_finala']
        widgets = {
            # RadioSelect afișează opțiunile ca butoane radio
            'stabilita_de': forms.RadioSelect(), 
            'tip_solutie': forms.Select(attrs={'class': 'form-select'}),
            'data_solutiei': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'este_finala': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def clean(self):
        cleaned_data = super().clean()
        data_solutiei = cleaned_data.get('data_solutiei')
        este_finala = cleaned_data.get('este_finala') # Citim bifa de soluție finală
        
        try:
            stadiu = self.instance.stadiu
            dosar = stadiu.dosar
        except:
            return cleaned_data # Dacă nu avem relațiile încărcate, trecem mai departe

        if not data_solutiei or not stadiu:
            return cleaned_data

        # VALIDARE: Cronologia Soluției
        if data_solutiei < stadiu.data_incepere:
            self.add_error('data_solutiei', f"Data soluției ({data_solutiei.strftime('%d.%m.%Y')}) nu poate fi anterioară începerii stadiului ({stadiu.data_incepere.strftime('%d.%m.%Y')}).")

        if data_solutiei < dosar.data_inregistrarii:
            self.add_error('data_solutiei', f"Soluția nu poate fi anterioară înregistrării dosarului ({dosar.data_inregistrarii.strftime('%d.%m.%Y')}).")

        # VALIDARE: O singură Soluție Finală pe Dosar
        if este_finala:
            # Căutăm dacă mai există VREO soluție finală pe ORICE stadiu al acestui dosar
            solutii_finale = SolutieDosar.objects.filter(stadiu__dosar=dosar, este_finala=True)
            
            # Dacă edităm o soluție deja existentă, o excludem pe ea însăși din căutare
            if self.instance.pk:
                solutii_finale = solutii_finale.exclude(pk=self.instance.pk)
                
            # Dacă am găsit altă soluție finală, blocăm salvarea!
            if solutii_finale.exists():
                self.add_error('este_finala', "🛑 Acest dosar are deja o soluție definitivă înregistrată. Nu pot exista două soluții finale pe același dosar!")

        return cleaned_data
    
class TermenProceduralForm(forms.ModelForm):
    class Meta:
        model = TermenProcedural
        fields = ['dosar', 'titlu', 'tip_termen', 'data_limita', 'ora', 'detalii']
        widgets = {
            'dosar': forms.Select(attrs={'class': 'form-select'}),
            'titlu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Audiere Popescu Ion (opțional)'}),
            'tip_termen': forms.Select(attrs={'class': 'form-select'}),
            'data_limita': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'ora': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'detalii': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalii suplimentare...'}),
        }

    # def __init__(self, *args, **kwargs):
    #     # Opțional: Dacă vrei să îi trimiți utilizatorul curent pentru a filtra dosarele
    #     # user = kwargs.pop('user', None)
    #     super(TermenProceduralForm, self).__init__(*args, **kwargs)
    #     # Dacă vrei să arăți doar dosarele active, poți filtra aici:
    #     # self.fields['dosar'].queryset = Dosar.objects.filter(stadiu='ACTIV')

    def __init__(self, *args, **kwargs):
        # Extragem utilizatorul trimis din view (dacă există)
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            # Filtrăm dropdown-ul pe baza echipei
            if user.is_superuser or getattr(user, 'rol', '') == 'ADMIN':
                self.fields['dosar'].queryset = Dosar.objects.all()
            else:
                self.fields['dosar'].queryset = Dosar.objects.filter(
                    Q(ofiter_caz=user) | Q(procuror_caz=user) | Q(grefier_caz=user)
                )
            
            # Afișăm doar numărul dosarului, curat și scurt
            self.fields['dosar'].label_from_instance = lambda d: d.numar_unic
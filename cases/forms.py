from django import forms
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva
from django.contrib.auth import get_user_model # <--- Importăm modelul de Utilizator

User = get_user_model() # Preluăm modelul de utilizator pentru a face filtrarile

class DosarForm(forms.ModelForm):
    # Câmp "virtual" - nu se salvează direct în tabelul Dosar, ci îl folosim noi pentru Istoric!
    data_schimbare_echipa = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Data preluării noului mandat",
        help_text="Completează doar dacă modifici Ofițerul, Procurorul sau Grefierul de caz."
    )
    
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'infractiune_cercetata', 'stadiu', 'tip_solutie', 'data_solutiei', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        
        widgets = {
            'data_solutiei': forms.DateInput(attrs={'type': 'date'}),
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'stadiu': forms.Select(attrs={'class': 'form-select'}),
            'infractiune_cercetata': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ofiter_caz': forms.Select(attrs={'class': 'form-select'}),
            'procuror_caz': forms.Select(attrs={'class': 'form-select'}),
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super(DosarForm, self).__init__(*args, **kwargs)
        # Ne asigurăm că valoarea disabled este setată și la nivel de validare Python
        self.fields['numar_unic'].disabled = True

        # ==========================================
        # LOGICA NOUĂ: Filtrarea dropdown-urilor
        # ==========================================
        # ATENȚIE: Înlocuiește 'rol' cu numele real al coloanei din modelul tău de utilizatori
        # și 'OFITER', 'PROCUROR', 'GREFIER' cu valorile exacte pe care le-ai definit tu.
        
        if 'ofiter_caz' in self.fields:
            self.fields['ofiter_caz'].queryset = User.objects.filter(rol='POLITIST')
            
        if 'procuror_caz' in self.fields:
            self.fields['procuror_caz'].queryset = User.objects.filter(rol='PROCUROR')
            
        if 'grefier_caz' in self.fields:
            self.fields['grefier_caz'].queryset = User.objects.filter(rol='GREFIER')

class CreareDosarForm(forms.ModelForm):
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'infractiune_cercetata', 'stadiu', 'tip_solutie', 'data_solutiei', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        widgets = {
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123/P/2026'}),
            'stadiu': forms.Select(attrs={'class': 'form-select'}),
            'infractiune_cercetata': forms.Textarea(attrs={'rows': 3}),
            'data_solutiei': forms.DateInput(attrs={'type': 'date'}), # Calendar pentru dată
            'ofiter_caz': forms.Select(attrs={'class': 'form-select'}),
            'procuror_caz': forms.Select(attrs={'class': 'form-select'}),
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}),
        }

    # ==========================================
    # LOGICA NOUĂ: Filtrarea dropdown-urilor
    # ==========================================
    # ATENȚIE: Înlocuiește 'rol' cu numele real al coloanei din modelul tău de utilizatori
    # și 'OFITER', 'PROCUROR', 'GREFIER' cu valorile exacte pe care le-ai definit tu.
    
    def __init__(self, *args, **kwargs):
        super(CreareDosarForm, self).__init__(*args, **kwargs)
        if 'ofiter_caz' in self.fields:
            self.fields['ofiter_caz'].queryset = User.objects.filter(rol='POLITIST')
            
        if 'procuror_caz' in self.fields:
            self.fields['procuror_caz'].queryset = User.objects.filter(rol='PROCUROR')
            
        if 'grefier_caz' in self.fields:
            self.fields['grefier_caz'].queryset = User.objects.filter(rol='GREFIER')

class ParteImplicataForm(forms.ModelForm):
    class Meta:
        model = ParteImplicata
        # Nu includem 'dosar' pentru că îl legăm noi în spate (în views.py)
        fields = ['nume_complet', 'calitate_procesuala', 'cnp', 'mentiuni']
        
        widgets = {
            'nume_complet': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nume și Prenume'}),
            'calitate_procesuala': forms.Select(attrs={'class': 'form-select'}),
            'cnp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cod Numeric Personal'}),
            'mentiuni': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Date de contact, antecedente etc.'}),
        }

class InfractiuneForm(forms.ModelForm):
    class Meta:
        model = Infractiune
        fields = ['act_normativ', 'articol', 'incadrare_juridica', 'data_comiterii']
        widgets = {
            'data_comiterii': forms.DateInput(attrs={'type': 'date'}),
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
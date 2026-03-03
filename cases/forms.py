from django import forms
from .models import Dosar, ParteImplicata, Infractiune, MasuraPreventiva

class DosarForm(forms.ModelForm):
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
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}), # <--- Adăugat widget
        }

    def __init__(self, *args, **kwargs):
        super(DosarForm, self).__init__(*args, **kwargs)
        # O altă metodă de securitate în Django: 
        # Ne asigurăm că valoarea disabled este setată și la nivel de validare Python, nu doar în HTML
        self.fields['numar_unic'].disabled = True

class CreareDosarForm(forms.ModelForm):
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'infractiune_cercetata', 'stadiu', 'tip_solutie', 'data_solutiei']
        widgets = {
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123/P/2026'}),
            'stadiu': forms.Select(attrs={'class': 'form-select'}),
            'infractiune_cercetata': forms.Textarea(attrs={'rows': 3}),
            'data_solutiei': forms.DateInput(attrs={'type': 'date'}), # Calendar pentru dată
            'ofiter_caz': forms.Select(attrs={'class': 'form-select'}),
            'procuror_caz': forms.Select(attrs={'class': 'form-select'}),
            'grefier_caz': forms.Select(attrs={'class': 'form-select'}),
        }

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
        fields = ['incadrare_juridica', 'articol_penal', 'data_comiterii']
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
from django import forms
from .models import Dosar, ParteImplicata

class DosarForm(forms.ModelForm):
    class Meta:
        model = Dosar
        fields = ['numar_unic', 'stadiu', 'infractiune_cercetata', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        
        widgets = {
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
        fields = ['numar_unic', 'stadiu', 'infractiune_cercetata', 'ofiter_caz', 'procuror_caz', 'grefier_caz']
        widgets = {
            'numar_unic': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 123/P/2026'}),
            'stadiu': forms.Select(attrs={'class': 'form-select'}),
            'infractiune_cercetata': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
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
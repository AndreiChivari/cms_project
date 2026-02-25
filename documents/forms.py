from django import forms
from .models import ActUrmarire

class DocumentForm(forms.ModelForm):
    class Meta:
        model = ActUrmarire
        # Alegem doar câmpurile pe care utilizatorul le completează
        # (Nu punem 'dosar' și 'autor' pentru că le vom seta noi automat în fundal)
        fields = ['titlu', 'tip', 'fisier', 'descriere_scurta']
        
        # Adăugăm clasele de Bootstrap pentru a face formularul să arate bine
        widgets = {
            'titlu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Ordonanță reținere'}),
            'tip': forms.Select(attrs={'class': 'form-select'}),
            'fisier': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descriere_scurta': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Detalii opționale...'}),
        }
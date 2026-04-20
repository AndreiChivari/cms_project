import hmac
import hashlib
from django import forms
from django.conf import settings
from django.utils import timezone
from cases.models import ParteImplicata, Dosar
from .models import CerereAccesPortal, AccesPortalParte

class CerereAccesForm(forms.Form):
    numar_dosar = forms.CharField(
        max_length=50,
        label="Număr dosar",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: 123/P/2026',
            'class': 'portal-input'
        })
    )
    cnp = forms.CharField(
        max_length=13,
        min_length=13,
        label="CNP",
        widget=forms.TextInput(attrs={
            'placeholder': 'Cod Numeric Personal (13 cifre)',
            'class': 'portal-input'
        })
    )
    email = forms.EmailField(
        label="Adresă de email",
        widget=forms.EmailInput(attrs={
            'placeholder': 'adresa@email.ro',
            'class': 'portal-input'
        })
    )
    motiv = forms.CharField(
        label="Motivul solicitării",
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Descrieți pe scurt motivul pentru care solicitați accesul...',
            'class': 'portal-input'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        numar_dosar = cleaned_data.get('numar_dosar', '').strip().upper()
        cnp = cleaned_data.get('cnp', '').strip()

        if numar_dosar and cnp:
            # Verificăm dacă dosarul există
            try:
                dosar = Dosar.objects.get(numar_unic=numar_dosar)
            except Dosar.DoesNotExist:
                raise forms.ValidationError(
                    "Dosarul indicat nu a fost găsit în sistem. "
                    "Verificați numărul introdus sau adresați-vă la sediul parchetului."
                )

            # Căutăm CNP-ul prin hash (același mecanism ca în modelul ParteImplicata)
            secret = settings.SECRET_KEY.encode('utf-8')
            cnp_hash = hmac.new(
                secret, cnp.encode('utf-8'), hashlib.sha256
            ).hexdigest()

            parte = ParteImplicata.objects.filter(
                dosar=dosar, cnp_hash=cnp_hash
            ).first()

            if not parte:
                raise forms.ValidationError(
                    "Datele de identificare nu corespund niciunei persoane "
                    "înregistrate în dosarul indicat. "
                    "Verificați CNP-ul introdus sau prezentaţi-vă la sediul parchetului."
                )

            # Verificăm dacă nu există deja o cerere în așteptare
            cerere_existenta = CerereAccesPortal.objects.filter(
                dosar=dosar,
                parte=parte,
                stare=CerereAccesPortal.Stare.IN_ASTEPTARE
            ).exists()

            if cerere_existenta:
                raise forms.ValidationError(
                    "Există deja o cerere de acces în așteptare pentru acest dosar. "
                    "Vă rugăm să așteptați procesarea acesteia."
                )

            # Verificăm dacă nu are deja un acces activ
            acces_activ = AccesPortalParte.objects.filter(
                parte=parte,
                activ=True,
                data_expirare__gte=timezone.now().date()
            ).exists()

            if acces_activ:
                raise forms.ValidationError(
                    "Aveți deja un acces activ la acest dosar. "
                    "Utilizați codul primit anterior prin email."
                )

            cleaned_data['dosar'] = dosar
            cleaned_data['parte'] = parte

        return cleaned_data


class LoginPortalForm(forms.Form):
    numar_dosar = forms.CharField(
        max_length=50,
        label="Număr dosar",
        widget=forms.TextInput(attrs={
            'placeholder': 'Ex: 123/P/2026',
            'class': 'portal-input',
            'autocomplete': 'off'
        })
    )
    cod_acces = forms.CharField(
        max_length=20,
        label="Cod de acces",
        widget=forms.TextInput(attrs={
            'placeholder': 'Codul primit prin email',
            'class': 'portal-input',
            'autocomplete': 'off'
        })
    )
    pin = forms.CharField(
        max_length=4,
        min_length=4,
        label="PIN",
        widget=forms.PasswordInput(attrs={
            'placeholder': '4 cifre',
            'class': 'portal-input',
            'autocomplete': 'off'
        })
    )


class AprobareCerereForm(forms.Form):
    data_expirare = forms.DateField(
        label="Acces valabil până la",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm'
        })
    )
    documente_selectate = forms.ModelMultipleChoiceField(
        queryset=None,
        required=False,
        label="Documente accesibile solicitantului",
        widget=forms.CheckboxSelectMultiple()
    )

    def __init__(self, *args, dosar=None, **kwargs):
        super().__init__(*args, **kwargs)
        if dosar:
            from documents.models import ActUrmarire
            self.fields['documente_selectate'].queryset = ActUrmarire.objects.filter(
                dosar=dosar
            ).order_by('-data_documentului')


class RespingereCerereForm(forms.Form):
    motiv = forms.ChoiceField(
        choices=CerereAccesPortal.MotivRespingere.choices,
        label="Motiv respingere",
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    detalii = forms.CharField(
        required=False,
        label="Detalii suplimentare (opțional)",
        widget=forms.Textarea(attrs={
            'rows': 2,
            'class': 'form-control form-control-sm',
            'placeholder': 'Informații adiționale pentru solicitant...'
        })
    )
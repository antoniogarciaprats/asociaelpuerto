from django import forms
from django.utils import timezone
from gestion.models import Socio

class SocioForm(forms.ModelForm):
    class Meta:
        model = Socio
        fields = ["numero", "nombre", "apellidos", "email", "telefono", "fecha_alta", "activo"]
        widgets = {"fecha_alta": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}

    def clean_numero(self):
        return self.cleaned_data["numero"].strip().upper()

    def clean_fecha_alta(self):
        fecha = self.cleaned_data["fecha_alta"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha de alta no puede estar en el futuro.")
        return fecha

from django import forms
from django.utils import timezone
from gestion.models import Actividad, Socio

class ActividadForm(forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["titulo", "descripcion", "lugar", "inicio", "fin", "aforo", "estado"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 4}),
            "inicio": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
            "fin": forms.DateTimeInput(format="%Y-%m-%dT%H:%M", attrs={"type": "datetime-local"}),
        }

    def clean_inicio(self):
        inicio = self.cleaned_data["inicio"]
        if not self.instance.pk and inicio <= timezone.now():
            raise forms.ValidationError("Crea una actividad que comience en el futuro.")
        return inicio

class InscripcionForm(forms.Form):
    socio = forms.ModelChoiceField(queryset=Socio.objects.filter(activo=True), label="Socio activo")

from django import forms
from django.utils import timezone
from gestion.models import Cuota, Movimiento, Socio

class CuotaForm(forms.ModelForm):
    class Meta:
        model = Cuota
        fields = ["socio", "ejercicio", "importe", "vencimiento"]
        widgets = {"vencimiento": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["socio"].queryset = Socio.objects.filter(activo=True)

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ["fecha", "tipo", "categoria", "concepto", "importe", "actividad"]
        widgets = {"fecha": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].choices = [c for c in Movimiento.Categoria.choices if c[0] != "cuotas"]
        self.fields["actividad"].help_text = "Opcional: permite relacionar el cobro o pago con una actividad."

class CobroForm(forms.Form):
    fecha = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(
        format="%Y-%m-%d", attrs={"type": "date"}))

    def clean_fecha(self):
        fecha = self.cleaned_data["fecha"]
        if fecha > timezone.localdate():
            raise forms.ValidationError("La fecha no puede estar en el futuro.")
        return fecha

class ReversionForm(CobroForm):
    motivo = forms.CharField(max_length=100, label="Motivo de la corrección")

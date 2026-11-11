from django.db import models
from django.utils import timezone

class Socio(models.Model):
    numero = models.CharField("número de socio", max_length=16, unique=True)
    nombre = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=120)
    email = models.EmailField("correo electrónico", blank=True)
    telefono = models.CharField("teléfono", max_length=25, blank=True)
    fecha_alta = models.DateField(default=timezone.localdate)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["apellidos", "nombre", "pk"]
        verbose_name = "socio"
        verbose_name_plural = "socios"

    def __str__(self):
        return f"{self.numero} · {self.nombre} {self.apellidos}"

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from .socios import Socio

class Actividad(models.Model):
    class Estado(models.TextChoices):
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"
        CANCELADA = "cancelada", "Cancelada"
    titulo = models.CharField("título", max_length=140)
    descripcion = models.TextField("descripción", blank=True)
    lugar = models.CharField(max_length=180, default="El Puerto de Santa María")
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    aforo = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    # Contador reservado a los servicios: no se modifica en formularios.
    ocupadas = models.PositiveIntegerField(default=0, editable=False)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ABIERTA)

    class Meta:
        ordering = ["inicio", "pk"]
        constraints = [
            models.CheckConstraint(condition=models.Q(fin__gt=models.F("inicio")), name="actividad_fechas"),
            models.CheckConstraint(condition=models.Q(aforo__gte=1), name="actividad_aforo_positivo"),
            models.CheckConstraint(condition=models.Q(ocupadas__lte=models.F("aforo")), name="actividad_aforo_limite"),
        ]

    def clean(self):
        if self.inicio and self.fin and self.fin <= self.inicio:
            raise ValidationError({"fin": "La hora final debe ser posterior al inicio."})
        if self.aforo is not None and self.aforo < self.ocupadas:
            raise ValidationError({"aforo": "El aforo no puede ser menor que las plazas ocupadas."})

    @property
    def disponibles(self):
        return self.aforo - self.ocupadas

    @property
    def admite_inscripciones(self):
        return self.estado == self.Estado.ABIERTA and self.inicio > timezone.now()

    def __str__(self):
        return self.titulo

class Inscripcion(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name="inscripciones")
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, related_name="inscripciones")
    activa = models.BooleanField(default=True)
    asistio = models.BooleanField("asistió", default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["socio__apellidos", "socio__nombre", "pk"]
        verbose_name = "inscripción"
        verbose_name_plural = "inscripciones"
        constraints = [models.UniqueConstraint(fields=["socio", "actividad"], name="inscripcion_unica")]

    def __str__(self):
        return f"{self.socio} / {self.actividad}"

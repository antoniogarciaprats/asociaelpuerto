from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from .socios import Socio
from .actividades import Actividad

class Cuota(models.Model):
    socio = models.ForeignKey(Socio, on_delete=models.PROTECT, related_name="cuotas")
    ejercicio = models.PositiveIntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    importe = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    vencimiento = models.DateField()
    # Apunta al último cobro vigente; los cobros anteriores quedan en Movimiento.
    pago = models.OneToOneField("Movimiento", on_delete=models.PROTECT, null=True, blank=True,
                               related_name="cuota_pagada", editable=False)

    class Meta:
        ordering = ["-ejercicio", "socio__apellidos", "pk"]
        constraints = [
            models.UniqueConstraint(fields=["socio", "ejercicio"], name="cuota_anual_unica"),
            models.CheckConstraint(condition=models.Q(importe__gt=0), name="cuota_positiva"),
        ]

    def clean(self):
        if self.vencimiento and self.ejercicio and self.vencimiento.year != self.ejercicio:
            raise ValidationError({"vencimiento": "El vencimiento debe pertenecer al ejercicio."})

    @property
    def estado(self):
        if self.pago_id:
            return "Pagada"
        return "Vencida" if self.vencimiento < timezone.localdate() else "Pendiente"

    def __str__(self):
        return f"{self.socio.numero} / {self.ejercicio}"

class Movimiento(models.Model):
    class Tipo(models.TextChoices):
        INGRESO = "I", "Ingreso"
        GASTO = "G", "Gasto"
    class Categoria(models.TextChoices):
        CUOTAS = "cuotas", "Cuotas"
        ACTIVIDADES = "actividades", "Actividades"
        DONACIONES = "donaciones", "Donaciones"
        SUBVENCIONES = "subvenciones", "Subvenciones"
        SUMINISTROS = "suministros", "Suministros"
        SERVICIOS = "servicios", "Servicios"
        OTROS = "otros", "Otros"
    fecha = models.DateField(default=timezone.localdate)
    tipo = models.CharField(max_length=1, choices=Tipo.choices)
    categoria = models.CharField("categoría", max_length=20, choices=Categoria.choices)
    concepto = models.CharField(max_length=200)
    importe = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    actividad = models.ForeignKey(Actividad, on_delete=models.PROTECT, null=True, blank=True)
    cuota = models.ForeignKey(Cuota, on_delete=models.PROTECT, null=True, blank=True, related_name="movimientos")
    reversa_de = models.OneToOneField("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversion")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        constraints = [models.CheckConstraint(condition=models.Q(importe__gt=0), name="movimiento_positivo")]
        permissions = [("revertir_movimiento", "Puede revertir movimientos"),
                       ("exportar_informe", "Puede exportar informes")]

    def clean(self):
        if self.fecha and self.fecha > timezone.localdate():
            raise ValidationError({"fecha": "Registra cobros o pagos realizados, sin fechas futuras."})

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.concepto}"

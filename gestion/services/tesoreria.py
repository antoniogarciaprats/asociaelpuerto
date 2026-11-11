from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from gestion.models import Cuota, Movimiento

@transaction.atomic
def cobrar_cuota(cuota_id, usuario, fecha):
    cuota = Cuota.objects.get(pk=cuota_id)
    if cuota.pago_id:
        raise ValidationError("La cuota ya está pagada.")
    movimiento = Movimiento(
        fecha=fecha, tipo=Movimiento.Tipo.INGRESO, categoria=Movimiento.Categoria.CUOTAS,
        concepto=f"Cuota {cuota.ejercicio} · socio {cuota.socio.numero}",
        importe=cuota.importe, cuota=cuota, creado_por=usuario,
    )
    movimiento.full_clean()
    movimiento.save()
    # Dos envíos del mismo formulario no pueden enlazar dos pagos vigentes.
    actualizada = Cuota.objects.filter(pk=cuota_id, pago__isnull=True).update(pago=movimiento)
    if not actualizada:
        raise ValidationError("La cuota acaba de cobrarse en otra operación.")
    return movimiento

@transaction.atomic
def revertir_movimiento(movimiento_id, usuario, fecha, motivo):
    original = Movimiento.objects.get(pk=movimiento_id)
    if original.reversa_de_id or Movimiento.objects.filter(reversa_de=original).exists():
        raise ValidationError("Solo se puede corregir una vez un movimiento original.")
    if fecha < original.fecha:
        raise ValidationError("La corrección no puede ser anterior al movimiento original.")
    inverso = Movimiento(
        fecha=fecha, tipo="G" if original.tipo == "I" else "I",
        categoria=original.categoria, concepto=f"Reversión #{original.pk}: {motivo}",
        importe=original.importe, cuota=original.cuota, actividad=original.actividad,
        reversa_de=original, creado_por=usuario,
    )
    inverso.full_clean()
    inverso.save()
    if original.cuota_id:
        Cuota.objects.filter(pk=original.cuota_id, pago=original).update(pago=None)
    return inverso

def resumen(movimientos):
    """Incluye originales y reversiones; la suma refleja el flujo real registrado."""
    datos = movimientos.aggregate(
        ingresos=Sum("importe", filter=Q(tipo="I")),
        gastos=Sum("importe", filter=Q(tipo="G")),
    )
    ingresos = datos["ingresos"] or Decimal("0.00")
    gastos = datos["gastos"] or Decimal("0.00")
    return {"ingresos": ingresos, "gastos": gastos, "neto": ingresos - gastos}

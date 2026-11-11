"""Reglas de aforo. Cada operación se confirma completa o se deshace."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from gestion.models import Actividad, Inscripcion, Socio

@transaction.atomic
def inscribir(actividad_id, socio_id):
    # La actualización condicional reserva una plaza en una sola sentencia SQL.
    reservada = Actividad.objects.filter(
        pk=actividad_id, estado=Actividad.Estado.ABIERTA,
        inicio__gt=timezone.now(), ocupadas__lt=F("aforo"),
    ).update(ocupadas=F("ocupadas") + 1)
    if not reservada:
        raise ValidationError("No hay plazas o la actividad ya no admite inscripciones.")
    socio = Socio.objects.get(pk=socio_id)
    if not socio.activo:
        raise ValidationError("Solo se pueden inscribir socios activos.")
    inscripcion, nueva = Inscripcion.objects.get_or_create(
        actividad_id=actividad_id, socio=socio)
    if not nueva:
        if inscripcion.activa:
            raise ValidationError("Este socio ya estaba inscrito.")
        inscripcion.activa = True
        inscripcion.asistio = False
        inscripcion.save(update_fields=["activa", "asistio"])
    return inscripcion

@transaction.atomic
def cancelar(inscripcion_id):
    inscripcion = Inscripcion.objects.select_related("actividad").get(pk=inscripcion_id)
    if inscripcion.actividad.inicio <= timezone.now():
        raise ValidationError("No se cancelan inscripciones de actividades ya iniciadas.")
    modificada = Inscripcion.objects.filter(pk=inscripcion_id, activa=True).update(activa=False, asistio=False)
    if not modificada:
        raise ValidationError("La inscripción ya estaba cancelada.")
    Actividad.objects.filter(pk=inscripcion.actividad_id).update(ocupadas=F("ocupadas") - 1)

@transaction.atomic
def marcar_asistencia(inscripcion_id):
    inscripcion = Inscripcion.objects.select_related("actividad").get(pk=inscripcion_id)
    if not inscripcion.activa or inscripcion.actividad.estado == Actividad.Estado.CANCELADA:
        raise ValidationError("La inscripción o la actividad está cancelada.")
    if inscripcion.actividad.inicio > timezone.now():
        raise ValidationError("Todavía no ha comenzado la actividad.")
    Inscripcion.objects.filter(pk=inscripcion_id).update(asistio=not inscripcion.asistio)

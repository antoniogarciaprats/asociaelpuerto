from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from gestion.models import Actividad, Inscripcion
from gestion.forms.actividades import ActividadForm, InscripcionForm
from gestion.services.actividades import inscribir, cancelar, marcar_asistencia
from .common import acceso, formulario

@acceso("gestion.view_actividad")
def lista(request):
    actividades = Actividad.objects.all().order_by("-inicio")
    return render(request, "gestion/actividades.html", {
        "page_obj": Paginator(actividades, 9).get_page(request.GET.get("page"))})

@acceso("gestion.add_actividad")
def crear(request):
    form = ActividadForm(request.POST if request.method == "POST" else None)
    return formulario(request, form, "Nueva actividad", "gestion:actividades")

@acceso("gestion.change_actividad")
def editar(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    form = ActividadForm(request.POST if request.method == "POST" else None, instance=actividad)
    return formulario(request, form, "Editar actividad", "gestion:actividades")

@acceso(("gestion.view_actividad", "gestion.view_inscripcion"))
def detalle(request, pk):
    actividad = get_object_or_404(Actividad, pk=pk)
    inscripciones = actividad.inscripciones.select_related("socio")
    return render(request, "gestion/actividad.html", {
        "actividad": actividad, "inscripciones": inscripciones, "form": InscripcionForm()})

@acceso("gestion.add_inscripcion")
@require_POST
def alta(request, pk):
    get_object_or_404(Actividad, pk=pk)
    form = InscripcionForm(request.POST)
    if form.is_valid():
        try:
            inscribir(pk, form.cleaned_data["socio"].pk)
        except (ValidationError, IntegrityError) as error:
            messages.error(request, "; ".join(error.messages) if isinstance(error, ValidationError) else "La inscripción ya ha cambiado. Recarga la página.")
        else:
            messages.success(request, "Inscripción registrada.")
    else:
        messages.error(request, "Selecciona un socio activo válido.")
    return redirect("gestion:actividad", pk=pk)

@acceso("gestion.change_inscripcion")
@require_POST
def baja(request, pk):
    return accion_inscripcion(request, pk, cancelar, "Inscripción cancelada.")

@acceso("gestion.change_inscripcion")
@require_POST
def asistencia(request, pk):
    return accion_inscripcion(request, pk, marcar_asistencia, "Asistencia actualizada.")

def accion_inscripcion(request, pk, operacion, mensaje):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    try:
        operacion(pk)
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
    else:
        messages.success(request, mensaje)
    return redirect("gestion:actividad", pk=inscripcion.actividad_id)

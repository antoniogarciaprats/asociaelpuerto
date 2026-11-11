from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from gestion.models import Cuota, Movimiento
from gestion.forms.tesoreria import CuotaForm, MovimientoForm, CobroForm, ReversionForm
from gestion.services.tesoreria import cobrar_cuota, revertir_movimiento, resumen
from .common import acceso, formulario

@acceso("gestion.view_cuota")
def cuotas(request):
    estado = request.GET.get("estado", "todas")
    datos = Cuota.objects.select_related("socio", "pago")
    if estado == "pagadas":
        datos = datos.filter(pago__isnull=False)
    elif estado == "pendientes":
        datos = datos.filter(pago__isnull=True)
    return render(request, "gestion/cuotas.html", {
        "page_obj": Paginator(datos, 12).get_page(request.GET.get("page")), "estado": estado})

@acceso("gestion.add_cuota")
def crear_cuota(request):
    form = CuotaForm(request.POST if request.method == "POST" else None,
                     initial={"ejercicio": timezone.localdate().year})
    return formulario(request, form, "Emitir cuota anual", "gestion:cuotas")

@acceso(("gestion.change_cuota", "gestion.add_movimiento"))
def cobrar(request, pk):
    cuota = get_object_or_404(Cuota.objects.select_related("socio"), pk=pk)
    form = CobroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            cobrar_cuota(pk, request.user, form.cleaned_data["fecha"])
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, "; ".join(error.messages) if isinstance(error, ValidationError) else "El cobro ya ha cambiado. Recarga la página.")
        else:
            messages.success(request, "Cobro registrado en tesorería.")
            return redirect("gestion:cuotas")
    return render(request, "gestion/formulario.html", {
        "form": form, "titulo": f"Cobrar {cuota.importe} € · {cuota.socio.numero}",
        "descripcion": "Confirma únicamente cuando hayas recibido el dinero.", "destino": "gestion:cuotas"})

@acceso("gestion.view_movimiento")
def movimientos(request):
    datos = Movimiento.objects.select_related("creado_por", "reversion", "reversa_de", "actividad")
    return render(request, "gestion/movimientos.html", {
        "page_obj": Paginator(datos, 15).get_page(request.GET.get("page")), "balance": resumen(datos)})

@acceso("gestion.add_movimiento")
def crear_movimiento(request):
    form = MovimientoForm(request.POST if request.method == "POST" else None)
    def autor(objeto):
        objeto.creado_por = request.user
    return formulario(request, form, "Registrar ingreso o gasto", "gestion:movimientos", autor)

@acceso("gestion.revertir_movimiento")
def revertir(request, pk):
    movimiento = get_object_or_404(Movimiento, pk=pk)
    form = ReversionForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        try:
            revertir_movimiento(pk, request.user, form.cleaned_data["fecha"], form.cleaned_data["motivo"])
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, "; ".join(error.messages) if isinstance(error, ValidationError) else "Este movimiento ya tiene una corrección.")
        else:
            messages.success(request, "Corrección registrada; el original permanece en el historial.")
            return redirect("gestion:movimientos")
    return render(request, "gestion/formulario.html", {
        "form": form, "titulo": f"Corregir movimiento #{pk}", "destino": "gestion:movimientos",
        "descripcion": "Se creará un movimiento de signo contrario por el mismo importe."})

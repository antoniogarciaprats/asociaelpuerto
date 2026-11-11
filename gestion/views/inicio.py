from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from gestion.models import Socio, Actividad, Cuota, Movimiento
from gestion.services.tesoreria import resumen

@login_required
def inicio(request):
    contexto = {}
    if request.user.has_perm("gestion.view_socio"):
        contexto["socios_activos"] = Socio.objects.filter(activo=True).count()
    if request.user.has_perm("gestion.view_actividad"):
        contexto["actividades"] = Actividad.objects.all().order_by("-inicio")[:4]
        contexto["actividades_abiertas"] = Actividad.objects.filter(estado="abierta").count()
    if request.user.has_perm("gestion.view_cuota"):
        contexto["cuotas_pendientes"] = Cuota.objects.filter(pago__isnull=True).count()
    if request.user.has_perm("gestion.view_movimiento"):
        contexto["balance"] = resumen(Movimiento.objects.all())
    return render(request, "gestion/inicio.html", contexto)

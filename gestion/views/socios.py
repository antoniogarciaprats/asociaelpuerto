from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from gestion.models import Socio
from gestion.forms.socios import SocioForm
from .common import acceso, formulario

@acceso("gestion.view_socio")
def lista(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "activos")
    socios = Socio.objects.all()
    if q:
        socios = socios.filter(Q(numero__icontains=q) | Q(nombre__icontains=q) | Q(apellidos__icontains=q))
    if estado in ("activos", "inactivos"):
        socios = socios.filter(activo=estado == "activos")
    return render(request, "gestion/socios.html", {
        "page_obj": Paginator(socios, 12).get_page(request.GET.get("page")), "q": q, "estado": estado})

@acceso("gestion.add_socio")
def crear(request):
    form = SocioForm(request.POST if request.method == "POST" else None)
    return formulario(request, form, "Nuevo socio", "gestion:socios")

@acceso("gestion.change_socio")
def editar(request, pk):
    socio = get_object_or_404(Socio, pk=pk)
    form = SocioForm(request.POST if request.method == "POST" else None, instance=socio)
    return formulario(request, form, "Editar socio · " + socio.numero, "gestion:socios")

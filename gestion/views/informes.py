import csv
from datetime import date
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from gestion.models import Movimiento
from gestion.forms.informes import PeriodoForm
from gestion.services.tesoreria import resumen
from .common import acceso

def celda_segura(valor):
    texto = str(valor)
    # Algunos programas de hoja de cálculo interpretan estas entradas como fórmulas.
    return "'" + texto if texto.lstrip().startswith(("=", "+", "-", "@")) or texto.startswith(("\t", "\r", "\n")) else texto

@acceso(("gestion.view_movimiento", "gestion.exportar_informe"))
def informe(request):
    hoy = timezone.localdate()
    form = PeriodoForm(request.GET if request.GET else {
        "desde": date(hoy.year, 1, 1), "hasta": hoy})
    datos = Movimiento.objects.none()
    contexto = {"form": form}
    if form.is_valid():
        desde, hasta = form.cleaned_data["desde"], form.cleaned_data["hasta"]
        datos = Movimiento.objects.filter(fecha__range=(desde, hasta)).select_related(
            "creado_por", "actividad").order_by("fecha", "pk")
        if request.GET.get("formato") == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="tesoreria_{desde}_{hasta}.csv"'
            response.write("\ufeff")
            writer = csv.writer(response, delimiter=";")
            writer.writerow(["ID", "Fecha", "Tipo", "Categoría", "Concepto", "Importe EUR", "Actividad", "Cuota", "Reversa de", "Autor"])
            for m in datos:
                fila = [m.pk, m.fecha.isoformat(), m.get_tipo_display(), m.get_categoria_display(),
                        m.concepto, format(m.importe, ".2f").replace(".", ","),
                        m.actividad.titulo if m.actividad else "", m.cuota_id or "",
                        m.reversa_de_id or "", m.creado_por.username]
                writer.writerow([celda_segura(v) for v in fila])
            return response
        anteriores = Movimiento.objects.filter(fecha__lt=desde)
        contexto.update(balance=resumen(datos), saldo_inicial=resumen(anteriores)["neto"],
                         desde=desde.isoformat(), hasta=hasta.isoformat())
        contexto["saldo_final"] = contexto["saldo_inicial"] + contexto["balance"]["neto"]
    elif request.GET.get("formato") == "csv":
        return HttpResponse("Periodo no válido. Revisa las fechas del informe.", status=400)
    contexto["page_obj"] = Paginator(datos, 15).get_page(request.GET.get("page"))
    return render(request, "gestion/informes.html", contexto)

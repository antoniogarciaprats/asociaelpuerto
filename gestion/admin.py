from django.contrib import admin
from .models import Socio, Actividad, Inscripcion, Cuota, Movimiento

class ConsultaAdmin(admin.ModelAdmin):
    """La administración consulta el dominio; las altas y cambios usan los servicios."""
    def has_add_permission(self, request):
        return False
    def has_change_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Socio)
class SocioAdmin(ConsultaAdmin):
    list_display = ["numero", "nombre", "apellidos", "activo"]
    search_fields = ["numero", "nombre", "apellidos"]
    list_filter = ["activo"]

@admin.register(Actividad)
class ActividadAdmin(ConsultaAdmin):
    list_display = ["titulo", "inicio", "aforo", "ocupadas", "estado"]
    list_filter = ["estado"]

@admin.register(Inscripcion)
class InscripcionAdmin(ConsultaAdmin):
    list_display = ["socio", "actividad", "activa", "asistio"]

@admin.register(Cuota)
class CuotaAdmin(ConsultaAdmin):
    list_display = ["socio", "ejercicio", "importe", "vencimiento", "estado"]

@admin.register(Movimiento)
class MovimientoAdmin(ConsultaAdmin):
    list_display = ["fecha", "tipo", "concepto", "importe", "creado_por"]
    list_filter = ["tipo", "categoria"]

admin.site.site_header = "Asocia Puerto · Administración"
admin.site.site_title = "Asocia Puerto"

from django.urls import path
from .views import inicio, socios, actividades, tesoreria, informes
app_name = "gestion"
urlpatterns = [
    path("", inicio.inicio, name="inicio"),
    path("socios/", socios.lista, name="socios"),
    path("socios/nuevo/", socios.crear, name="socio_nuevo"),
    path("socios/<int:pk>/editar/", socios.editar, name="socio_editar"),
    path("actividades/", actividades.lista, name="actividades"),
    path("actividades/nueva/", actividades.crear, name="actividad_nueva"),
    path("actividades/<int:pk>/", actividades.detalle, name="actividad"),
    path("actividades/<int:pk>/editar/", actividades.editar, name="actividad_editar"),
    path("actividades/<int:pk>/inscribir/", actividades.alta, name="inscribir"),
    path("inscripciones/<int:pk>/cancelar/", actividades.baja, name="cancelar"),
    path("inscripciones/<int:pk>/asistencia/", actividades.asistencia, name="asistencia"),
    path("cuotas/", tesoreria.cuotas, name="cuotas"),
    path("cuotas/nueva/", tesoreria.crear_cuota, name="cuota_nueva"),
    path("cuotas/<int:pk>/cobrar/", tesoreria.cobrar, name="cobrar"),
    path("tesoreria/", tesoreria.movimientos, name="movimientos"),
    path("tesoreria/nuevo/", tesoreria.crear_movimiento, name="movimiento_nuevo"),
    path("tesoreria/<int:pk>/revertir/", tesoreria.revertir, name="revertir"),
    path("informes/", informes.informe, name="informes"),
]

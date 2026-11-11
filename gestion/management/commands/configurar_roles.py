from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Crea o actualiza los permisos de Secretaría, Tesorería y Consulta."

    def handle(self, *args, **options):
        lectura = {"view_socio", "view_actividad", "view_inscripcion"}
        roles = {
            "Consulta": lectura,
            "Secretaría": lectura | {"add_socio", "change_socio", "add_actividad", "change_actividad",
                                      "add_inscripcion", "change_inscripcion"},
            "Tesorería": lectura | {"view_cuota", "add_cuota", "change_cuota", "view_movimiento",
                                    "add_movimiento", "revertir_movimiento", "exportar_informe"},
        }
        for nombre, codigos in roles.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = Permission.objects.filter(content_type__app_label="gestion", codename__in=codigos)
            grupo.permissions.set(permisos)
            self.stdout.write(self.style.SUCCESS(f"{nombre}: {permisos.count()} permisos"))

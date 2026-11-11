"""Carga manual e idempotente de datos completamente ficticios; no crea accesos."""
from datetime import timedelta, date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from gestion.models import Socio, Actividad, Cuota, Movimiento
from gestion.services.actividades import inscribir
from gestion.services.tesoreria import cobrar_cuota

class Command(BaseCommand):
    help = "Añade datos ficticios para clase; requiere un usuario existente como autor."
    def add_arguments(self, parser):
        parser.add_argument("--autor", required=True, help="Nombre de usuario que constará como autor")

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        try:
            autor = User.objects.get(username=options["autor"])
        except User.DoesNotExist as exc:
            raise CommandError("Crea primero el usuario con createsuperuser.") from exc
        hoy = timezone.localdate()
        personas = [("DEMO-001", "Ana", "Ejemplo Sierra"), ("DEMO-002", "Luis", "Prueba Mar"),
                    ("DEMO-003", "Carmen", "Muestra Sol"), ("DEMO-004", "Pablo", "Ensayo Río")]
        socios = []
        for numero, nombre, apellidos in personas:
            socio, _ = Socio.objects.get_or_create(numero=numero, defaults={
                "nombre": nombre, "apellidos": apellidos, "email": numero.lower()+"@example.org"})
            socios.append(socio)
        inicio = (timezone.now() + timedelta(days=7)).replace(hour=17, minute=0, second=0, microsecond=0)
        actividad, nueva = Actividad.objects.get_or_create(titulo="DEMO · Paseo fotográfico por El Puerto", defaults={
            "descripcion": "Actividad ficticia para practicar las inscripciones.", "lugar": "El Puerto de Santa María",
            "inicio": inicio, "fin": inicio+timedelta(hours=2), "aforo": 12})
        if nueva:
            inscribir(actividad.pk, socios[0].pk)
            inscribir(actividad.pk, socios[1].pk)
        for socio in socios:
            cuota, nueva_cuota = Cuota.objects.get_or_create(socio=socio, ejercicio=hoy.year, defaults={
                "importe": Decimal("30.00"), "vencimiento": date(hoy.year, 12, 31)})
            if nueva_cuota and socio == socios[0]:
                cobrar_cuota(cuota.pk, autor, hoy)
        if not Movimiento.objects.filter(concepto="DEMO · Material del taller").exists():
            Movimiento.objects.create(fecha=hoy, tipo="G", categoria="suministros",
                concepto="DEMO · Material del taller", importe=Decimal("12.50"), creado_por=autor)
        self.stdout.write(self.style.SUCCESS("Datos ficticios disponibles. No se han creado contraseñas."))

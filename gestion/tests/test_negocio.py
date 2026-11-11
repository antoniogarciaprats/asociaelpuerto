from datetime import date, timedelta
from decimal import Decimal
from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from gestion.models import Socio, Actividad, Inscripcion, Cuota, Movimiento
from gestion.forms.actividades import ActividadForm
from gestion.forms.tesoreria import MovimientoForm
from gestion.services.actividades import inscribir, cancelar, marcar_asistencia
from gestion.services.tesoreria import cobrar_cuota, revertir_movimiento, resumen

class BaseCaso(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser("admin", "a@example.org", "ClaveSoloPruebas-2026")
        cls.socio = Socio.objects.create(numero="S-001", nombre="Ana", apellidos="Ejemplo")
        cls.otro = Socio.objects.create(numero="S-002", nombre="Luis", apellidos="Prueba")
        cls.hoy = timezone.localdate()
        inicio = timezone.now() + timedelta(days=2)
        cls.actividad = Actividad.objects.create(titulo="Taller", inicio=inicio,
            fin=inicio+timedelta(hours=2), aforo=1)
        cls.cuota = Cuota.objects.create(socio=cls.socio, ejercicio=cls.hoy.year,
            importe=Decimal("30.00"), vencimiento=date(cls.hoy.year, 12, 31))

class ActividadesCaso(BaseCaso):
    def test_aforo_no_se_supera(self):
        inscribir(self.actividad.pk, self.socio.pk)
        with self.assertRaises(ValidationError):
            inscribir(self.actividad.pk, self.otro.pk)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 1)
        self.assertEqual(Inscripcion.objects.count(), 1)

    def test_duplicado_no_consume_plaza(self):
        self.actividad.aforo = 3
        self.actividad.save()
        inscribir(self.actividad.pk, self.socio.pk)
        with self.assertRaises(ValidationError):
            inscribir(self.actividad.pk, self.socio.pk)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 1)

    def test_inactivo_no_consume_plaza(self):
        self.socio.activo = False
        self.socio.save()
        with self.assertRaises(ValidationError):
            inscribir(self.actividad.pk, self.socio.pk)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 0)

    def test_cancelacion_y_reinscripcion(self):
        i = inscribir(self.actividad.pk, self.socio.pk)
        cancelar(i.pk)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 0)
        with self.assertRaises(ValidationError):
            cancelar(i.pk)
        nuevo = inscribir(self.actividad.pk, self.socio.pk)
        self.assertEqual(nuevo.pk, i.pk)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 1)

    def test_actividad_cerrada_y_pasada(self):
        for cambios in [{"estado": "cerrada"}, {"inicio": timezone.now()-timedelta(hours=1)}]:
            Actividad.objects.filter(pk=self.actividad.pk).update(**cambios)
            with self.assertRaises(ValidationError):
                inscribir(self.actividad.pk, self.socio.pk)

    def test_asistencia_solo_cuando_comienza(self):
        i = inscribir(self.actividad.pk, self.socio.pk)
        with self.assertRaises(ValidationError):
            marcar_asistencia(i.pk)
        Actividad.objects.filter(pk=self.actividad.pk).update(inicio=timezone.now()-timedelta(hours=1))
        marcar_asistencia(i.pk)
        i.refresh_from_db()
        self.assertTrue(i.asistio)
        with self.assertRaises(ValidationError):
            cancelar(i.pk)

    def test_fechas_invalidas(self):
        self.actividad.fin = self.actividad.inicio
        with self.assertRaises(ValidationError):
            self.actividad.full_clean()

    def test_bd_impide_reducir_aforo(self):
        inscribir(self.actividad.pk, self.socio.pk)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Actividad.objects.filter(pk=self.actividad.pk).update(aforo=0)

class TesoreriaCaso(BaseCaso):
    def test_emitir_no_es_cobrar(self):
        self.assertEqual(resumen(Movimiento.objects.all())["neto"], Decimal("0.00"))
        self.assertEqual(self.cuota.estado, "Pendiente")

    def test_doble_cobro_no_duplica(self):
        cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        with self.assertRaises(ValidationError):
            cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        self.assertEqual(Movimiento.objects.count(), 1)
        self.cuota.refresh_from_db()
        self.assertEqual(self.cuota.estado, "Pagada")

    def test_revertir_reabre_cuota_y_permite_nuevo_cobro(self):
        m = cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        revertir_movimiento(m.pk, self.usuario, self.hoy, "Cobro devuelto")
        self.cuota.refresh_from_db()
        self.assertIsNone(self.cuota.pago_id)
        self.assertEqual(resumen(Movimiento.objects.all())["neto"], Decimal("0.00"))
        cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        self.assertEqual(Movimiento.objects.count(), 3)
        self.assertEqual(resumen(Movimiento.objects.all())["neto"], Decimal("30.00"))

    def test_reversion_unica_y_no_se_revierte_inverso(self):
        m = cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        inverso = revertir_movimiento(m.pk, self.usuario, self.hoy, "Error")
        for pk in (m.pk, inverso.pk):
            with self.assertRaises(ValidationError):
                revertir_movimiento(pk, self.usuario, self.hoy, "Otra vez")
        self.assertEqual(Movimiento.objects.count(), 2)

    def test_fecha_futura_y_anterior_se_rechazan(self):
        with self.assertRaises(ValidationError):
            cobrar_cuota(self.cuota.pk, self.usuario, self.hoy+timedelta(days=1))
        self.assertEqual(Movimiento.objects.count(), 0)
        m = cobrar_cuota(self.cuota.pk, self.usuario, self.hoy)
        with self.assertRaises(ValidationError):
            revertir_movimiento(m.pk, self.usuario, self.hoy-timedelta(days=1), "Error")

    def test_cuota_unica_e_importe_positivo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cuota.objects.create(socio=self.socio, ejercicio=self.hoy.year,
                importe=30, vencimiento=self.hoy)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cuota.objects.create(socio=self.otro, ejercicio=self.hoy.year,
                importe=0, vencimiento=self.hoy)

    def test_formulario_no_permite_cuotas_manuales(self):
        form = MovimientoForm({"fecha": self.hoy, "tipo": "I", "categoria": "cuotas", "concepto": "Intento", "importe": "30.00"})
        self.assertFalse(form.is_valid())
        self.assertIn("categoria", form.errors)

    def test_decimales_y_gastos(self):
        for importe in ("0.10", "0.20"):
            Movimiento.objects.create(tipo="I", categoria="otros", concepto="Entrada",
                importe=Decimal(importe), creado_por=self.usuario)
        Movimiento.objects.create(tipo="G", categoria="otros", concepto="Salida",
            importe=Decimal("0.05"), creado_por=self.usuario)
        self.assertEqual(resumen(Movimiento.objects.all())["neto"], Decimal("0.25"))

class AccesoYVistasCaso(BaseCaso):
    def setUp(self):
        call_command("configurar_roles", stdout=StringIO())
        self.lector = get_user_model().objects.create_user("lector", password="ConsultaPruebas-2026")
        self.lector.groups.add(Group.objects.get(name="Consulta"))
        self.secretaria = get_user_model().objects.create_user("secretaria", password="SecretariaPruebas-2026")
        self.secretaria.groups.add(Group.objects.get(name="Secretaría"))
        self.tesorero = get_user_model().objects.create_user("tesorero", password="TesoreriaPruebas-2026")
        self.tesorero.groups.add(Group.objects.get(name="Tesorería"))

    def test_anonimo_redirigido(self):
        for ruta in ["/", "/socios/", "/actividades/", "/cuotas/", "/tesoreria/", "/informes/"]:
            self.assertEqual(self.client.get(ruta).status_code, 302)

    def test_consulta_no_escribe_ni_ve_tesoreria(self):
        self.client.force_login(self.lector)
        for ruta in ["/", "/socios/", "/actividades/"]:
            self.assertEqual(self.client.get(ruta).status_code, 200)
        for ruta in ["/socios/nuevo/", "/cuotas/", "/tesoreria/", "/informes/"]:
            self.assertEqual(self.client.get(ruta).status_code, 403)
        self.assertEqual(self.client.post("/socios/nuevo/", {}).status_code, 403)
        self.assertNotContains(self.client.get("/"), "Saldo registrado")

    def test_secretaria_y_tesoreria_separadas(self):
        self.client.force_login(self.secretaria)
        self.assertEqual(self.client.get("/socios/nuevo/").status_code, 200)
        self.assertEqual(self.client.get("/tesoreria/").status_code, 403)
        self.client.force_login(self.tesorero)
        self.assertEqual(self.client.get("/tesoreria/").status_code, 200)
        self.assertEqual(self.client.get("/socios/nuevo/").status_code, 403)

    def test_operaciones_por_get_no_modifican(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("gestion:inscribir", args=[self.actividad.pk])).status_code, 405)
        self.client.get(reverse("gestion:cobrar", args=[self.cuota.pk]))
        self.assertEqual(Movimiento.objects.count(), 0)
        self.assertEqual(Inscripcion.objects.count(), 0)

    def test_csrf_obligatorio(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post("/socios/nuevo/", {}).status_code, 403)

    def test_paginas_y_errores(self):
        self.client.force_login(self.usuario)
        for ruta in ["/", "/socios/", "/socios/nuevo/", f"/socios/{self.socio.pk}/editar/",
                     "/actividades/", "/actividades/nueva/", f"/actividades/{self.actividad.pk}/",
                     f"/actividades/{self.actividad.pk}/editar/", "/cuotas/", "/cuotas/nueva/",
                     f"/cuotas/{self.cuota.pk}/cobrar/", "/tesoreria/", "/tesoreria/nuevo/", "/informes/"]:
            with self.subTest(ruta=ruta):
                self.assertEqual(self.client.get(ruta).status_code, 200)
        self.assertEqual(self.client.get("/socios/9999/editar/").status_code, 404)

    def test_editar_actividad_conserva_contador(self):
        inscribir(self.actividad.pk, self.socio.pk)
        self.client.force_login(self.usuario)
        respuesta = self.client.post(reverse("gestion:actividad_editar", args=[self.actividad.pk]), {
            "titulo": "Nuevo título", "lugar": "El Puerto", "inicio": timezone.localtime(self.actividad.inicio).strftime("%Y-%m-%dT%H:%M"),
            "fin": timezone.localtime(self.actividad.fin).strftime("%Y-%m-%dT%H:%M"), "aforo": "2", "estado": "abierta"})
        self.assertEqual(respuesta.status_code, 302)
        self.actividad.refresh_from_db()
        self.assertEqual(self.actividad.ocupadas, 1)

    def test_csv_filtro_y_formula_segura(self):
        self.client.force_login(self.tesorero)
        Movimiento.objects.create(fecha=self.hoy, tipo="I", categoria="otros", concepto="=1+1",
            importe=Decimal("2.00"), creado_por=self.usuario)
        Movimiento.objects.create(fecha=self.hoy-timedelta(days=2), tipo="I", categoria="otros", concepto="Anterior",
            importe=Decimal("9.00"), creado_por=self.usuario)
        respuesta = self.client.get("/informes/", {"desde": self.hoy.isoformat(), "hasta": self.hoy.isoformat(), "formato": "csv"})
        texto = respuesta.content.decode("utf-8-sig")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("'=1+1", texto)
        self.assertNotIn("Anterior", texto)
        self.assertIn("2,00", texto)

    def test_periodo_invalido_no_exporta(self):
        self.client.force_login(self.tesorero)
        respuesta = self.client.get("/informes/", {"desde": "mal", "hasta": "2026-11-06", "formato": "csv"})
        self.assertEqual(respuesta.status_code, 400)

    def test_saldo_inicial_y_final(self):
        self.client.force_login(self.usuario)
        Movimiento.objects.create(fecha=self.hoy-timedelta(days=2), tipo="I", categoria="otros", concepto="Anterior", importe=10, creado_por=self.usuario)
        Movimiento.objects.create(fecha=self.hoy, tipo="G", categoria="otros", concepto="Actual", importe=3, creado_por=self.usuario)
        respuesta = self.client.get("/informes/", {"desde": self.hoy.isoformat(), "hasta": self.hoy.isoformat()})
        self.assertEqual(respuesta.context["saldo_inicial"], Decimal("10.00"))
        self.assertEqual(respuesta.context["saldo_final"], Decimal("7.00"))

    def test_socio_alta_edicion_y_busqueda(self):
        self.client.force_login(self.secretaria)
        respuesta = self.client.post("/socios/nuevo/", {"numero": " s-003 ", "nombre": "Carmen", "apellidos": "Muestra", "fecha_alta": self.hoy, "activo": "on"})
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(Socio.objects.filter(numero="S-003").exists())
        self.assertContains(self.client.get("/socios/?q=Muestra"), "Carmen")

    def test_paginacion_conserva_busqueda(self):
        for n in range(15):
            Socio.objects.create(numero=f"P-{n}", nombre="Pagina", apellidos=str(n))
        self.client.force_login(self.lector)
        respuesta = self.client.get("/socios/?q=Pagina")
        self.assertContains(respuesta, "q=Pagina&amp;page=2")

    def test_demo_idempotente(self):
        for _ in range(2):
            call_command("datos_demo", autor="admin", stdout=StringIO())
        self.assertEqual(Socio.objects.filter(numero__startswith="DEMO").count(), 4)
        self.assertEqual(Movimiento.objects.filter(concepto="DEMO · Material del taller").count(), 1)
        self.assertEqual(Movimiento.objects.filter(cuota__socio__numero="DEMO-001").count(), 1)

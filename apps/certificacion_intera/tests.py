from django.contrib.auth.models import Group, Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import default_storage
from django.db.models.deletion import ProtectedError
from django.test import Client, SimpleTestCase, TestCase
from django.test.utils import override_settings
from django.urls import reverse
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from io import BytesIO
import re
from types import SimpleNamespace
from unittest.mock import patch
from urllib import error
from .models import Escuela
from .models import (
    AplicacionInstrumento,
    AplicacionPublica,
    Canalizacion,
    Consejeria,
    ConfiguracionInstrumento,
    Participante,
    ProcesoCertificacion,
    RespuestaInstrumento,
    ResultadoInstrumento,
    EntrevistaSeguimiento,
    BitacoraProceso,
    SolicitudAtencion,
    EntrevistaUnoAUno,
    RespuestaEntrevistaUnoAUno,
)
from apps.portafolio.models import (
    CalculadoraInstrumento,
    CategoriaDocumento,
    Documento,
    ImportacionInstrumento,
    Instrumento,
    PreguntaInstrumento,
    RevisionInstrumento,
    RelacionDocumento,
    VersionDocumento,
)
from apps.portafolio.services_documentales import (
    incorporar_documento_contextual,
    obtener_documentos_contextuales,
)
from apps.portafolio.services_entrevista import CLAVE_ENTREVISTA
from apps.portafolio.services_calificacion import (
    ADVERTENCIA_RESULTADO_ORIENTATIVO,
    calcular_resultado,
    validar_variante_por_edad,
)
from . import consultorio_web
from .templatetags.intera_publica import nombre_publico_intera


def crear_documento_con_version(**datos):
    archivo = datos.pop('archivo')
    version = datos.pop('version', '1.0')
    cargado_por = datos.pop('cargado_por', None)
    observaciones = datos.pop('observaciones', '')
    datos.pop('tipo_archivo', None)
    documento = Documento.objects.create(**datos)
    documento.agregar_version(
        archivo=archivo,
        version=version,
        cargado_por=cargado_por,
        observaciones=observaciones,
    )
    return documento


class NombrePublicoInstrumentoTests(SimpleTestCase):

    def test_plutchik_usa_nombre_neutro_solo_en_presentacion_publica(self):
        instrumento = SimpleNamespace(
            clave='ersp-plutchik-adolescentes',
            nombre='Escala de Riesgo Suicida de Plutchik',
        )

        self.assertEqual(nombre_publico_intera(instrumento), 'Escala de Plutchik')
        self.assertEqual(
            instrumento.nombre,
            'Escala de Riesgo Suicida de Plutchik',
        )

    def test_instrumento_normal_conserva_su_nombre(self):
        instrumento = SimpleNamespace(
            clave='dass-21-adolescentes',
            nombre='DASS-21',
        )

        self.assertEqual(nombre_publico_intera(instrumento), 'DASS-21')

    def test_rosenberg_usa_nombre_neutro_solo_en_presentacion_publica(self):
        instrumento = SimpleNamespace(
            clave='rse-autoestima',
            nombre='Escala de Autoestima de Rosenberg',
        )

        self.assertEqual(
            nombre_publico_intera(instrumento),
            'Escala de Rosenberg',
        )
        self.assertEqual(
            instrumento.nombre,
            'Escala de Autoestima de Rosenberg',
        )

class FakeHttpResponse:

    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body

def crear_instrumento_bateria(
    clave,
    nombre,
    reactivos,
    estado_calculadora,
    variante='Adolescentes',
):
    categoria, _ = CategoriaDocumento.objects.get_or_create(nombre='Pruebas de batería')
    documento = crear_documento_con_version(
        nombre=f'Fuente {clave}',
        categoria=categoria,
        archivo=f'portafolio/documentos/{clave}.xlsx',
    )
    instrumento = Instrumento.objects.create(
        nombre=nombre,
        clave=clave,
        version='1.0',
    )
    PreguntaInstrumento.objects.bulk_create(
        [
            PreguntaInstrumento(
                instrumento=instrumento,
                orden=orden,
                texto=f'Reactivo {orden}',
                opciones=[{'valor': '1', 'etiqueta': 'Sí'}],
            )
            for orden in range(1, reactivos + 1)
        ],
    )
    CalculadoraInstrumento.objects.create(
        instrumento=instrumento,
        clave=f'calc-{clave}',
        version_regla='1.0',
        estado=estado_calculadora,
        definicion={},
        huella_contenido=(clave * 64)[:64],
    )
    ImportacionInstrumento.objects.create(
        instrumento=instrumento,
        documento=documento,
        huella_contenido=(clave * 64)[:64],
        metadatos={
            'Variante': variante,
            'Número de reactivos': reactivos,
        },
    )
    return instrumento

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class EscuelaRevisionYFichaTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username='escuelas-prueba',
            password='prueba',
        )
        self.user.groups.add(
            Group.objects.get_or_create(name='Certificación')[0],
        )
        self.client.force_login(self.user)
        self.escuela = Escuela.objects.create(
            nombre='Colegio Central',
            director='Directora de prueba',
            cantidad_total_alumnos=80,
            estado='Coahuila',
            municipio='Saltillo',
            correo='contacto@colegio.test',
            telefono='844-111-2222',
        )

    def _post_coincidencia(self):
        return self.client.post(
            reverse('certificacion_intera:escuela_crear'),
            {
                'nombre': '  colegio   central ',
                'director': 'Otra dirección',
                'cantidad_total_alumnos': 20,
                'estado': 'Coahuila',
                'municipio': 'Saltillo',
                'correo': 'CONTACTO@COLEGIO.TEST',
                'telefono': '(844) 111 2222',
            },
        )

    def test_revision_temporal_no_crea_y_confirmacion_es_unica(self):
        response = self._post_coincidencia()
        self.assertEqual(Escuela.objects.count(), 1)
        self.assertContains(
            response,
            'Encontramos escuelas que podrían coincidir',
        )
        token = response.context['revision_token']
        clave = f'intera_revision_escuela_{token}'
        self.assertIn(clave, self.client.session)
        confirmado = self.client.post(
            reverse('certificacion_intera:escuela_confirmar'),
            {'revision_token': token},
        )
        self.assertEqual(Escuela.objects.count(), 2)
        self.assertNotIn(clave, self.client.session)
        self.assertEqual(confirmado.status_code, 302)
        self.client.post(
            reverse('certificacion_intera:escuela_confirmar'),
            {'revision_token': token},
        )
        self.assertEqual(Escuela.objects.count(), 2)

    def test_revision_ajena_o_expirada_no_crea(self):
        response = self._post_coincidencia()
        token = response.context['revision_token']
        other = Client()
        other.force_login(self.user)
        other.post(
            reverse('certificacion_intera:escuela_confirmar'),
            {'revision_token': token},
        )
        self.assertEqual(Escuela.objects.count(), 1)
        session = self.client.session
        session[f'intera_revision_escuela_{token}']['creado_en'] = 0
        session.save()
        self.client.post(
            reverse('certificacion_intera:escuela_confirmar'),
            {'revision_token': token},
        )
        self.assertEqual(Escuela.objects.count(), 1)

    def test_ficha_tabs_director_y_retorno(self):
        retorno = '/certificacion-intera/escuelas/?q=colegio&page=2'
        for tab in (
            'resumen',
            'datos',
            'contactos',
            'procesos',
            'historial',
        ):
            response = self.client.get(
                reverse(
                    'certificacion_intera:escuela_detalle',
                    args=[self.escuela.id],
                ),
                {'tab': tab, 'return_url': retorno},
            )
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'return_url=')
        resumen = self.client.get(
            reverse(
                'certificacion_intera:escuela_detalle',
                args=[self.escuela.id],
            ),
        )
        self.assertContains(resumen, 'Ficha de la escuela')
        self.assertContains(resumen, 'Directora de prueba')
        self.assertContains(resumen, 'Capacidad estimada')
        self.assertContains(resumen, 'Participantes registrados')

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class DashboardCertificacionInteraTests(TestCase):

    def _usuario_y_escuela_para_acceso_publico(self):
        usuario = User.objects.create_user(username='acceso_escuela', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        escuela = Escuela.objects.create(
            nombre='Escuela con acceso',
            director='Dirección',
            cantidad_total_alumnos=100,
            estado='México',
            municipio='Toluca',
        )
        self.client.force_login(usuario)
        return usuario, escuela

    def test_ficha_reutiliza_acceso_general_del_proceso_vigente(self):
        usuario, escuela = self._usuario_y_escuela_para_acceso_publico()
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            nombre='Proceso vigente',
            estado=ProcesoCertificacion.Estado.APLICACION,
            fecha_inicio=date(2026, 8, 1),
            creado_por=usuario,
        )
        publica = AplicacionPublica.objects.create(proceso=proceso)

        respuesta = self.client.get(
            reverse('certificacion_intera:escuela_detalle', args=[escuela.id]),
        )

        url_absoluta = 'http://testserver' + publica.url_publica
        self.assertContains(respuesta, 'Acceso para participantes')
        self.assertContains(respuesta, 'Proceso vigente')
        self.assertContains(respuesta, url_absoluta, count=2)
        self.assertContains(respuesta, publica.url_publica)
        self.assertContains(
            respuesta,
            reverse('certificacion_intera:aplicacion_publica_proceso_qr', args=[proceso.id]),
        )
        self.assertEqual(AplicacionPublica.objects.filter(proceso=proceso).count(), 1)

    def test_ficha_sin_acceso_no_lo_genera_y_enlaza_al_proceso_vigente(self):
        usuario, escuela = self._usuario_y_escuela_para_acceso_publico()
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            nombre='Proceso sin acceso',
            estado=ProcesoCertificacion.Estado.CONFIGURACION,
            fecha_inicio=date(2026, 8, 1),
            creado_por=usuario,
        )

        respuesta = self.client.get(
            reverse('certificacion_intera:escuela_detalle', args=[escuela.id]),
        )

        self.assertContains(respuesta, 'Este proceso todavía no cuenta con un acceso público.')
        self.assertContains(respuesta, 'Ir al proceso →')
        self.assertContains(
            respuesta,
            reverse('certificacion_intera:proceso_detalle', args=[proceso.id]),
        )
        self.assertFalse(AplicacionPublica.objects.filter(proceso=proceso).exists())

    def test_usuario_autorizado_puede_ver_el_dashboard(self):
        usuario = User.objects.create_user(username='certificacion', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('certificacion_intera:dashboard'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(
            respuesta,
            'certificacion_intera/dashboard.html',
        )
        self.assertContains(respuesta, 'Procesos activos')
        self.assertContains(respuesta, 'Trabajo pendiente')

    def test_listado_separa_estado_operativo_etapa_y_aplica_filtros(self):
        usuario = User.objects.create_user(username='filtros-proceso', password='secreto')
        usuario.groups.add(Group.objects.get_or_create(name='Certificación')[0])
        escuela = Escuela.objects.create(
            nombre='Escuela filtros',
            director='Dirección',
            cantidad_total_alumnos=50,
            estado='México',
            municipio='Toluca',
        )
        ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            nombre='Proceso configurándose',
            estado=ProcesoCertificacion.Estado.CONFIGURACION,
            fecha_inicio=date(2026, 8, 1),
        )
        ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2025-2026',
            nombre='Proceso histórico',
            estado=ProcesoCertificacion.Estado.CERRADO,
            fecha_inicio=date(2025, 8, 1),
            fecha_cierre=date(2026, 6, 30),
        )
        self.client.force_login(usuario)
        url = reverse('certificacion_intera:procesos')

        listado = self.client.get(url)
        self.assertContains(listado, 'Estado operativo')
        self.assertContains(listado, 'Activo')
        self.assertContains(listado, 'Configuración')
        self.assertContains(listado, 'Cerrado')
        self.assertContains(listado, 'Finalizado')

        activos = self.client.get(url, {'operativo': 'activo'})
        self.assertContains(activos, 'Proceso configurándose')
        self.assertNotContains(activos, 'Proceso histórico')
        cerrados = self.client.get(url, {'operativo': 'cerrado'})
        self.assertContains(cerrados, 'Proceso histórico')
        self.assertNotContains(cerrados, 'Proceso configurándose')
        configuracion = self.client.get(
            url,
            {'etapa': ProcesoCertificacion.Estado.CONFIGURACION},
        )
        self.assertContains(configuracion, 'Proceso configurándose')
        self.assertNotContains(configuracion, 'Proceso histórico')

    def test_usuario_sin_grupo_recibe_error_de_permiso(self):
        usuario = User.objects.create_user(username='sin_permiso', password='secreto')
        self.client.force_login(usuario)
        respuesta = self.client.get(reverse('certificacion_intera:dashboard'))
        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_autorizado_puede_registrar_una_escuela(self):
        usuario = User.objects.create_user(username='captura', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        self.client.force_login(usuario)
        respuesta = self.client.post(
            reverse('certificacion_intera:escuela_crear'),
            {
                'nombre': 'Escuela Ejemplo',
                'director': 'Ana Pérez',
                'cantidad_total_alumnos': 120,
                'estado': 'Ciudad de México',
                'municipio': 'Coyoacán',
            },
        )
        escuela = Escuela.objects.get(nombre='Escuela Ejemplo')
        self.assertRedirects(
            respuesta,
            reverse('certificacion_intera:escuela_detalle', args=[escuela.id]),
        )

    def test_usuario_autorizado_puede_listar_consultar_y_editar_una_escuela(self):
        usuario = User.objects.create_user(username='gestion', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        escuela = Escuela.objects.create(
            nombre='Instituto Inicial',
            director='Luis Díaz',
            cantidad_total_alumnos=80,
            estado='México',
            municipio='Toluca',
        )
        self.client.force_login(usuario)
        listado = self.client.get(reverse('certificacion_intera:escuelas'))
        expediente = self.client.get(
            reverse('certificacion_intera:escuela_detalle', args=[escuela.id]),
        )
        respuesta = self.client.post(
            reverse('certificacion_intera:escuela_editar', args=[escuela.id]),
            {
                'nombre': 'Instituto Actualizado',
                'director': 'Luis Díaz',
                'cantidad_total_alumnos': 95,
                'estado': 'México',
                'municipio': 'Toluca',
            },
        )
        self.assertContains(listado, 'Instituto Inicial')
        self.assertContains(expediente, 'Luis Díaz')
        self.assertRedirects(
            respuesta,
            reverse('certificacion_intera:escuela_detalle', args=[escuela.id]),
        )
        escuela.refresh_from_db()
        self.assertEqual(escuela.nombre, 'Instituto Actualizado')

    def test_proceso_permite_fecha_de_cierre_vacia_y_no_cierra_antes_de_tiempo(self):
        usuario = User.objects.create_user(username='proceso', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        escuela = Escuela.objects.create(
            nombre='Escuela proceso',
            director='Dirección',
            cantidad_total_alumnos=30,
            estado='Estado',
            municipio='Municipio',
        )
        instrumento = crear_instrumento_bateria(
            'dass-21-adolescentes',
            'DASS-21',
            21,
            CalculadoraInstrumento.Estado.ORIENTATIVA,
        )
        self.client.force_login(usuario)
        abierto = self.client.post(
            reverse('certificacion_intera:proceso_crear', args=[escuela.id]),
            {
                'ciclo_escolar': '2026-2027',
                'nombre': 'Proceso abierto',
                'fecha_inicio': date.today().isoformat(),
                'fecha_cierre': '',
                'observaciones': '',
                'instrumentos': [instrumento.id],
                f'orden_{instrumento.id}': 1,
            },
        )
        proceso = ProcesoCertificacion.objects.get(nombre='Proceso abierto')
        self.assertRedirects(
            abierto,
            reverse('certificacion_intera:proceso_detalle', args=[proceso.id]),
        )
        self.assertIsNone(proceso.fecha_cierre)
        cerrado = self.client.post(
            reverse('certificacion_intera:proceso_crear', args=[escuela.id]),
            {
                'ciclo_escolar': '2027-2028',
                'nombre': 'Proceso futuro',
                'fecha_inicio': date.today().isoformat(),
                'fecha_cierre': (date.today() + timedelta(days=2)).isoformat(),
                'observaciones': '',
                'instrumentos': [instrumento.id],
                f'orden_{instrumento.id}': 1,
            },
        )
        self.assertEqual(cerrado.status_code, 200)
        self.assertFalse(
            ProcesoCertificacion.objects.filter(nombre='Proceso futuro').exists(),
        )

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class FlujoInteraConPortafolioTests(TestCase):

    def test_el_proceso_consume_instrumentos_y_preguntas_de_portafolio(self):
        escuela = Escuela.objects.create(
            nombre='Escuela',
            director='Dirección',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            fecha_inicio='2026-08-02',
        )
        categoria, _ = CategoriaDocumento.objects.get_or_create(nombre='Instrumento')
        documento = crear_documento_con_version(
            nombre='Origen',
            categoria=categoria,
            archivo='portafolio/documentos/origen.xlsx',
        )
        instrumento = Instrumento.objects.create(
            nombre='Instrumento compartido',
            clave='compartido',
            documento_origen=documento,
        )
        pregunta = PreguntaInstrumento.objects.create(
            instrumento=instrumento,
            orden=1,
            texto='Pregunta',
        )
        configuracion = ConfiguracionInstrumento.objects.create(
            proceso=proceso,
            instrumento=instrumento,
        )
        participante = Participante.objects.create(
            proceso=proceso,
            nombre='Participante',
            numero_alumno='001',
        )
        aplicacion = AplicacionInstrumento.objects.create(
            proceso=proceso,
            participante=participante,
            instrumento=instrumento,
        )
        respuesta = RespuestaInstrumento.objects.create(
            aplicacion=aplicacion,
            pregunta=pregunta,
            valor='Sí',
        )
        self.assertEqual(configuracion.instrumento, instrumento)
        self.assertEqual(instrumento.documento_origen, documento)
        self.assertEqual(aplicacion.instrumento, instrumento)
        self.assertEqual(respuesta.pregunta, pregunta)

    def test_panel_del_proceso_expone_operaciones_y_aplicaciones_publicas(self):
        usuario = User.objects.create_user(username='coordinador', password='secreto')
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        escuela = Escuela.objects.create(
            nombre='Escuela panel',
            director='DirecciÃ³n',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            fecha_inicio='2026-08-02',
        )
        instrumento = Instrumento.objects.create(nombre='Instrumento panel', clave='panel')
        ConfiguracionInstrumento.objects.create(
            proceso=proceso,
            instrumento=instrumento,
        )
        BitacoraProceso.objects.create(
            proceso=proceso,
            evento='Evento visible',
            descripcion='Detalle reutilizado',
            usuario=usuario,
        )
        self.client.force_login(usuario)
        panel = self.client.get(
            reverse('certificacion_intera:proceso_detalle', args=[proceso.id]),
            {'tab': 'bateria'},
        )
        publicas = self.client.get(
            reverse(
                'certificacion_intera:proceso_aplicaciones_publicas',
                args=[proceso.id],
            ),
        )
        bitacora = self.client.get(
            reverse('certificacion_intera:proceso_detalle', args=[proceso.id]),
            {'tab': 'bitacora'},
        )
        bitacora_independiente = self.client.get(
            reverse('certificacion_intera:proceso_bitacora', args=[proceso.id]),
        )
        self.assertEqual(panel.status_code, 200)
        self.assertContains(panel, 'Batería y aplicación')
        self.assertContains(panel, 'Instrumento panel')
        self.assertContains(publicas, 'Abrir enlace')
        self.assertEqual(bitacora.status_code, 200)
        self.assertContains(bitacora, 'Bitácora')
        self.assertContains(bitacora, 'Evento visible')
        self.assertContains(bitacora, 'Detalle reutilizado')
        self.assertNotContains(bitacora, 'Consultar bitácora')
        self.assertContains(bitacora_independiente, 'Evento visible')
        self.assertContains(bitacora_independiente, 'Detalle reutilizado')

    def test_enlace_publico_usa_portafolio_y_persiste_una_respuesta(self):
        usuario = User.objects.create_user(
            username='coordinadora-publica',
            password='secreto',
        )
        grupo, _ = Group.objects.get_or_create(name='Certificación')
        usuario.groups.add(grupo)
        categoria = CategoriaDocumento.objects.create(nombre='Instrumentos públicos')
        documento = crear_documento_con_version(
            nombre='Cuestionario origen',
            categoria=categoria,
            archivo='portafolio/documentos/cuestionario.xlsx',
        )
        instrumento = Instrumento.objects.create(
            nombre='Bienestar escolar',
            clave='bienestar-escolar',
            documento_origen=documento,
        )
        pregunta = PreguntaInstrumento.objects.create(
            instrumento=instrumento,
            orden=1,
            texto='¿Te sientes bien?',
            opciones=[
                {'valor': 'si', 'etiqueta': 'Sí'},
                {'valor': 'no', 'etiqueta': 'No'},
            ],
        )
        escuela = Escuela.objects.create(
            nombre='Escuela pública',
            director='Dirección',
            cantidad_total_alumnos=20,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            fecha_inicio='2026-08-02',
        )
        self.client.force_login(usuario)
        configuracion = ConfiguracionInstrumento.objects.create(
            proceso=proceso,
            instrumento=instrumento,
            orden=1,
        )
        publica = AplicacionPublica.objects.create(configuracion=configuracion)
        self.assertEqual(
            AplicacionPublica.objects.filter(configuracion=publica.configuracion).count(),
            1,
        )
        self.client.logout()
        pagina = self.client.get(publica.url_publica)
        self.assertEqual(pagina.status_code, 200)
        self.assertContains(pagina, pregunta.texto)
        enviada = self.client.post(
            publica.url_publica,
            {
                'nombre': 'Alumno Uno',
                'numero_alumno': 'A-001',
                'grupo': '1A',
                f'pregunta_{pregunta.id}': 'si',
            },
        )
        self.assertEqual(enviada.status_code, 200)
        self.assertContains(enviada, 'Gracias por responder')
        participante = Participante.objects.get(proceso=proceso, numero_alumno='A-001')
        aplicacion = AplicacionInstrumento.objects.get(
            proceso=proceso,
            participante=participante,
            instrumento=instrumento,
        )
        self.assertEqual(aplicacion.aplicacion_publica, publica)
        self.assertEqual(
            RespuestaInstrumento.objects.filter(aplicacion=aplicacion).count(),
            1,
        )
        self.assertTrue(
            ResultadoInstrumento.objects.filter(
                aplicacion=aplicacion,
                estado=ResultadoInstrumento.Estado.PENDIENTE,
            ).exists(),
        )
        repetida = self.client.post(
            publica.url_publica,
            {
                'nombre': 'Alumno Uno',
                'numero_alumno': 'A-001',
                'grupo': '1A',
                f'pregunta_{pregunta.id}': 'si',
            },
        )
        self.assertContains(repetida, 'ya fue respondido')
        self.assertEqual(
            RespuestaInstrumento.objects.filter(aplicacion=aplicacion).count(),
            1,
        )
        self.client.force_login(usuario)
        panel = self.client.get(
            reverse('certificacion_intera:proceso_detalle', args=[proceso.id]),
            {'tab': 'bateria'},
        )
        self.assertContains(panel, 'Batería y aplicación')
        self.assertContains(panel, publica.url_publica)

    def test_aplicacion_publica_guarda_un_instrumento_largo_completo(self):
        escuela = Escuela.objects.create(
            nombre='Escuela cuestionario largo',
            director='Dirección',
            cantidad_total_alumnos=120,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2028-2029',
            fecha_inicio='2026-08-02',
        )
        instrumento = Instrumento.objects.create(
            nombre='Cuestionario largo',
            clave='cuestionario-largo',
        )
        preguntas = [
            PreguntaInstrumento(
                instrumento=instrumento,
                orden=orden,
                texto=f'Pregunta {orden}',
                opciones=[
                    {'valor': '1', 'etiqueta': 'Sí'},
                    {'valor': '0', 'etiqueta': 'No'},
                ],
            )
            for orden in range(1, 120)
        ]
        PreguntaInstrumento.objects.bulk_create(preguntas)
        configuracion = ConfiguracionInstrumento.objects.create(
            proceso=proceso,
            instrumento=instrumento,
        )
        publica = AplicacionPublica.objects.create(configuracion=configuracion)
        datos_incompletos = {
            'nombre': 'Alumno largo',
            'numero_alumno': 'L-001',
            'grupo': '1A',
            f'pregunta_{instrumento.preguntas.first().id}': '1',
        }
        incompleta = self.client.post(publica.url_publica, datos_incompletos)
        self.assertContains(incompleta, 'Faltan 118 preguntas obligatorias')
        self.assertFalse(
            Participante.objects.filter(proceso=proceso, numero_alumno='L-001').exists(),
        )
        datos_completos = {
            'nombre': 'Alumno largo',
            'numero_alumno': 'L-001',
            'grupo': '1A',
        }
        datos_completos.update(
            {f'pregunta_{pregunta.id}': '1' for pregunta in instrumento.preguntas.all()},
        )
        enviada = self.client.post(publica.url_publica, datos_completos)
        aplicacion = AplicacionInstrumento.objects.get(
            proceso=proceso,
            participante__numero_alumno='L-001',
        )
        self.assertContains(enviada, 'Gracias por responder')
        self.assertEqual(
            aplicacion.estado,
            AplicacionInstrumento.Estado.RESPONDIDA,
        )
        self.assertEqual(aplicacion.respuestas.count(), 119)

class CanalizacionTests(TestCase):

    def setUp(self):
        self.escuela = Escuela.objects.create(
            nombre='Escuela canalización',
            director='Dirección',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela,
            fecha_inicio=date.today(),
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Alumno',
            numero_alumno='C-1',
        )

    def test_voluntaria_y_emergencia_no_requieren_consejerias_y_crean_bitacora(self):
        voluntaria = Canalizacion.objects.create(
            participante=self.participante,
            tipo=Canalizacion.Tipo.VOLUNTARIA,
            motivo='Solicita atención',
        )
        self.assertEqual(
            voluntaria.estado,
            Canalizacion.Estado.PENDIENTE_ENVIO,
        )
        self.assertEqual(
            voluntaria.estado_envio,
            Canalizacion.EstadoEnvio.PENDIENTE,
        )
        self.assertTrue(
            BitacoraProceso.objects.filter(
                proceso=self.proceso,
                evento='Canalización creada',
            ).exists(),
        )
        voluntaria.estado = Canalizacion.Estado.CERRADA
        voluntaria.save()
        emergencia = Canalizacion.objects.create(
            participante=self.participante,
            tipo=Canalizacion.Tipo.EMERGENCIA,
            motivo='Riesgo inmediato',
            observaciones='Atención urgente',
            prioridad=Canalizacion.Prioridad.URGENTE,
        )
        self.assertEqual(emergencia.prioridad, Canalizacion.Prioridad.URGENTE)

    def test_solicitud_pertenece_a_una_canalizacion_y_registra_bitacora(self):
        canalizacion = Canalizacion.objects.create(
            participante=self.participante,
            tipo=Canalizacion.Tipo.VOLUNTARIA,
            motivo='Atención solicitada',
        )
        solicitud = SolicitudAtencion.objects.create(canalizacion=canalizacion)
        self.assertEqual(
            solicitud.estado,
            SolicitudAtencion.Estado.PENDIENTE_ENVIO,
        )
        self.assertEqual(canalizacion.solicitud_atencion, solicitud)
        self.assertTrue(
            BitacoraProceso.objects.filter(
                proceso=self.proceso,
                evento='Solicitud de Atención creada',
            ).exists(),
        )
        with self.assertRaises(Exception):
            SolicitudAtencion.objects.create(canalizacion=canalizacion)

    def test_ordinaria_requiere_entrevista_tres_sesiones_y_no_duplica_activas(self):
        with self.assertRaises(Exception):
            Canalizacion.objects.create(
                participante=self.participante,
                tipo=Canalizacion.Tipo.ORDINARIA,
                motivo='Seguimiento',
            )
        EntrevistaSeguimiento.objects.create(
            participante=self.participante,
            nombre_confirmado='Alumno',
            numero_alumno_confirmado='C-1',
            fecha=date.today(),
            decision=EntrevistaSeguimiento.Decision.CONSEJERIA,
        )
        for _ in range(3):
            Consejeria.objects.create(
                participante=self.participante,
                fecha=date.today(),
                observaciones='Sesión',
                estado=Consejeria.Estado.REALIZADA,
            )
        canalizacion = Canalizacion.objects.create(
            participante=self.participante,
            tipo=Canalizacion.Tipo.ORDINARIA,
            motivo='Seguimiento concluido',
        )
        self.assertEqual(
            canalizacion.estado,
            Canalizacion.Estado.PENDIENTE_ENVIO,
        )
        with self.assertRaises(Exception):
            Canalizacion.objects.create(
                participante=self.participante,
                tipo=Canalizacion.Tipo.VOLUNTARIA,
                motivo='Duplicada',
            )

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
    CONSULTORIOWEB_INTEGRATION_ENABLED=True,
    CONSULTORIOWEB_API_BASE_URL='https://consultorio.example',
    CONSULTORIOWEB_API_KEY='clave-de-prueba',
    CONSULTORIOWEB_API_TIMEOUT=17,
)
class ConsultorioWebClientTests(TestCase):

    def setUp(self):
        escuela = Escuela.objects.create(
            nombre='Escuela API',
            director='Dirección',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            fecha_inicio=date.today(),
        )
        participante = Participante.objects.create(
            proceso=proceso,
            nombre='Persona administrativa',
            numero_alumno='A-1',
            telefono='5551234567',
        )
        canalizacion = Canalizacion.objects.create(
            participante=participante,
            tipo=Canalizacion.Tipo.VOLUNTARIA,
            motivo='Solicita orientación',
            prioridad=Canalizacion.Prioridad.MEDIA,
        )
        self.solicitud = SolicitudAtencion.objects.create(canalizacion=canalizacion)

    def test_payload_es_administrativo_y_omite_opcionales_vacios(self):
        payload = consultorio_web.payload_for(self.solicitud)
        self.assertEqual(payload['source'], 'certificacion_intera')
        self.assertEqual(payload['priority'], 'normal')
        self.assertNotIn('email', payload['participant'])
        serialized = str(payload).lower()
        for forbidden in (
            'resultado',
            'puntaje',
            'entrevista',
            'consejeria',
            'diagnostico',
            'api_key',
        ):
            self.assertNotIn(forbidden, serialized)

    def test_payload_reporta_los_campos_obligatorios_faltantes(self):
        self.solicitud.canalizacion.participante.telefono = ''
        self.solicitud.canalizacion.participante.save()
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.payload_for(self.solicitud)
        self.assertEqual(captured.exception.code, 'validation_error')
        self.assertIn('teléfono de contacto', captured.exception.message)

    @override_settings(CONSULTORIOWEB_INTEGRATION_ENABLED=False)
    def test_integracion_deshabilitada(self):
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.enviar_solicitud(self.solicitud)
        self.assertEqual(captured.exception.code, 'integration_disabled')

    @override_settings(CONSULTORIOWEB_API_BASE_URL='')
    def test_url_ausente(self):
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.enviar_solicitud(self.solicitud)
        self.assertEqual(captured.exception.code, 'configuration_error')

    @override_settings(CONSULTORIOWEB_API_KEY='')
    def test_api_key_ausente(self):
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.enviar_solicitud(self.solicitud)
        self.assertEqual(captured.exception.code, 'configuration_error')

    @patch('apps.certificacion_intera.consultorio_web.request.urlopen')
    def test_headers_timeout_ids_y_post_201(self, urlopen):
        urlopen.return_value = FakeHttpResponse(201, b'{"status":"recibida","message":"Aceptada"}')
        status, body = consultorio_web.enviar_solicitud(self.solicitud)
        http_request = urlopen.call_args.args[0]
        self.assertEqual(status, 201)
        self.assertEqual(body['status'], 'recibida')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 17)
        self.assertEqual(
            http_request.get_header('Authorization'),
            'ApiKey clave-de-prueba',
        )
        self.assertEqual(http_request.get_header('X-contract-version'), '1')
        self.assertEqual(
            http_request.get_header('Idempotency-key'),
            str(self.solicitud.idempotency_key),
        )
        self.assertNotIn(
            'clave-de-prueba',
            str(consultorio_web.payload_for(self.solicitud)),
        )

    @patch('apps.certificacion_intera.consultorio_web.request.urlopen')
    def test_request_id_cambia_e_idempotency_key_permanece(self, urlopen):
        urlopen.return_value = FakeHttpResponse(200, b'{"status":"recibida"}')
        consultorio_web.enviar_solicitud(self.solicitud)
        first = urlopen.call_args.args[0]
        consultorio_web.enviar_solicitud(self.solicitud)
        second = urlopen.call_args.args[0]
        self.assertNotEqual(
            first.get_header('X-request-id'),
            second.get_header('X-request-id'),
        )
        self.assertEqual(
            first.get_header('Idempotency-key'),
            second.get_header('Idempotency-key'),
        )

    def _http_error(self, status, body=b'{"message":"Error administrativo"}'):
        return error.HTTPError(
            'https://consultorio.example',
            status,
            'error',
            {},
            BytesIO(body),
        )

    @patch('apps.certificacion_intera.consultorio_web.request.urlopen')
    def test_post_error_codes_y_respuesta_no_json(self, urlopen):
        for status in (
            400,
            401,
            403,
            409,
            422,
            429,
            500,
        ):
            urlopen.side_effect = self._http_error(status)
            self.assertEqual(
                consultorio_web.enviar_solicitud(self.solicitud)[0],
                status,
            )
        urlopen.side_effect = None
        urlopen.return_value = FakeHttpResponse(201, b'no-json')
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.enviar_solicitud(self.solicitud)
        self.assertEqual(captured.exception.code, 'contract_error')

    @patch('apps.certificacion_intera.consultorio_web.request.urlopen')
    def test_timeout_conexion_rechazada_y_get(self, urlopen):
        urlopen.side_effect = TimeoutError()
        with self.assertRaises(consultorio_web.ConsultorioWebError) as captured:
            consultorio_web.enviar_solicitud(self.solicitud)
        self.assertEqual(captured.exception.code, 'communication_error')
        urlopen.side_effect = error.URLError('rechazada')
        with self.assertRaises(consultorio_web.ConsultorioWebError):
            consultorio_web.enviar_solicitud(self.solicitud)
        urlopen.side_effect = None
        urlopen.return_value = FakeHttpResponse(200, b'{"status":"finalizada"}')
        self.assertEqual(
            consultorio_web.consultar_estado(self.solicitud),
            (200, {'status': 'finalizada'}),
        )

    @patch('apps.certificacion_intera.consultorio_web.request.urlopen')
    def test_get_404_y_500(self, urlopen):
        for status in (404, 500):
            urlopen.side_effect = self._http_error(status)
            self.assertEqual(
                consultorio_web.consultar_estado(self.solicitud)[0],
                status,
            )

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
    CONSULTORIOWEB_INTEGRATION_ENABLED=True,
    CONSULTORIOWEB_API_BASE_URL='https://consultorio.example',
    CONSULTORIOWEB_API_KEY='clave-de-prueba',
)
class SolicitudAtencionViewsTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username='intera-api', password='secreto')
        group, _ = Group.objects.get_or_create(name='Certificación')
        self.usuario.groups.add(group)
        escuela = Escuela.objects.create(
            nombre='Escuela vistas',
            director='Dirección',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='2026-2027',
            fecha_inicio=date.today(),
        )
        participante = Participante.objects.create(
            proceso=proceso,
            nombre='Participante vistas',
            numero_alumno='V-1',
            telefono='5559876543',
            correo='persona@example.com',
        )
        canalizacion = Canalizacion.objects.create(
            participante=participante,
            tipo=Canalizacion.Tipo.VOLUNTARIA,
            motivo='Orientación',
        )
        self.solicitud = SolicitudAtencion.objects.create(
            canalizacion=canalizacion,
            creada_por=self.usuario,
        )
        self.canalizacion = canalizacion

    def _url(self, name):
        return reverse(f'certificacion_intera:{name}', args=[self.canalizacion.id])

    def test_autorizado_ve_panel_y_no_autorizado_no_ejecuta_acciones(self):
        self.client.force_login(self.usuario)
        self.assertContains(
            self.client.get(self._url('canalizacion_detalle')),
            'Seguimiento en Consultorio Web',
        )
        externo = User.objects.create_user(username='sin-intera', password='secreto')
        self.client.force_login(externo)
        self.assertEqual(
            self.client.post(self._url('solicitud_enviar')).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(self._url('solicitud_actualizar_estado')).status_code,
            403,
        )

    @patch('apps.certificacion_intera.views_extra.enviar_solicitud')
    def test_get_y_post_sin_confirmacion_no_envian(self, enviar):
        self.client.force_login(self.usuario)
        self.assertEqual(
            self.client.get(self._url('solicitud_enviar')).status_code,
            405,
        )
        self.client.post(self._url('solicitud_enviar'))
        enviar.assert_not_called()
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.send_attempts, 0)

    @patch('apps.certificacion_intera.views_extra.enviar_solicitud')
    def test_post_201_y_200_son_exitosos_y_no_duplican(self, enviar):
        self.client.force_login(self.usuario)
        enviar.return_value = (201, {'status': 'recibida'})
        self.client.post(
            self._url('solicitud_enviar'),
            {'confirmar_envio': 'si'},
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(
            self.solicitud.integration_status,
            SolicitudAtencion.EstadoIntegracion.ENVIADA,
        )
        self.assertEqual(self.solicitud.send_attempts, 1)
        self.assertTrue(
            BitacoraProceso.objects.filter(evento='Envío exitoso 201').exists(),
        )
        self.client.post(
            self._url('solicitud_enviar'),
            {'confirmar_envio': 'si'},
        )
        self.assertEqual(enviar.call_count, 1)
        self.assertEqual(
            SolicitudAtencion.objects.filter(canalizacion=self.canalizacion).count(),
            1,
        )

    @patch('apps.certificacion_intera.views_extra.enviar_solicitud')
    def test_error_reintento_y_conflicto_conservan_uuid(self, enviar):
        self.client.force_login(self.usuario)
        external, key = (
            self.solicitud.external_request_id,
            self.solicitud.idempotency_key,
        )
        enviar.side_effect = consultorio_web.ConsultorioWebError(
            'communication_error',
            'Sin conexión',
        )
        self.client.post(
            self._url('solicitud_enviar'),
            {'confirmar_envio': 'si'},
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(
            self.solicitud.integration_status,
            SolicitudAtencion.EstadoIntegracion.ERROR,
        )
        enviar.side_effect = None
        enviar.return_value = (409, {'message': 'Conflicto'})
        self.client.post(
            self._url('solicitud_enviar'),
            {'confirmar_envio': 'si'},
        )
        self.solicitud.refresh_from_db()
        self.assertEqual(
            (
                self.solicitud.external_request_id,
                self.solicitud.idempotency_key,
            ),
            (external, key),
        )
        self.assertTrue(
            BitacoraProceso.objects.filter(evento='Conflicto de idempotencia').exists(),
        )

    @patch('apps.certificacion_intera.views_extra.consultar_estado')
    def test_actualizar_estado_y_sin_cambio_no_duplica_cambio(self, consultar):
        self.client.force_login(self.usuario)
        self.solicitud.integration_status = SolicitudAtencion.EstadoIntegracion.ENVIADA
        self.solicitud.remote_status = 'recibida'
        self.solicitud.save()
        consultar.return_value = (
            200,
            {
                'status': 'finalizada',
                'message': 'Atención finalizada',
                'updated_at': '2026-08-03T12:00:00-06:00',
            },
        )
        self.client.post(self._url('solicitud_actualizar_estado'))
        self.solicitud.refresh_from_db()
        self.assertEqual(self.solicitud.remote_status, 'finalizada')
        changes = BitacoraProceso.objects.filter(evento='Cambio de estado remoto').count()
        consultar.return_value = (
            200,
            {'status': 'finalizada', 'message': 'Sin cambio'},
        )
        self.client.post(self._url('solicitud_actualizar_estado'))
        self.assertEqual(
            BitacoraProceso.objects.filter(evento='Cambio de estado remoto').count(),
            changes,
        )
        self.assertTrue(
            BitacoraProceso.objects.filter(evento='Estado remoto sin cambios').exists(),
        )

    def test_csrf_es_requerido_para_envio(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(
            client.post(self._url('solicitud_enviar'), {'confirmar_envio': 'si'}).status_code,
            403,
        )

class EntrevistaUnoAUnoPermissionsTests(TestCase):

    def test_acceso_no_hereda_el_permiso_general_de_certificacion(self):
        usuario = User.objects.create_user(
            username='sin-permiso-1a1',
            password='secreto',
        )
        grupo, _ = Group.objects.get_or_create(name='CertificaciÃ³n')
        usuario.groups.add(grupo)
        escuela = Escuela.objects.create(
            nombre='Escuela 1a1',
            director='DirecciÃ³n',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='1a1',
            fecha_inicio=date.today(),
        )
        participante = Participante.objects.create(
            proceso=proceso,
            nombre='Persona Uno',
            numero_alumno='1A1',
        )
        self.client.force_login(usuario)
        respuesta = self.client.get(
            reverse(
                'certificacion_intera:entrevista_1a1_acceso',
                args=[participante.id],
            ),
        )
        self.assertEqual(respuesta.status_code, 403)

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class EntrevistaUnoAUnoCapturaTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='entrevista-1a1',
            password='secreto',
            is_superuser=True,
        )
        escuela = Escuela.objects.create(
            nombre='Escuela captura',
            director='Dirección',
            cantidad_total_alumnos=1,
            estado='Estado',
            municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='captura',
            fecha_inicio=date.today(),
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Persona Captura',
            numero_alumno='C-1',
        )
        instrumento = Instrumento.objects.get(clave=CLAVE_ENTREVISTA)
        revision = RevisionInstrumento.objects.get(
            instrumento=instrumento,
            version=instrumento.version,
        )
        self.entrevista = EntrevistaUnoAUno.objects.create(
            participante=self.participante,
            proceso=self.proceso,
            instrumento=instrumento,
            revision_plantilla=revision,
            responsable=self.usuario,
            iniciada_por=self.usuario,
        )
        self.client.force_login(self.usuario)

    def _url(self):
        return reverse(
            'certificacion_intera:entrevista_1a1',
            args=[self.participante.id],
        )

    def _datos(self, **cambios):
        datos = {'accion': 'borrador'}
        for pregunta in self.entrevista.revision_plantilla.estructura['preguntas']:
            if pregunta['tipo_respuesta'] == 'si_no':
                datos['pregunta_' + pregunta['clave']] = 'no'
            elif pregunta['clave'] == 'MOT-04':
                datos['pregunta_' + pregunta['clave']] = '5'
            elif pregunta['tipo_respuesta'] == 'texto_libre':
                datos['pregunta_' + pregunta['clave']] = 'texto abierto'
            else:
                datos['pregunta_' + pregunta['clave']] = 'texto corto'
        datos.update(
            {
                (
                    'pregunta_' + clave[len('pregunta_'):].replace('_', '-')
                    if clave.startswith('pregunta_')
                    else clave
                ): valor
                for (clave, valor) in cambios.items()
            },
        )
        return datos

    def test_widgets_abiertos_si_no_y_numero_se_renderizan_correctamente(self):
        respuesta = self.client.get(self._url())
        html = respuesta.content.decode()
        self.assertEqual(respuesta.status_code, 200)
        self.assertRegex(html, r'<textarea\b[^>]*\bid="id_pregunta_MOT-01"[^>]*>')
        self.assertRegex(html, r'<input\b(?=[^>]*\btype="radio")(?=[^>]*\bname="pregunta_MOT-02")[^>]*>')
        self.assertRegex(html, r'<input\b(?=[^>]*\btype="number")(?=[^>]*\bname="pregunta_MOT-04")(?=[^>]*\bmin="1")(?=[^>]*\bmax="10")(?=[^>]*\bstep="1")[^>]*>')
        for clave in (
            'DES-07',
            'DES-08',
            'DES-09',
            'RES-03',
            'MOD-05',
            'MOD-08',
        ):
            self.assertRegex(html, rf'<textarea\b[^>]*\bid="id_pregunta_{re.escape(clave)}"[^>]*>')

    def test_borrador_guarda_texto_abierto_y_limpia_dependiente_inactiva(self):
        self.client.post(
            self._url(),
            self._datos(
                pregunta_MOT_02='si',
                pregunta_MOT_03='Plan personal',
                pregunta_MOT_01='Respuesta libre',
            ),
        )
        mot03 = PreguntaInstrumento.objects.get(
            instrumento=self.entrevista.instrumento,
            clave='MOT-03',
        )
        self.assertEqual(
            RespuestaEntrevistaUnoAUno.objects.get(
                entrevista=self.entrevista,
                pregunta=mot03,
                revision=1,
            ).valor,
            'Plan personal',
        )
        self.client.post(self._url(), self._datos(pregunta_MOT_02='no'))
        self.assertFalse(
            RespuestaEntrevistaUnoAUno.objects.filter(
                entrevista=self.entrevista,
                pregunta=mot03,
                revision=1,
            ).exists(),
        )

    def test_finalizar_exige_solo_visibles_y_rango_entero(self):
        datos = self._datos(accion='finalizar', pregunta_MOT_04='11')
        respuesta = self.client.post(self._url(), datos)
        self.entrevista.refresh_from_db()
        self.assertEqual(
            self.entrevista.estado,
            EntrevistaUnoAUno.Estado.EN_CURSO,
        )
        self.assertContains(
            respuesta,
            'Completa las preguntas obligatorias visibles',
        )
        datos = self._datos(
            accion='finalizar',
            pregunta_MOT_02='no',
            pregunta_DES_01='no',
            pregunta_DES_04='no',
            pregunta_MOD_04='no',
            pregunta_MOD_07='no',
        )
        self.client.post(self._url(), datos)
        self.entrevista.refresh_from_db()
        self.assertEqual(
            self.entrevista.estado,
            EntrevistaUnoAUno.Estado.FINALIZADA,
        )

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class CrearProcesoConBateriaTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username='crear-proceso', password='secreto')
        self.usuario.groups.add(
            Group.objects.get_or_create(name='Certificación')[0],
        )
        self.client.force_login(self.usuario)
        self.escuela = Escuela.objects.create(
            nombre='Escuela para proceso',
            director='Dirección',
            cantidad_total_alumnos=20,
            estado='Estado',
            municipio='Municipio',
        )
        self.orientativo = crear_instrumento_bateria(
            'dass-21-adolescentes',
            'DASS-21',
            21,
            CalculadoraInstrumento.Estado.ORIENTATIVA,
        )
        self.rosenberg = crear_instrumento_bateria(
            'rse-autoestima',
            'Escala de Autoestima de Rosenberg',
            10,
            CalculadoraInstrumento.Estado.ORIENTATIVA,
        )
        crear_instrumento_bateria(
            'scid-ii-adolescentes',
            'SCID-II PQ',
            119,
            CalculadoraInstrumento.Estado.NO_DIAGNOSTICA,
        )
        self.plutchik = crear_instrumento_bateria(
            'ersp-plutchik-adolescentes',
            'Escala de Riesgo Suicida de Plutchik',
            15,
            CalculadoraInstrumento.Estado.ORIENTATIVA,
        )
        Instrumento.objects.create(
            nombre='SCID-II',
            clave='scid-ii-incompleto',
        )
        scid_sin_trazabilidad = Instrumento.objects.create(nombre='SCID-II', clave='scid-ii-antiguo')
        PreguntaInstrumento.objects.create(
            instrumento=scid_sin_trazabilidad,
            orden=1,
            texto='Registro antiguo',
        )

    def _datos(self, **cambios):
        datos = {
            'escuela': self.escuela.id,
            'nombre': 'Proceso de prueba',
            'ciclo_escolar': '2026-2027',
            'fecha_inicio': date.today().isoformat(),
            'instrumentos': [str(self.orientativo.id)],
            f'orden_{self.orientativo.id}': '1',
        }
        datos.update(cambios)
        return datos

    def test_panel_abre_formulario_directo_y_crea_proceso_con_bateria(self):
        panel = self.client.get(reverse('certificacion_intera:dashboard'))
        self.assertContains(
            panel,
            reverse('certificacion_intera:proceso_crear_general'),
        )
        pagina = self.client.get(reverse('certificacion_intera:proceso_crear_general'))
        self.assertContains(pagina, 'Batería de evaluación')
        self.assertContains(pagina, 'DASS-21')
        self.assertContains(pagina, '21 reactivos')
        self.assertContains(
            pagina,
            'Escala de Autoestima de Rosenberg',
        )
        self.assertContains(pagina, '10 reactivos')
        self.assertContains(
            pagina,
            'SCID-II PQ',
            count=1,
        )
        self.assertContains(pagina, '119 reactivos')
        self.assertContains(pagina, 'Calculadora no diagnóstica')
        self.assertContains(
            pagina,
            'Escala de Riesgo Suicida de Plutchik',
        )
        entrevista = Instrumento.objects.get(clave=CLAVE_ENTREVISTA)
        self.assertTrue(entrevista.activo)
        self.assertEqual(entrevista.preguntas.count(), 24)
        self.assertNotContains(pagina, entrevista.nombre)
        self.assertContains(pagina, 'Calculadora orientativa')
        respuesta = self.client.post(
            reverse('certificacion_intera:proceso_crear_general'),
            self._datos(),
        )
        self.assertEqual(respuesta.status_code, 302)
        proceso = ProcesoCertificacion.objects.get(nombre='Proceso de prueba')
        self.assertEqual(proceso.escuela, self.escuela)
        self.assertEqual(
            proceso.estado,
            ProcesoCertificacion.Estado.CONFIGURACION,
        )
        self.assertIsNone(proceso.fecha_cierre)
        self.assertEqual(
            list(
                proceso.configuraciones_instrumento.values_list(
                    'instrumento_id',
                    'orden',
                ),
            ),
            [(self.orientativo.id, 1)],
        )

    def test_post_manipulado_no_agrega_entrevista_a_la_bateria(self):
        entrevista = Instrumento.objects.get(clave=CLAVE_ENTREVISTA)
        respuesta = self.client.post(
            reverse('certificacion_intera:proceso_crear_general'),
            self._datos(
                instrumentos=[str(entrevista.id)],
                **{f'orden_{entrevista.id}': '1'},
            ),
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'Este instrumento no está disponible para esta batería.',
        )
        self.assertFalse(ProcesoCertificacion.objects.exists())

    def test_entrevista_preexistente_no_entra_al_flujo_publico_ni_al_expediente(self):
        proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela,
            nombre='Proceso con configuración histórica',
            ciclo_escolar='histórico',
            fecha_inicio=date.today(),
        )
        entrevista = Instrumento.objects.get(clave=CLAVE_ENTREVISTA)
        ConfiguracionInstrumento.objects.bulk_create(
            [
                ConfiguracionInstrumento(
                    proceso=proceso,
                    instrumento=self.orientativo,
                    orden=1,
                ),
                ConfiguracionInstrumento(
                    proceso=proceso,
                    instrumento=entrevista,
                    orden=2,
                ),
            ],
        )
        participante = Participante.objects.create(
            proceso=proceso,
            nombre='Participante histórico',
            numero_alumno='H-1',
        )
        AplicacionInstrumento.objects.create(
            proceso=proceso,
            participante=participante,
            instrumento=entrevista,
        )
        publica = AplicacionPublica.objects.create(proceso=proceso)

        expediente = self.client.get(
            reverse(
                'certificacion_intera:participante_detalle',
                args=[participante.id],
            ),
        )
        self.assertContains(expediente, 'Entrevista 1:1', count=1)

        cliente_publico = Client()
        respuesta = cliente_publico.post(
            publica.url_publica,
            {
                'nombre': 'Participante público',
                'numero_alumno': 'PUB-1',
                'fecha_nacimiento': '2008-01-01',
                'grupo': 'A',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        nuevo = Participante.objects.get(numero_alumno='PUB-1', proceso=proceso)
        self.assertEqual(
            list(nuevo.aplicaciones.values_list('instrumento__clave', flat=True)),
            [self.orientativo.clave],
        )
        bateria = cliente_publico.get(publica.url_publica)
        self.assertContains(bateria, self.orientativo.nombre)
        self.assertNotContains(bateria, entrevista.nombre)

    def test_instrumento_orientativo_y_orden_invalido_no_dejan_proceso_parcial(self):
        datos = self._datos(
            instrumentos=[str(self.orientativo.id), str(self.rosenberg.id)],
            **{f'orden_{self.rosenberg.id}': '1'},
        )
        respuesta = self.client.post(
            reverse('certificacion_intera:proceso_crear_general'),
            datos,
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(ProcesoCertificacion.objects.count(), 0)

    def test_instrumento_orientativo_puede_integrarse_a_la_bateria(self):
        datos = self._datos(
            instrumentos=[str(self.orientativo.id), str(self.rosenberg.id)],
            **{f'orden_{self.rosenberg.id}': '2'},
        )
        respuesta = self.client.post(
            reverse('certificacion_intera:proceso_crear_general'),
            datos,
        )

        self.assertEqual(respuesta.status_code, 302)
        proceso = ProcesoCertificacion.objects.get(nombre='Proceso de prueba')
        self.assertEqual(
            list(
                proceso.configuraciones_instrumento.values_list(
                    'instrumento_id',
                    'orden',
                ),
            ),
            [(self.orientativo.id, 1), (self.rosenberg.id, 2)],
        )

    def test_instrumento_inactivo_no_aparece_en_la_bateria(self):
        inactivo = Instrumento.objects.create(
            nombre='Instrumento inactivo',
            clave='instrumento-inactivo',
            activo=False,
        )
        pagina = self.client.get(
            reverse('certificacion_intera:proceso_crear_general'),
        )
        self.assertNotContains(pagina, inactivo.nombre)

    def test_plutchik_orientativo_puede_integrarse_a_la_bateria(self):
        datos = self._datos(
            instrumentos=[str(self.plutchik.id)],
            **{f'orden_{self.plutchik.id}': '1'},
        )
        respuesta = self.client.post(
            reverse('certificacion_intera:proceso_crear_general'),
            datos,
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            ProcesoCertificacion.objects.get().configuraciones_instrumento.get().instrumento,
            self.plutchik,
        )

@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class ListadosAdministrativosFiltrosTests(TestCase):

    def setUp(self):
        usuario = User.objects.create_user(username='filtros-listados', password='secreto')
        usuario.groups.add(Group.objects.get_or_create(name='Certificación')[0])
        self.client.force_login(usuario)
        self.escuela_a = Escuela.objects.create(
            nombre='Escuela Norte', director='Dirección', cantidad_total_alumnos=30,
            estado='México', municipio='Toluca', contacto='Contacto Norte',
        )
        self.escuela_b = Escuela.objects.create(
            nombre='Escuela Sur', director='Dirección', cantidad_total_alumnos=30,
            estado='Puebla', municipio='Puebla', contacto='Contacto Sur',
        )
        self.proceso_a = ProcesoCertificacion.objects.create(
            escuela=self.escuela_a, nombre='Proceso Norte', ciclo_escolar='2026-2027',
            fecha_inicio=date(2026, 8, 1),
        )
        self.proceso_b = ProcesoCertificacion.objects.create(
            escuela=self.escuela_b, nombre='Proceso Sur', ciclo_escolar='2026-2027',
            fecha_inicio=date(2026, 8, 1),
        )
        self.participante_a = Participante.objects.create(
            proceso=self.proceso_a, nombre='Ana Norte', numero_alumno='N-01',
        )
        self.participante_b = Participante.objects.create(
            proceso=self.proceso_b, nombre='Bruno Sur', numero_alumno='S-01',
        )
        self.instrumento = Instrumento.objects.create(
            nombre='Instrumento filtros', clave='instrumento-filtros-listados',
        )
        aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso_a,
            participante=self.participante_a,
            instrumento=self.instrumento,
            estado=AplicacionInstrumento.Estado.RESPONDIDA,
        )
        ResultadoInstrumento.objects.create(
            aplicacion=aplicacion,
            estado=ResultadoInstrumento.Estado.EVALUADO,
        )
        EntrevistaSeguimiento.objects.create(
            participante=self.participante_a,
            nombre_confirmado='Ana Norte',
            numero_alumno_confirmado='N-01',
            fecha=date(2026, 8, 20),
            decision=EntrevistaSeguimiento.Decision.CONSEJERIA,
        )
        EntrevistaSeguimiento.objects.create(
            participante=self.participante_b,
            nombre_confirmado='Bruno Sur',
            numero_alumno_confirmado='S-01',
            fecha=date(2026, 8, 21),
            decision=EntrevistaSeguimiento.Decision.FINALIZAR,
        )
        Consejeria.objects.create(
            participante=self.participante_a,
            fecha=date(2026, 8, 22),
            observaciones='Pendiente Norte',
            estado=Consejeria.Estado.PENDIENTE,
        )
        Consejeria.objects.create(
            participante=self.participante_b,
            fecha=date(2026, 8, 23),
            observaciones='Realizada Sur',
            estado=Consejeria.Estado.REALIZADA,
        )

    def test_escuelas_conserva_filtros_y_usa_barra_compartida(self):
        respuesta = self.client.get(
            reverse('certificacion_intera:escuelas'),
            {'q': 'Norte', 'estado': 'México', 'municipio': 'Toluca'},
        )
        self.assertContains(respuesta, 'Escuela Norte')
        self.assertNotContains(respuesta, 'Escuela Sur')
        self.assertContains(respuesta, 'intera-filter-grid--schools')
        self.assertContains(respuesta, 'value="México"')
        self.assertContains(respuesta, 'selected')

    def test_participantes_filtra_por_escuela_proceso_y_resultados(self):
        respuesta = self.client.get(
            reverse('certificacion_intera:participantes'),
            {'escuela': self.escuela_a.id, 'proceso': self.proceso_a.id, 'estado': 'resultados'},
        )
        self.assertContains(respuesta, 'Ana Norte')
        self.assertNotContains(respuesta, 'Bruno Sur')
        self.assertContains(respuesta, 'value="resultados" selected')
        self.assertContains(respuesta, '>Limpiar</a>')

    def test_entrevistas_filtra_por_decision_y_fecha_real(self):
        respuesta = self.client.get(
            reverse('certificacion_intera:entrevistas'),
            {'estado': EntrevistaSeguimiento.Decision.CONSEJERIA, 'fecha': '2026-08-20'},
        )
        self.assertContains(respuesta, 'Ana Norte')
        self.assertNotContains(respuesta, 'Bruno Sur')
        self.assertContains(respuesta, 'value="2026-08-20"')

    def test_seguimiento_filtra_por_estado_real(self):
        respuesta = self.client.get(
            reverse('certificacion_intera:seguimiento'),
            {'estado': Consejeria.Estado.PENDIENTE, 'proceso': self.proceso_a.id},
        )
        self.assertContains(respuesta, 'Ana Norte')
        self.assertNotContains(respuesta, 'Bruno Sur')
        self.assertContains(respuesta, 'value="pendiente" selected')


@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class AplicacionPublicaGeneralTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='publica-general',
            password='secreto',
        )
        self.usuario.groups.add(
            Group.objects.get_or_create(name='Certificación')[0],
        )
        self.client.force_login(self.usuario)
        escuela = Escuela.objects.create(
            nombre='Escuela pública general',
            director='Dirección',
            cantidad_total_alumnos=20,
            estado='Estado',
            municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='general',
            fecha_inicio=date.today(),
        )
        self.instrumento = Instrumento.objects.create(
            nombre='Instrumento general',
            clave='general-publico',
        )
        PreguntaInstrumento.objects.create(
            instrumento=self.instrumento,
            orden=1,
            texto='Pregunta pública',
            opciones=[{'valor': 'si', 'etiqueta': 'Sí'}],
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=self.instrumento,
            orden=1,
        )

    def test_generar_es_idempotente_y_la_ficha_tiene_pestanas(self):
        detalle = self.client.get(
            reverse(
                'certificacion_intera:proceso_detalle',
                args=[self.proceso.id],
            ),
            {'tab': 'bateria'},
        )
        self.assertContains(detalle, 'Aplicación pública')
        self.assertContains(detalle, 'Generar enlace')
        for tab in (
            'resumen',
            'participantes',
            'bateria',
            'entrevistas',
            'resultados',
            'seguimiento',
            'bitacora',
        ):
            self.assertContains(detalle, '?tab=' + tab)
        self.assertNotContains(detalle, 'Accesos rápidos')
        url = reverse(
            'certificacion_intera:aplicacion_publica_proceso_generar',
            args=[self.proceso.id],
        )
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(
            AplicacionPublica.objects.filter(proceso=self.proceso).count(),
            1,
        )

    def test_activar_acceso_avanza_configuracion_a_aplicacion(self):
        publica = AplicacionPublica.objects.create(
            proceso=self.proceso,
            estado=AplicacionPublica.Estado.CERRADA,
        )

        respuesta = self.client.post(
            reverse(
                'certificacion_intera:aplicacion_publica_proceso_estado',
                args=[self.proceso.id],
            ),
            {'accion': 'activar'},
        )

        self.assertEqual(respuesta.status_code, 302)
        publica.refresh_from_db()
        self.proceso.refresh_from_db()
        self.assertEqual(publica.estado, AplicacionPublica.Estado.ACTIVA)
        self.assertEqual(self.proceso.estado, ProcesoCertificacion.Estado.APLICACION)

    def test_procesos_distintos_tienen_accesos_y_qr_distintos(self):
        otra_escuela = Escuela.objects.create(
            nombre='Otra escuela',
            director='Dirección',
            cantidad_total_alumnos=10,
            estado='Estado',
            municipio='Municipio',
        )
        otro_proceso = ProcesoCertificacion.objects.create(
            escuela=otra_escuela,
            ciclo_escolar='otro',
            fecha_inicio=date.today(),
        )
        primera = AplicacionPublica.objects.create(proceso=self.proceso)
        segunda = AplicacionPublica.objects.create(proceso=otro_proceso)

        self.assertNotEqual(primera.token, segunda.token)
        self.assertNotEqual(primera.url_publica, segunda.url_publica)
        self.assertNotEqual(
            reverse(
                'certificacion_intera:aplicacion_publica_proceso_qr',
                args=[self.proceso.id],
            ),
            reverse(
                'certificacion_intera:aplicacion_publica_proceso_qr',
                args=[otro_proceso.id],
            ),
        )

    @patch('apps.certificacion_intera.views.qrcode.make')
    def test_enlace_mostrado_y_qr_reciben_exactamente_la_misma_url(self, crear_qr):
        class ImagenFalsa:
            def save(self, destino):
                destino.write(b'<svg></svg>')

        crear_qr.return_value = ImagenFalsa()
        publica = AplicacionPublica.objects.create(proceso=self.proceso)
        detalle = self.client.get(
            reverse('certificacion_intera:proceso_detalle', args=[self.proceso.id]),
            {'tab': 'bateria'},
        )
        url_absoluta = f'http://testserver{publica.url_publica}'
        self.assertContains(detalle, url_absoluta, count=2)

        respuesta_qr = self.client.get(
            reverse(
                'certificacion_intera:aplicacion_publica_proceso_qr',
                args=[self.proceso.id],
            ),
        )

        self.assertEqual(respuesta_qr.status_code, 200)
        self.assertEqual(crear_qr.call_args.args[0], url_absoluta)

    def test_qr_no_tiene_token_separado_y_cambiar_bateria_no_cambia_acceso(self):
        publica = AplicacionPublica.objects.create(proceso=self.proceso)
        token = publica.token
        campos = {campo.name for campo in AplicacionPublica._meta.get_fields()}
        self.assertNotIn('token_qr', campos)
        self.assertNotIn('qr_token', campos)

        self.proceso.configuraciones_instrumento.all().delete()
        nuevo = Instrumento.objects.create(nombre='Instrumento nuevo', clave='nuevo-qr')
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=nuevo,
            orden=1,
        )
        publica.refresh_from_db()

        self.assertEqual(publica.token, token)

    def test_proceso_sin_instrumentos_conserva_acceso_y_muestra_mensaje(self):
        self.proceso.configuraciones_instrumento.all().delete()
        generar = reverse(
            'certificacion_intera:aplicacion_publica_proceso_generar',
            args=[self.proceso.id],
        )
        self.assertEqual(self.client.post(generar).status_code, 302)
        publica = AplicacionPublica.objects.get(proceso=self.proceso)
        self.client.logout()

        respuesta = self.client.get(publica.url_publica)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            'Este proceso aún no tiene instrumentos disponibles.',
        )

    def test_participantes_del_mismo_acceso_no_mezclan_aplicaciones(self):
        publica = AplicacionPublica.objects.create(proceso=self.proceso)
        url = publica.url_publica
        primero = Client()
        segundo = Client()
        datos_base = {
            'fecha_nacimiento': '2008-01-01',
            'grupo': 'A',
        }
        primero.post(
            url,
            {**datos_base, 'nombre': 'Participante uno', 'numero_alumno': 'UNO'},
        )
        segundo.post(
            url,
            {**datos_base, 'nombre': 'Participante dos', 'numero_alumno': 'DOS'},
        )

        participantes = Participante.objects.filter(proceso=self.proceso)
        self.assertEqual(participantes.count(), 2)
        aplicaciones = AplicacionInstrumento.objects.filter(aplicacion_publica=publica)
        self.assertEqual(aplicaciones.count(), 2)
        self.assertEqual(aplicaciones.values('participante_id').distinct().count(), 2)

    def test_enlace_general_inicia_con_datos_y_reutiliza_participante(self):
        publica, _ = AplicacionPublica.objects.get_or_create(proceso=self.proceso)
        self.client.logout()
        url = reverse(
            'certificacion_intera:aplicacion_publica',
            args=[publica.token],
        )
        pagina = self.client.get(url)
        self.assertContains(pagina, 'Datos generales')
        datos = {
            'nombre': 'Persona Pública',
            'numero_alumno': 'PG-1',
            'sexo': 'femenino',
            'fecha_nacimiento': '2008-01-01',
            'grupo': 'A',
        }
        self.assertNotContains(pagina, 'Sexo')
        respuesta = self.client.post(url, datos)
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            Participante.objects.filter(
                proceso=self.proceso,
                numero_alumno='PG-1',
            ).count(),
            1,
        )
        self.assertEqual(
            Participante.objects.get(proceso=self.proceso, numero_alumno='PG-1').sexo,
            '',
        )
        self.client.post(url, datos)
        self.assertEqual(
            Participante.objects.filter(
                proceso=self.proceso,
                numero_alumno='PG-1',
            ).count(),
            1,
        )

    def test_solicita_sexo_solo_antes_del_instrumento_que_lo_requiere(self):
        self.proceso.configuraciones_instrumento.all().delete()
        instrumento = Instrumento.objects.create(nombre='ISRA', clave='isra')
        PreguntaInstrumento.objects.create(
            instrumento=instrumento,
            orden=1,
            texto='Reactivo ISRA',
            opciones=[{'valor': '1', 'etiqueta': 'Sí'}],
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=instrumento,
            orden=1,
        )
        publica, _ = AplicacionPublica.objects.get_or_create(proceso=self.proceso)
        self.client.logout()
        url = reverse(
            'certificacion_intera:aplicacion_publica',
            args=[publica.token],
        )
        datos = {
            'nombre': 'Persona ISRA',
            'numero_alumno': 'ISRA-1',
            'fecha_nacimiento': '2008-01-01',
            'grupo': 'A',
        }
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        contexto = self.client.get(url)
        self.assertContains(
            contexto,
            'Sexo (requerido para baremos del instrumento)',
        )
        self.assertContains(contexto, 'value="femenino"')
        self.assertContains(contexto, 'value="masculino"')
        self.assertNotContains(contexto, 'no_especificado')
        self.assertNotContains(contexto, 'value="otro"')
        self.assertEqual(
            self.client.post(url, {'sexo': 'femenino'}).status_code,
            302,
        )
        participante = Participante.objects.get(proceso=self.proceso, numero_alumno='ISRA-1')
        self.assertEqual(participante.sexo, 'femenino')
        siguiente = self.client.get(url)
        self.assertContains(siguiente, 'Comenzar evaluación')
        self.assertNotContains(
            siguiente,
            'Sexo (requerido para baremos del instrumento)',
        )

    @patch(
        'apps.certificacion_intera.views.campos_contexto_requeridos',
        return_value={'sexo'},
    )
    def test_reutiliza_sexo_para_varios_instrumentos_del_mismo_flujo(
        self,
        _campos_contexto,
    ):
        self.proceso.configuraciones_instrumento.all().delete()
        primero = Instrumento.objects.create(
            nombre='Instrumento uno',
            clave='contexto-uno',
        )
        segundo = Instrumento.objects.create(
            nombre='Instrumento dos',
            clave='contexto-dos',
        )
        pregunta_uno = PreguntaInstrumento.objects.create(
            instrumento=primero,
            orden=1,
            texto='Reactivo uno',
            opciones=[{'valor': '1', 'etiqueta': 'Sí'}],
        )
        PreguntaInstrumento.objects.create(
            instrumento=segundo,
            orden=1,
            texto='Reactivo dos',
            opciones=[{'valor': '1', 'etiqueta': 'Sí'}],
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=primero,
            orden=1,
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=segundo,
            orden=2,
        )
        publica, _ = AplicacionPublica.objects.get_or_create(proceso=self.proceso)
        self.client.logout()
        url = reverse(
            'certificacion_intera:aplicacion_publica',
            args=[publica.token],
        )
        self.client.post(
            url,
            {
                'nombre': 'Persona contexto',
                'numero_alumno': 'CTX-1',
                'fecha_nacimiento': '2008-01-01',
            },
        )
        self.assertContains(
            self.client.get(url),
            'Sexo (requerido para baremos del instrumento)',
        )
        self.client.post(url, {'sexo': 'masculino'})
        self.client.post(url, {'accion': 'comenzar'})
        self.client.post(
            url,
            {
                'accion': 'responder',
                f'pregunta_{pregunta_uno.id}': '1',
            },
        )
        siguiente = self.client.get(url)
        self.assertContains(siguiente, 'Instrumento dos')
        self.assertNotContains(
            siguiente,
            'Sexo (requerido para baremos del instrumento)',
        )

    def test_ficha_presenta_acciones_publicas_con_jerarquia_y_nombres(self):
        publica, _ = AplicacionPublica.objects.get_or_create(
            proceso=self.proceso,
        )
        respuesta = self.client.get(
            reverse(
                'certificacion_intera:proceso_detalle',
                args=[self.proceso.id],
            ),
            {'tab': 'bateria'},
        )

        self.assertContains(respuesta, 'Activa')
        self.assertContains(respuesta, 'Copiar enlace')
        self.assertContains(respuesta, 'Abrir aplicación')
        self.assertContains(respuesta, 'Desactivar')
        self.assertContains(respuesta, 'aplicacion-publica__acciones')
        self.assertContains(respuesta, 'intera-btn-secondary')
        self.assertContains(respuesta, 'intera-btn-caution')
        self.assertContains(respuesta, 'intera-btn-small')
        self.assertContains(respuesta, 'Vista individual')
        self.assertContains(respuesta, publica.url_publica)
        self.assertContains(respuesta, 'readonly')

        self.assertNotContains(respuesta, 'Registrar participante')
        self.assertNotContains(respuesta, 'Mostrar enlace')
        self.assertNotContains(respuesta, 'Ocultar enlace')
        self.assertNotContains(respuesta, '<br>')

    def test_ficha_muestra_url_de_solo_lectura_sin_regenerar_enlace(self):
        publica, _ = AplicacionPublica.objects.get_or_create(
            proceso=self.proceso,
        )
        token_original = publica.token

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:proceso_detalle',
                args=[self.proceso.id],
            ),
            {'tab': 'bateria'},
        )

        self.assertContains(respuesta, 'readonly')
        self.assertContains(respuesta, 'data-copy-status')
        self.assertContains(respuesta, 'Copiar enlace')
        self.assertContains(respuesta, 'Abrir aplicación')
        self.assertContains(respuesta, publica.url_publica)

        self.assertNotContains(respuesta, 'Mostrar enlace')
        self.assertNotContains(respuesta, 'Ocultar enlace')

        publica.refresh_from_db()

        self.assertEqual(
            publica.token,
            token_original,
        )

    def test_resultado_muestra_advertencia_orientativa_separada(self):
        participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Participante orientativo',
            numero_alumno='ORI-1',
        )
        aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=participante,
            instrumento=self.instrumento,
            interpretacion='Interpretación calculada.',
            revision_calculadora={
                'clave': 'regla-orientativa',
                'version_regla': '1.0',
                'estado': 'orientativa',
            },
        )

        respuesta = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id])
        )

        self.assertContains(respuesta, 'Interpretación calculada.')
        self.assertContains(
            respuesta,
            ADVERTENCIA_RESULTADO_ORIENTATIVO,
        )


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class ResultadosParticipanteTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='resultados-consolidados',
            password='secreto',
        )
        self.usuario.groups.add(
            Group.objects.get_or_create(name='Certificación')[0],
        )
        self.client.force_login(self.usuario)
        self.escuela = Escuela.objects.create(
            nombre='Escuela resultados',
            director='Dirección',
            cantidad_total_alumnos=50,
            estado='Coahuila',
            municipio='Saltillo',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela,
            nombre='Proceso resultados',
            ciclo_escolar='RESULTADOS-2026',
            fecha_inicio=date(2026, 1, 1),
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Alumno consolidado',
            numero_alumno='CONSOLIDADO-1',
            fecha_nacimiento=date(2010, 1, 1),
        )

    def _instrumento(self, clave, nombre, orden):
        instrumento = Instrumento.objects.create(
            clave=clave,
            nombre=nombre,
            version='1.0',
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=instrumento,
            orden=orden,
        )
        return instrumento

    def _aplicacion(
        self,
        instrumento,
        participante=None,
        estado=AplicacionInstrumento.Estado.RESPONDIDA,
        puntaje=10,
        interpretacion='Interpretación persistida',
        detalle=None,
    ):
        return AplicacionInstrumento.objects.create(
            proceso=(participante or self.participante).proceso,
            participante=participante or self.participante,
            instrumento=instrumento,
            estado=estado,
            puntaje_total=puntaje,
            interpretacion=interpretacion,
            resultado_detalle=detalle or {'Resumen general': 'Dato persistido'},
        )

    def test_un_instrumento_respondido_abre_y_conserva_resultado_individual(self):
        instrumento = self._instrumento('resultado-unico', 'Instrumento único', 1)
        aplicacion = self._aplicacion(instrumento, puntaje=18)

        consolidado = self.client.get(
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )
        individual = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )

        self.assertEqual(consolidado.status_code, 200)
        self.assertContains(consolidado, 'Instrumento único')
        self.assertContains(consolidado, '18.00')
        self.assertContains(consolidado, 'Interpretación persistida')
        self.assertContains(consolidado, '1/1')
        self.assertEqual(individual.status_code, 200)
        self.assertContains(individual, 'Instrumento único')
        self.assertContains(individual, 'Respuestas registradas')

    def test_varios_resultados_respetan_orden_y_no_mezclan_participantes_o_procesos(self):
        segundo = self._instrumento('resultado-segundo', 'Segundo en batería', 2)
        primero = self._instrumento('resultado-primero', 'Primero en batería', 1)
        self._aplicacion(segundo, interpretacion='Resultado segundo')
        self._aplicacion(primero, interpretacion='Resultado primero')

        otro = Participante.objects.create(
            proceso=self.proceso,
            nombre='Otro alumno',
            numero_alumno='OTRO-1',
        )
        self._aplicacion(
            primero,
            participante=otro,
            interpretacion='NO MEZCLAR OTRO PARTICIPANTE',
        )
        otra_escuela = Escuela.objects.create(
            nombre='Otra escuela',
            director='Dirección',
            cantidad_total_alumnos=10,
            estado='Coahuila',
            municipio='Torreón',
        )
        otro_proceso = ProcesoCertificacion.objects.create(
            escuela=otra_escuela,
            nombre='Otro proceso',
            ciclo_escolar='OTRO-2026',
            fecha_inicio=date(2026, 1, 1),
        )
        participante_otro_proceso = Participante.objects.create(
            proceso=otro_proceso,
            nombre='Alumno otro proceso',
            numero_alumno='OTRO-PROCESO-1',
        )
        instrumento_otro_proceso = Instrumento.objects.create(
            clave='solo-otro-proceso',
            nombre='NO MEZCLAR OTRO PROCESO',
        )
        self._aplicacion(
            instrumento_otro_proceso,
            participante=participante_otro_proceso,
            interpretacion='NO MEZCLAR RESULTADO OTRO PROCESO',
        )

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )
        contenido = respuesta.content.decode()

        self.assertLess(
            contenido.index('Primero en batería'),
            contenido.index('Segundo en batería'),
        )
        self.assertNotContains(respuesta, 'NO MEZCLAR OTRO PARTICIPANTE')
        self.assertNotContains(respuesta, 'NO MEZCLAR OTRO PROCESO')
        self.assertNotContains(respuesta, 'NO MEZCLAR RESULTADO OTRO PROCESO')

    def test_pendiente_aparece_sin_inventar_resultado(self):
        instrumento = self._instrumento('resultado-pendiente', 'Instrumento pendiente', 1)
        self._aplicacion(
            instrumento,
            estado=AplicacionInstrumento.Estado.PENDIENTE,
            puntaje=None,
            interpretacion='',
            detalle={},
        )

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )

        self.assertContains(respuesta, 'Instrumento pendiente')
        self.assertContains(respuesta, 'Pendiente')
        self.assertContains(respuesta, 'Este instrumento está pendiente de respuesta.')
        self.assertNotContains(respuesta, '<b>Puntaje:</b>', html=True)

    def test_respondido_sin_calculo_conserva_mensaje_profesional(self):
        instrumento = self._instrumento('sin-calculadora', 'Sin cálculo automático', 1)
        aplicacion = self._aplicacion(
            instrumento,
            interpretacion='',
            puntaje=None,
            detalle={},
        )

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )

        self.assertContains(
            respuesta,
            'Este instrumento aún no cuenta con una calculadora automática',
        )
        self.assertContains(
            respuesta,
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )

    def test_plutchik_conserva_advertencia_prioritaria(self):
        instrumento = self._instrumento(
            'ersp-plutchik-adolescentes',
            'Escala de Plutchik',
            1,
        )
        self._aplicacion(
            instrumento,
            puntaje=1,
            detalle={
                'puntaje_total': 1,
                'respuestas_afirmativas': 1,
                'reactivos_criticos_afirmativos': [13],
            },
        )

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )

        self.assertContains(respuesta, 'ALERTA DE ATENCIÓN EL MISMO DÍA')
        self.assertContains(respuesta, 'Reactivos críticos afirmativos')

    def test_expediente_enlaza_los_resultados_del_participante_correcto(self):
        instrumento = self._instrumento('resultado-enlace', 'Instrumento enlazado', 1)
        self._aplicacion(instrumento)

        respuesta = self.client.get(
            reverse(
                'certificacion_intera:participante_detalle',
                args=[self.participante.id],
            ),
        )

        self.assertContains(respuesta, 'Ver todos los resultados →')
        self.assertContains(
            respuesta,
            reverse(
                'certificacion_intera:resultados_participante',
                args=[self.participante.id],
            ),
        )
        self.assertContains(respuesta, 'intera-application-result-row')
        self.assertContains(respuesta, 'intera-back-link')
        self.assertContains(respuesta, 'intera-text-link')
        self.assertContains(respuesta, 'intera-small-action', count=2)
        self.assertContains(
            respuesta,
            reverse(
                'certificacion_intera:consejeria_crear',
                args=[self.participante.id],
            ),
        )
        self.assertContains(
            respuesta,
            reverse(
                'certificacion_intera:canalizacion_crear',
                args=[self.participante.id],
            ),
        )


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    },
)
class CierreProcesoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='cierre-proceso',
            password='secreto',
        )
        self.usuario.groups.add(
            Group.objects.get_or_create(name='Certificación')[0],
        )
        self.client.force_login(self.usuario)
        escuela = Escuela.objects.create(
            nombre='Escuela cierre',
            director='Dirección',
            cantidad_total_alumnos=10,
            estado='Estado',
            municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='cierre',
            fecha_inicio=date.today(),
        )
        self.instrumento = Instrumento.objects.create(
            nombre='Instrumento cierre',
            clave='instrumento-cierre',
        )
        self.pregunta = PreguntaInstrumento.objects.create(
            instrumento=self.instrumento,
            orden=1,
            texto='Pregunta cierre',
            opciones=[{'valor': 'si', 'etiqueta': 'Sí'}],
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=self.instrumento,
            orden=1,
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Participante histórico',
            numero_alumno='CIERRE-1',
        )
        self.aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=self.participante,
            instrumento=self.instrumento,
            estado=AplicacionInstrumento.Estado.RESPONDIDA,
        )
        RespuestaInstrumento.objects.create(
            aplicacion=self.aplicacion,
            pregunta=self.pregunta,
            valor='si',
        )
        ResultadoInstrumento.objects.create(
            aplicacion=self.aplicacion,
            estado=ResultadoInstrumento.Estado.EVALUADO,
        )
        self.publica = AplicacionPublica.objects.create(proceso=self.proceso)
        self.url_detalle = reverse(
            'certificacion_intera:proceso_detalle',
            args=[self.proceso.id],
        )
        self.url_cierre = reverse(
            'certificacion_intera:proceso_cerrar',
            args=[self.proceso.id],
        )

    def test_abierto_muestra_accion_y_get_solo_confirma(self):
        detalle = self.client.get(self.url_detalle)
        self.assertContains(detalle, 'Cerrar proceso')

        confirmacion = self.client.get(self.url_cierre)
        self.proceso.refresh_from_db()
        self.assertEqual(confirmacion.status_code, 200)
        self.assertContains(confirmacion, 'Ya no se recibirán nuevos participantes')
        self.assertContains(confirmacion, 'csrfmiddlewaretoken')
        self.assertNotEqual(self.proceso.estado, ProcesoCertificacion.Estado.CERRADO)

    def test_cierre_requiere_csrf(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)

        respuesta = cliente.post(self.url_cierre)

        self.assertEqual(respuesta.status_code, 403)
        self.proceso.refresh_from_db()
        self.assertNotEqual(self.proceso.estado, ProcesoCertificacion.Estado.CERRADO)

    def test_cierre_registra_bitacora_conserva_historial_y_oculta_accion(self):
        totales = {
            'participantes': self.proceso.participantes.count(),
            'aplicaciones': self.proceso.aplicaciones.count(),
            'respuestas': RespuestaInstrumento.objects.filter(
                aplicacion__proceso=self.proceso,
            ).count(),
            'resultados': ResultadoInstrumento.objects.filter(
                aplicacion__proceso=self.proceso,
            ).count(),
        }

        respuesta = self.client.post(self.url_cierre)
        self.proceso.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.proceso.estado, ProcesoCertificacion.Estado.CERRADO)
        self.assertEqual(self.proceso.fecha_cierre, date.today())
        evento = BitacoraProceso.objects.get(
            proceso=self.proceso,
            evento='Cierre de proceso',
        )
        self.assertEqual(evento.usuario, self.usuario)
        self.assertIsNotNone(evento.creado_en)
        self.assertEqual(self.proceso.participantes.count(), totales['participantes'])
        self.assertEqual(self.proceso.aplicaciones.count(), totales['aplicaciones'])
        self.assertEqual(
            RespuestaInstrumento.objects.filter(aplicacion__proceso=self.proceso).count(),
            totales['respuestas'],
        )
        self.assertEqual(
            ResultadoInstrumento.objects.filter(aplicacion__proceso=self.proceso).count(),
            totales['resultados'],
        )
        detalle = self.client.get(self.url_detalle)
        self.assertContains(detalle, 'Finalizado')
        self.assertNotContains(detalle, 'Cerrar proceso')
        resultado = self.client.get(
            reverse('certificacion_intera:resultado', args=[self.aplicacion.id]),
        )
        self.assertEqual(resultado.status_code, 200)

    def test_cerrado_bloquea_altas_y_respuestas_pero_conserva_url_y_qr(self):
        pendiente = AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=self.participante,
            instrumento=self.instrumento,
        )
        self.client.post(self.url_cierre)
        participantes_antes = self.proceso.participantes.count()
        respuestas_antes = RespuestaInstrumento.objects.count()

        publico = Client()
        general = publico.post(
            self.publica.url_publica,
            {
                'nombre': 'Participante nuevo',
                'numero_alumno': 'NUEVO',
                'fecha_nacimiento': '2008-01-01',
            },
        )
        individual = publico.post(
            reverse(
                'certificacion_intera:aplicacion_individual',
                args=[pendiente.token],
            ),
            {f'pregunta_{self.pregunta.id}': 'si'},
        )

        mensaje = 'Este proceso de certificación ha finalizado y ya no recibe respuestas.'
        self.assertEqual(general.status_code, 200)
        self.assertContains(general, mensaje)
        self.assertEqual(individual.status_code, 200)
        self.assertContains(individual, mensaje)
        self.assertEqual(self.proceso.participantes.count(), participantes_antes)
        self.assertEqual(RespuestaInstrumento.objects.count(), respuestas_antes)
        qr = self.client.get(
            reverse(
                'certificacion_intera:aplicacion_publica_proceso_qr',
                args=[self.proceso.id],
            ),
        )
        self.assertEqual(qr.status_code, 200)
        self.publica.refresh_from_db()
        self.assertIsNotNone(self.publica.token)


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class EliminacionSeguraTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username='elimina-intera', password='secreto')
        self.usuario.groups.add(Group.objects.get_or_create(name='Certificación')[0])
        self.client.force_login(self.usuario)
        self.escuela = Escuela.objects.create(
            nombre='Escuela con proceso',
            director='Dirección',
            cantidad_total_alumnos=20,
            estado='Coahuila',
            municipio='Saltillo',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela,
            nombre='Proceso eliminable',
            ciclo_escolar='2026-2027',
            fecha_inicio=date.today(),
        )
        self.instrumento = Instrumento.objects.create(
            nombre='Instrumento compartido',
            clave='instrumento-compartido-eliminacion',
        )
        self.pregunta = PreguntaInstrumento.objects.create(
            instrumento=self.instrumento,
            orden=1,
            texto='Pregunta que debe conservarse',
        )
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=self.instrumento,
            orden=1,
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Participante dependiente',
            numero_alumno='E-1',
        )
        self.aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=self.participante,
            instrumento=self.instrumento,
        )
        RespuestaInstrumento.objects.create(
            aplicacion=self.aplicacion,
            pregunta=self.pregunta,
            valor='respuesta',
        )

    def test_proceso_se_elimina_por_post_y_conserva_portafolio(self):
        url = reverse('certificacion_intera:proceso_eliminar', args=[self.proceso.id])
        respuesta = self.client.post(url)

        self.assertRedirects(respuesta, reverse('certificacion_intera:procesos'))
        self.assertFalse(ProcesoCertificacion.objects.filter(id=self.proceso.id).exists())
        self.assertFalse(Participante.objects.filter(id=self.participante.id).exists())
        self.assertTrue(Instrumento.objects.filter(id=self.instrumento.id).exists())
        self.assertTrue(PreguntaInstrumento.objects.filter(id=self.pregunta.id).exists())

    def test_get_solo_muestra_confirmacion_con_csrf(self):
        url = reverse('certificacion_intera:proceso_eliminar', args=[self.proceso.id])
        respuesta = self.client.get(url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Eliminar proceso')
        self.assertContains(respuesta, 'csrfmiddlewaretoken')
        self.assertTrue(ProcesoCertificacion.objects.filter(id=self.proceso.id).exists())

    def test_escuela_sin_procesos_puede_eliminarse(self):
        escuela = Escuela.objects.create(
            nombre='Escuela vacía', director='Dirección', cantidad_total_alumnos=1,
            estado='Coahuila', municipio='Saltillo',
        )
        respuesta = self.client.post(
            reverse('certificacion_intera:escuela_eliminar', args=[escuela.id]),
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Escuela.objects.filter(id=escuela.id).exists())

    def test_escuela_con_procesos_se_bloquea_sin_cascada(self):
        url = reverse('certificacion_intera:escuela_eliminar', args=[self.escuela.id])
        confirmacion = self.client.get(url)
        respuesta = self.client.post(url, follow=True)

        self.assertContains(confirmacion, 'no puede eliminarse')
        self.assertNotContains(confirmacion, 'intera-btn intera-btn-danger')
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'tiene procesos de certificación asociados')
        self.assertTrue(Escuela.objects.filter(id=self.escuela.id).exists())
        self.assertTrue(ProcesoCertificacion.objects.filter(id=self.proceso.id).exists())

    def test_usuario_sin_permiso_no_puede_eliminar(self):
        usuario = User.objects.create_user(username='sin-permiso', password='secreto')
        cliente = Client()
        cliente.force_login(usuario)

        respuesta = cliente.post(
            reverse('certificacion_intera:proceso_eliminar', args=[self.proceso.id]),
        )

        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(ProcesoCertificacion.objects.filter(id=self.proceso.id).exists())

    def test_relacion_protegida_muestra_error_amigable(self):
        url = reverse('certificacion_intera:proceso_eliminar', args=[self.proceso.id])
        with patch.object(
            ProcesoCertificacion,
            'delete',
            side_effect=ProtectedError('protegido', []),
        ):
            respuesta = self.client.post(url, follow=True)

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'registros protegidos')
        self.assertTrue(ProcesoCertificacion.objects.filter(id=self.proceso.id).exists())


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class CalculoDASSAdolescenteInteraTests(TestCase):

    def setUp(self):
        self.usuario = User.objects.create_user(username='resultado-dass', password='secreto')
        self.usuario.groups.add(Group.objects.get_or_create(name='Certificación')[0])
        self.client.force_login(self.usuario)
        escuela = Escuela.objects.create(
            nombre='Escuela DASS', director='Dirección', cantidad_total_alumnos=20,
            estado='Coahuila', municipio='Saltillo',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=escuela,
            ciclo_escolar='DASS-2026',
            fecha_inicio=date(2024, 1, 1),
        )
        self.instrumento = Instrumento.objects.create(
            nombre='DASS-21 adolescentes',
            clave='dass-21-adolescentes',
            version='1.0',
        )
        self.preguntas = [
            PreguntaInstrumento.objects.create(
                instrumento=self.instrumento,
                orden=orden,
                texto=f'Reactivo {orden}',
                opciones=[{'valor': '1', 'etiqueta': 'A veces'}],
            )
            for orden in range(1, 22)
        ]
        CalculadoraInstrumento.objects.create(
            instrumento=self.instrumento,
            clave='calc-dass-21-adolescentes',
            version_regla='1.0',
            estado=CalculadoraInstrumento.Estado.ACTIVA,
            definicion={},
            huella_contenido='dass-intera-activa',
        )

    def _aplicacion(self, fecha_nacimiento):
        participante = Participante.objects.create(
            proceso=self.proceso,
            nombre='Participante adolescente',
            numero_alumno=f'DASS-{Participante.objects.count() + 1}',
            fecha_nacimiento=fecha_nacimiento,
        )
        return AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=participante,
            instrumento=self.instrumento,
        )

    def _responder(self, aplicacion):
        return Client().post(
            reverse('certificacion_intera:aplicacion_individual', args=[aplicacion.token]),
            {f'pregunta_{pregunta.id}': '1' for pregunta in self.preguntas},
        )

    def _crear_y_responder_instrumento(self, clave, reactivos, opciones, estado):
        instrumento = Instrumento.objects.create(
            nombre=clave,
            clave=clave,
            version='1.0',
        )
        preguntas = [
            PreguntaInstrumento.objects.create(
                instrumento=instrumento,
                orden=orden,
                texto=f'{clave} reactivo {orden}',
                opciones=opciones,
            )
            for orden in range(1, reactivos + 1)
        ]
        CalculadoraInstrumento.objects.create(
            instrumento=instrumento,
            clave=f'calc-{clave}',
            version_regla='1.0',
            estado=estado,
            definicion={},
            huella_contenido=f'huella-{clave}',
        )
        participante = Participante.objects.create(
            proceso=self.proceso,
            nombre=f'Participante {clave}',
            numero_alumno=f'{clave}-{Participante.objects.count() + 1}',
            fecha_nacimiento=date(2010, 1, 1),
        )
        aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso,
            participante=participante,
            instrumento=instrumento,
        )
        respuesta = Client().post(
            reverse('certificacion_intera:aplicacion_individual', args=[aplicacion.token]),
            {f'pregunta_{pregunta.id}': '1' for pregunta in preguntas},
        )
        aplicacion.refresh_from_db()
        return respuesta, aplicacion

    def test_dass_publico_genera_resultado_y_lo_deja_evaluado(self):
        aplicacion = self._aplicacion(date(2010, 1, 1))

        respuesta = self._responder(aplicacion)
        aplicacion.refresh_from_db()
        resultado = ResultadoInstrumento.objects.get(aplicacion=aplicacion)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(aplicacion.respuestas.count(), 21)
        self.assertIsNotNone(aplicacion.respondido_en)
        self.assertIsNotNone(aplicacion.puntaje_total)
        self.assertTrue(aplicacion.interpretacion)
        self.assertIn('Depresión', aplicacion.resultado_detalle)
        self.assertIn('Ansiedad', aplicacion.resultado_detalle)
        self.assertIn('Estrés', aplicacion.resultado_detalle)
        self.assertEqual(resultado.estado, ResultadoInstrumento.Estado.EVALUADO)
        pagina = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(pagina, 'Depresión')
        self.assertContains(pagina, 'Ansiedad')
        self.assertContains(pagina, 'Estrés')
        self.assertContains(pagina, 'Puntaje multiplicado: 14')

    def test_bateria_general_del_qr_califica_dass_y_guarda_valores_numericos(self):
        ConfiguracionInstrumento.objects.create(
            proceso=self.proceso,
            instrumento=self.instrumento,
            orden=1,
        )
        publica = AplicacionPublica.objects.create(proceso=self.proceso)
        cliente = Client()
        alta = cliente.post(
            publica.url_publica,
            {
                'nombre': 'Participante QR',
                'numero_alumno': 'DASS-QR-1',
                'fecha_nacimiento': '2010-01-01',
            },
        )
        self.assertEqual(alta.status_code, 302)
        aplicacion = AplicacionInstrumento.objects.get(
            participante__numero_alumno='DASS-QR-1',
            instrumento=self.instrumento,
        )
        cliente.post(publica.url_publica, {'accion': 'comenzar'})

        respuesta = cliente.post(
            publica.url_publica,
            {
                'accion': 'responder',
                **{f'pregunta_{pregunta.id}': '1' for pregunta in self.preguntas},
            },
        )
        aplicacion.refresh_from_db()

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(aplicacion.respuestas.count(), 21)
        self.assertEqual(
            aplicacion.respuestas.exclude(valor_numerico=None).count(),
            21,
        )
        self.assertIn('Depresión', aplicacion.resultado_detalle)
        self.assertIn('Ansiedad', aplicacion.resultado_detalle)
        self.assertIn('Estrés', aplicacion.resultado_detalle)
        self.assertEqual(
            ResultadoInstrumento.objects.get(aplicacion=aplicacion).estado,
            ResultadoInstrumento.Estado.EVALUADO,
        )
        pagina = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(pagina, 'Depresión')
        self.assertContains(pagina, 'Ansiedad')
        self.assertContains(pagina, 'Estrés')

    def test_revision_calculadora_persistida_no_cambia_si_cambia_la_calculadora(self):
        aplicacion = self._aplicacion(date(2010, 1, 1))
        self._responder(aplicacion)
        aplicacion.refresh_from_db()
        snapshot_original = dict(aplicacion.revision_calculadora)

        calculadora = self.instrumento.calculadoras.get()
        calculadora.estado = CalculadoraInstrumento.Estado.BLOQUEADA
        calculadora.clave = 'calculadora-modificada-despues'
        calculadora.save(update_fields=['estado', 'clave'])
        aplicacion.refresh_from_db()

        self.assertEqual(aplicacion.revision_calculadora, snapshot_original)
        self.assertEqual(
            aplicacion.revision_calculadora['estado'],
            CalculadoraInstrumento.Estado.ACTIVA,
        )
        self.assertNotEqual(
            aplicacion.revision_calculadora['clave'],
            calculadora.clave,
        )

    def test_rosenberg_recibe_contexto_completo_y_persiste_resultado(self):
        respuesta, aplicacion = self._crear_y_responder_instrumento(
            'rse-autoestima',
            10,
            [{'valor': valor, 'etiqueta': str(valor)} for valor in range(1, 5)],
            CalculadoraInstrumento.Estado.ACTIVA,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('reactivos_directos', aplicacion.resultado_detalle)
        self.assertIn('reactivos_inversos', aplicacion.resultado_detalle)
        self.assertEqual(
            aplicacion.resultado_detalle['clasificacion_orientativa'],
            'Sin rango definido',
        )
        self.assertEqual(
            aplicacion.resultado_detalle['observacion_orientativa'],
            'El documento no especifica este puntaje',
        )
        self.assertIsNotNone(aplicacion.puntaje_total)
        self.assertTrue(aplicacion.interpretacion)
        self.assertEqual(
            ResultadoInstrumento.objects.get(aplicacion=aplicacion).estado,
            ResultadoInstrumento.Estado.EVALUADO,
        )
        pagina = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(pagina, 'Reactivos directos')
        self.assertContains(pagina, 'Reactivos inversos')
        self.assertContains(pagina, 'Clasificación orientativa')
        self.assertContains(pagina, 'Sin rango definido')
        self.assertContains(pagina, 'El documento no especifica este puntaje')

    def test_scid_adolescente_recibe_contexto_completo_y_persiste_resultado(self):
        respuesta, aplicacion = self._crear_y_responder_instrumento(
            'scid-ii-adolescentes',
            119,
            [{'valor': 0, 'etiqueta': 'No'}, {'valor': 1, 'etiqueta': 'Sí'}],
            CalculadoraInstrumento.Estado.NO_DIAGNOSTICA,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('bloques', aplicacion.resultado_detalle)
        self.assertTrue(aplicacion.resultado_detalle['revision_manual_requerida'])
        self.assertIsNotNone(aplicacion.puntaje_total)
        self.assertTrue(aplicacion.interpretacion)
        self.assertEqual(
            ResultadoInstrumento.objects.get(aplicacion=aplicacion).estado,
            ResultadoInstrumento.Estado.EVALUADO,
        )
        pagina = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(pagina, 'Edad calculada')
        self.assertContains(pagina, 'Conductas problemáticas')

    def test_plutchik_recibe_contexto_completo_y_persiste_resultado(self):
        respuesta, aplicacion = self._crear_y_responder_instrumento(
            'ersp-plutchik-adolescentes',
            15,
            [{'valor': 0, 'etiqueta': 'No'}, {'valor': 1, 'etiqueta': 'Sí'}],
            CalculadoraInstrumento.Estado.ACTIVA,
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn('respuestas_afirmativas', aplicacion.resultado_detalle)
        self.assertIn('reactivos_criticos_afirmativos', aplicacion.resultado_detalle)
        self.assertIsNotNone(aplicacion.puntaje_total)
        self.assertTrue(aplicacion.interpretacion)
        self.assertEqual(
            ResultadoInstrumento.objects.get(aplicacion=aplicacion).estado,
            ResultadoInstrumento.Estado.EVALUADO,
        )
        pagina = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(pagina, 'Reactivos críticos afirmativos')
        self.assertContains(pagina, 'Revisión prioritaria')
        self.assertContains(pagina, 'Interpretación orientativa')
        self.assertContains(pagina, 'Acción requerida')
        self.assertContains(pagina, 'ATENCIÓN EL MISMO DÍA')
        self.assertContains(pagina, 'canalización el mismo día')

    def test_sin_fecha_aplicacion_la_validacion_impide_el_calculo(self):
        respuestas = [
            RespuestaInstrumento(
                pregunta=pregunta,
                valor='A veces',
                valor_numerico=1,
            )
            for pregunta in self.preguntas
        ]
        contexto = {'fecha_nacimiento': date(2010, 1, 1)}

        validacion = validar_variante_por_edad(self.instrumento, contexto)

        self.assertEqual(validacion['motivo'], 'fecha_aplicacion_requerida')
        self.assertIsNone(calcular_resultado(self.instrumento, respuestas, contexto))

    def test_edad_usa_fecha_historica_de_respuesta_y_no_fecha_actual(self):
        aplicacion = self._aplicacion(date(2006, 6, 2))
        fecha_historica = datetime(2024, 6, 2, 2, 0, tzinfo=datetime_timezone.utc)

        with patch('apps.certificacion_intera.views.timezone.now', return_value=fecha_historica):
            self._responder(aplicacion)
        aplicacion.refresh_from_db()

        validacion = aplicacion.resultado_detalle[
            'trazabilidad_calculadora'
        ]['validacion_edad']
        self.assertEqual(aplicacion.respondido_en.date(), date(2024, 6, 2))
        self.assertEqual(validacion['fecha_aplicacion'], '2024-06-01')
        self.assertEqual(validacion['edad_cumplida'], 17)
        self.assertEqual(validacion['motivo'], 'variante_validada')
        self.assertEqual(
            ResultadoInstrumento.objects.get(aplicacion=aplicacion).estado,
            ResultadoInstrumento.Estado.EVALUADO,
        )

    def test_mensaje_no_afirma_ausencia_si_existe_calculadora(self):
        aplicacion = self._aplicacion(None)
        aplicacion.estado = AplicacionInstrumento.Estado.RESPONDIDA
        aplicacion.respondido_en = datetime(2024, 6, 1, tzinfo=datetime_timezone.utc)
        aplicacion.save(update_fields=['estado', 'respondido_en'])

        respuesta = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )

        self.assertContains(respuesta, 'falta la fecha de nacimiento')
        self.assertNotContains(respuesta, 'no cuenta con una calculadora automática')

    def test_mensajes_distinguen_calculadora_no_ejecutable_y_edad_no_aplicable(self):
        aplicacion = self._aplicacion(date(2010, 1, 1))
        aplicacion.estado = AplicacionInstrumento.Estado.RESPONDIDA
        aplicacion.respondido_en = datetime(2024, 6, 1, tzinfo=datetime_timezone.utc)
        aplicacion.save(update_fields=['estado', 'respondido_en'])
        calculadora = self.instrumento.calculadoras.get()
        calculadora.estado = CalculadoraInstrumento.Estado.BLOQUEADA
        calculadora.save(update_fields=['estado'])

        no_ejecutable = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(no_ejecutable, 'no está habilitada para ejecución automática')

        calculadora.estado = CalculadoraInstrumento.Estado.ACTIVA
        calculadora.save(update_fields=['estado'])
        aplicacion.participante.fecha_nacimiento = date(2000, 1, 1)
        aplicacion.participante.save(update_fields=['fecha_nacimiento'])
        edad_no_aplicable = self.client.get(
            reverse('certificacion_intera:resultado', args=[aplicacion.id]),
        )
        self.assertContains(edad_no_aplicable, 'edad no corresponde a esta variante')


class ContratosHistoricosInteraTests(TestCase):
    def setUp(self):
        self.escuela = Escuela.objects.create(
            nombre='Escuela contratos', director='Direccion',
            cantidad_total_alumnos=1, estado='Estado', municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela, ciclo_escolar='contratos', fecha_inicio=date.today(),
        )
        self.participante = Participante.objects.create(
            proceso=self.proceso, nombre='Persona historica', numero_alumno='CH-1',
        )
        self.instrumento = Instrumento.objects.create(
            nombre='Instrumento historico', clave='instrumento-historico',
            version='1.0',
        )
        self.pregunta = PreguntaInstrumento.objects.create(
            instrumento=self.instrumento, orden=1, clave='H-1', texto='Pregunta historica',
        )
        self.revision = RevisionInstrumento.objects.create(
            instrumento=self.instrumento, version='1.0',
            estructura={'preguntas': [{'id': self.pregunta.id, 'clave': 'H-1'}]},
        )

    def test_eliminar_pregunta_elimina_en_cascada_respuesta_instrumento(self):
        aplicacion = AplicacionInstrumento.objects.create(
            proceso=self.proceso, participante=self.participante,
            instrumento=self.instrumento,
        )
        respuesta = RespuestaInstrumento.objects.create(
            aplicacion=aplicacion, pregunta=self.pregunta, valor='respuesta historica',
        )

        self.pregunta.delete()

        self.assertFalse(PreguntaInstrumento.objects.filter(pk=self.pregunta.pk).exists())
        self.assertFalse(RespuestaInstrumento.objects.filter(pk=respuesta.pk).exists())

    def test_entrevista_y_respuesta_protegen_revision_instrumento_y_pregunta(self):
        usuario = User.objects.create_user(username='responsable-historico')
        entrevista = EntrevistaUnoAUno.objects.create(
            participante=self.participante, proceso=self.proceso,
            instrumento=self.instrumento, revision_plantilla=self.revision,
            responsable=usuario, iniciada_por=usuario,
        )
        respuesta = RespuestaEntrevistaUnoAUno.objects.create(
            entrevista=entrevista, pregunta=self.pregunta, revision=1,
            valor='respuesta protegida',
        )

        with self.assertRaises(ProtectedError):
            self.revision.delete()
        with self.assertRaises(ProtectedError):
            self.pregunta.delete()
        with self.assertRaises(ProtectedError):
            self.instrumento.delete()

        self.assertTrue(EntrevistaUnoAUno.objects.filter(pk=entrevista.pk).exists())
        self.assertTrue(RespuestaEntrevistaUnoAUno.objects.filter(pk=respuesta.pk).exists())


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.InMemoryStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
)
class DocumentosProcesoInteraTests(TestCase):
    def setUp(self):
        self.grupo = Group.objects.get(name='Certificación')
        self.usuario = User.objects.create_user(username='documentos-intera', password='x')
        self.usuario.groups.add(self.grupo)
        self.client.force_login(self.usuario)
        self.escuela = Escuela.objects.create(
            nombre='Escuela documental', director='Dirección',
            cantidad_total_alumnos=10, estado='Estado', municipio='Municipio',
        )
        self.proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela, ciclo_escolar='2026-2027',
            nombre='Proceso documental', fecha_inicio=date.today(),
        )
        self.otro_proceso = ProcesoCertificacion.objects.create(
            escuela=self.escuela, ciclo_escolar='2027-2028',
            nombre='Otro proceso', fecha_inicio=date.today(),
        )

    def documento(self, nombre, *, ambito=Documento.Ambito.ESPECIFICO, modulo=None,
                  proceso=None, nivel_modulo=False):
        documento = crear_documento_con_version(
            nombre=nombre,
            archivo=SimpleUploadedFile(f'{nombre}.txt', nombre.encode()),
            ambito=ambito,
        )
        if modulo:
            RelacionDocumento.objects.create(
                documento=documento,
                modulo=modulo,
                tipo_proceso='' if nivel_modulo else 'proceso_certificacion',
                id_externo='' if nivel_modulo else str((proceso or self.proceso).id),
                creado_por=self.usuario,
            )
            documento.refresh_from_db()
        return documento

    def quitar_permiso_grupo(self, codename):
        permiso = Permission.objects.get(
            content_type__app_label='portafolio', codename=codename,
        )
        self.grupo.permissions.remove(permiso)
        self.usuario = User.objects.get(pk=self.usuario.pk)
        self.client.force_login(self.usuario)

    def test_centro_muestra_generales_modulo_y_todos_los_procesos_intera(self):
        actual = self.documento('Documento actual', modulo='certificacion_intera')
        modulo = self.documento(
            'Documento del modulo', modulo='certificacion_intera', nivel_modulo=True,
        )
        otro = self.documento(
            'Documento de otro proceso', modulo='certificacion_intera',
            proceso=self.otro_proceso,
        )
        finanzas = self.documento('Documento finanzas', modulo='finanzas')
        ventas = self.documento('Documento ventas', modulo='ventas')
        general = self.documento('Documento general', ambito=Documento.Ambito.GENERAL)
        sin_clasificar = self.documento(
            'Documento sin clasificar', ambito=Documento.Ambito.SIN_CLASIFICAR,
        )

        respuesta = self.client.get(
            reverse('certificacion_intera:documentos'),
        )

        for documento in (actual, otro, modulo, general):
            self.assertContains(respuesta, documento.nombre)
        for documento in (finanzas, ventas, sin_clasificar):
            self.assertNotContains(respuesta, documento.nombre)

    def test_busqueda_se_aplica_despues_del_alcance(self):
        visible = self.documento('Acta autorizada', modulo='certificacion_intera')
        oculto = self.documento(
            'Acta confidencial', modulo='certificacion_intera', proceso=self.otro_proceso,
        )
        respuesta = self.client.get(
            reverse('certificacion_intera:documentos'),
            {'q': 'Acta', 'proceso': self.proceso.id},
        )
        self.assertContains(respuesta, visible.nombre)
        self.assertNotContains(respuesta, oculto.nombre)

    def test_sin_consultar_componente_no_expone_documentos(self):
        documento = self.documento('No expuesto', modulo='certificacion_intera')
        self.quitar_permiso_grupo('consultar_documento')
        respuesta = self.client.get(
            reverse('certificacion_intera:documentos'),
        )
        self.assertNotContains(respuesta, documento.nombre)
        self.assertContains(respuesta, 'No tienes permiso para consultar documentos')

    def test_descarga_autorizada_general_y_del_proceso(self):
        for documento in (
            self.documento('Descarga proceso', modulo='certificacion_intera'),
            self.documento('Descarga general', ambito=Documento.Ambito.GENERAL),
        ):
            respuesta = self.client.get(reverse(
                'certificacion_intera:proceso_documento_descargar',
                args=[self.proceso.id, documento.id],
            ))
            self.assertEqual(respuesta.status_code, 200)
            respuesta.close()

    def test_descarga_rechaza_permiso_otro_proceso_modulo_e_id_manipulado(self):
        otro = self.documento(
            'Descarga ajena', modulo='certificacion_intera', proceso=self.otro_proceso,
        )
        finanzas = self.documento('Descarga finanzas', modulo='finanzas')
        for documento in (otro, finanzas):
            self.assertEqual(self.client.get(reverse(
                'certificacion_intera:proceso_documento_descargar',
                args=[self.proceso.id, documento.id],
            )).status_code, 404)
        self.quitar_permiso_grupo('descargar_documento')
        general = self.documento('Sin permiso descarga', ambito=Documento.Ambito.GENERAL)
        self.assertEqual(self.client.get(reverse(
            'certificacion_intera:proceso_documento_descargar',
            args=[self.proceso.id, general.id],
        )).status_code, 404)

    def test_archivo_faltante_conserva_404_controlado(self):
        documento = self.documento('Archivo faltante', modulo='certificacion_intera')
        documento.archivo.storage.delete(documento.archivo.name)
        respuesta = self.client.get(reverse(
            'certificacion_intera:proceso_documento_descargar',
            args=[self.proceso.id, documento.id],
        ))
        self.assertEqual(respuesta.status_code, 404)
        self.assertContains(respuesta, 'almacenamiento configurado', status_code=404)

    def test_incorporacion_crea_documento_version_y_relacion_sin_permiso_relacionar(self):
        self.assertFalse(self.usuario.has_perm('portafolio.relacionar_documento'))
        respuesta = self.client.post(
            reverse('certificacion_intera:documento_incorporar'),
            {
                'nombre': 'Evidencia incorporada', 'descripcion': 'Desde INTERA',
                'archivo': SimpleUploadedFile('evidencia.pdf', b'pdf'),
                'alcance': 'proceso', 'proceso': self.proceso.id,
                'modulo': 'finanzas', 'id_externo': '999',
            },
        )
        self.assertRedirects(
            respuesta, reverse('certificacion_intera:documentos'),
        )
        documento = Documento.objects.get(nombre='Evidencia incorporada')
        self.assertEqual(documento.ambito, Documento.Ambito.ESPECIFICO)
        self.assertEqual(documento.origen, Documento.Origen.INCORPORADO)
        version = VersionDocumento.objects.get(documento=documento)
        self.assertEqual(version.cargado_por, self.usuario)
        relacion = RelacionDocumento.objects.get(documento=documento)
        self.assertEqual(relacion.modulo, 'certificacion_intera')
        self.assertEqual(relacion.tipo_proceso, 'proceso_certificacion')
        self.assertEqual(relacion.id_externo, str(self.proceso.id))

    def test_sin_incorporar_o_sin_acceso_intera_no_crea_documento(self):
        self.quitar_permiso_grupo('incorporar_documento')
        url = reverse('certificacion_intera:documento_incorporar')
        self.assertEqual(self.client.post(url, {
            'nombre': 'No creado', 'archivo': SimpleUploadedFile('no.txt', b'no'),
        }).status_code, 403)
        ajeno = User.objects.create_user(username='ajeno-intera', password='x')
        ajeno.user_permissions.add(Permission.objects.get(
            content_type__app_label='portafolio', codename='incorporar_documento',
        ))
        self.client.force_login(ajeno)
        self.assertEqual(self.client.post(url, {
            'nombre': 'Tampoco creado', 'archivo': SimpleUploadedFile('no2.txt', b'no'),
        }).status_code, 403)
        self.assertFalse(Documento.objects.filter(nombre__contains='creado').exists())

    def test_navegacion_centro_y_detalle_sin_formulario_documental(self):
        centro = self.client.get(reverse('certificacion_intera:documentos'))
        detalle = self.client.get(
            reverse('certificacion_intera:proceso_detalle', args=[self.proceso.id]),
        )
        self.assertContains(centro, 'Centro documental')
        self.assertContains(centro, 'Generar reporte')
        self.assertContains(centro, 'Incorporados')
        self.assertContains(centro, 'Generados')
        self.assertContains(detalle, 'Ver documentos')
        self.assertNotContains(detalle, 'Incorporar documento')
        self.assertNotContains(detalle, 'type="file"')

    def test_usuario_sin_acceso_intera_no_entra_al_centro(self):
        usuario = User.objects.create_user(username='sin-intera-centro', password='x')
        self.client.force_login(usuario)
        self.assertEqual(
            self.client.get(reverse('certificacion_intera:documentos')).status_code,
            403,
        )

    def test_filtros_de_alcance_y_proceso(self):
        modulo = self.documento(
            'Filtro modulo', modulo='certificacion_intera', nivel_modulo=True,
        )
        proceso = self.documento('Filtro proceso', modulo='certificacion_intera')
        otro = self.documento(
            'Filtro otro proceso', modulo='certificacion_intera', proceso=self.otro_proceso,
        )
        general = self.documento('Filtro general', ambito=Documento.Ambito.GENERAL)
        url = reverse('certificacion_intera:documentos')
        respuesta = self.client.get(url, {'alcance': 'modulo'})
        self.assertContains(respuesta, modulo.nombre)
        for documento in (proceso, otro, general):
            self.assertNotContains(respuesta, documento.nombre)
        respuesta = self.client.get(url, {'proceso': self.proceso.id})
        self.assertContains(respuesta, proceso.nombre)
        self.assertNotContains(respuesta, otro.nombre)
        self.assertNotContains(respuesta, general.nombre)

    def test_incorporacion_a_nivel_modulo(self):
        respuesta = self.client.post(
            reverse('certificacion_intera:documento_incorporar'),
            {
                'nombre': 'Manual de INTERA', 'alcance': 'modulo',
                'archivo': SimpleUploadedFile('manual.txt', b'manual'),
                'modulo': 'ventas',
            },
        )
        self.assertRedirects(respuesta, reverse('certificacion_intera:documentos'))
        documento = Documento.objects.get(nombre='Manual de INTERA')
        relacion = documento.relaciones.get()
        self.assertEqual(relacion.modulo, 'certificacion_intera')
        self.assertEqual(relacion.tipo_proceso, '')
        self.assertEqual(relacion.id_externo, '')
        self.assertEqual(documento.versiones.count(), 1)

    def test_alcance_o_proceso_manipulado_no_crea_documento(self):
        url = reverse('certificacion_intera:documento_incorporar')
        for datos in (
            {'alcance': 'finanzas'},
            {'alcance': 'proceso', 'proceso': 999999},
            {'alcance': 'proceso', 'proceso': ''},
        ):
            respuesta = self.client.post(url, {
                'nombre': 'Manipulado',
                'archivo': SimpleUploadedFile('manipulado.txt', b'x'),
                'modulo': 'ventas',
                **datos,
            })
            self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Documento.objects.filter(nombre='Manipulado').exists())

    def test_descarga_desde_centro_respeta_alcance_y_permiso(self):
        permitidos = (
            self.documento('Centro modulo', modulo='certificacion_intera', nivel_modulo=True),
            self.documento('Centro proceso', modulo='certificacion_intera'),
            self.documento('Centro general', ambito=Documento.Ambito.GENERAL),
        )
        for documento in permitidos:
            respuesta = self.client.get(reverse(
                'certificacion_intera:documento_descargar', args=[documento.id],
            ))
            self.assertEqual(respuesta.status_code, 200)
            respuesta.close()
        finanzas = self.documento('Centro finanzas', modulo='finanzas')
        self.assertEqual(self.client.get(reverse(
            'certificacion_intera:documento_descargar', args=[finanzas.id],
        )).status_code, 404)

    def test_incorporacion_es_atomica_si_falla_relacion(self):
        archivo = SimpleUploadedFile('rollback.txt', b'rollback')
        with patch(
            'apps.portafolio.services_documentales._crear_relacion_inicial_contextual',
            side_effect=RuntimeError('fallo controlado'),
        ), self.assertRaises(RuntimeError):
            incorporar_documento_contextual(
                self.usuario, 'certificacion_intera', 'proceso_certificacion',
                self.proceso.id, nombre='Rollback', archivo=archivo,
            )
        self.assertFalse(Documento.objects.filter(nombre='Rollback').exists())
        self.assertFalse(VersionDocumento.objects.filter(documento__nombre='Rollback').exists())
        self.assertFalse(RelacionDocumento.objects.filter(documento__nombre='Rollback').exists())
        self.assertFalse(any(
            'rollback' in nombre
            for nombre in default_storage.listdir('portafolio/documentos')[1]
        ))

    def test_servicio_es_reutilizable_para_otro_modulo(self):
        ventas = self.documento('Contrato ventas reusable', modulo='ventas')
        visibles = obtener_documentos_contextuales(
            self.usuario, 'ventas', 'proceso_certificacion', self.proceso.id,
        )
        self.assertIn(ventas, visibles)

    def test_certificacion_usa_componente_pero_no_accede_portafolio(self):
        respuesta = self.client.get(
            reverse('certificacion_intera:documentos'),
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Documentos')
        self.assertEqual(self.client.get(reverse('portafolio:dashboard')).status_code, 403)

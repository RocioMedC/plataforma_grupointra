"""Deja el portal sin datos capturados, para entregarlo en limpio.

Borra TODO lo que se capturó o importó (movimientos, nóminas, donativos,
catálogos de Configuración y la bitácora) y **conserva las cuentas de
usuario y los grupos** — sin al menos una cuenta nadie podría volver a
entrar al portal, porque no hay registro público.

No toca ConsultorioWeb: el portal habla con esa plataforma solo por HTTP de
lectura (`integraciones/consultorioweb.py`), no tiene su base de datos
configurada en ningún lado y este comando únicamente usa el ORM del portal.

Sin `--confirmar` no borra nada: solo enseña qué se llevaría. La cuenta
regresiva de verdad es `--confirmar`, y conviene correr antes un
`dumpdata` porque esto no se puede deshacer.
"""

from django.contrib.admin.models import LogEntry
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.auditoria.models import RegistroAuditoria
from apps.finanzas.models import (
    Ajuste, CategoriaEgreso, CitaRecepcion, ConceptoIngreso,
    ConceptoNominaAcademia, Donativo, Egreso, Honorario, Ingreso,
    LineaNominaSemanal, Maestro, NominaAcademia, NominaSemanal, Tabulador,
    TabuladorAcademia,
)

# El orden importa: hay FKs con on_delete=PROTECT (Honorario→Tabulador,
# NominaAcademia→Maestro, ConceptoNominaAcademia→TabuladorAcademia) que
# revientan si se borra primero el catálogo. Los hijos van antes que el
# padre aunque el CASCADE los arrastraría igual, para que el conteo que se
# imprime sea el real y no cero.
EN_ORDEN = [
    ('Ajustes', Ajuste),
    ('Citas de recepción importadas', CitaRecepcion),
    ('Conceptos de nómina Academia', ConceptoNominaAcademia),
    ('Nóminas de Academia', NominaAcademia),
    ('Honorarios (modelo retirado)', Honorario),
    ('Tabuladores de honorarios (modelo retirado)', Tabulador),
    ('Líneas de nómina', LineaNominaSemanal),
    ('Nóminas', NominaSemanal),
    ('Egresos', Egreso),
    ('Ingresos', Ingreso),
    ('Donativos', Donativo),
    ('Maestros de Academia', Maestro),
    ('Tabuladores de Academia', TabuladorAcademia),
    ('Conceptos de ingreso (catálogo)', ConceptoIngreso),
    ('Categorías de egreso (catálogo)', CategoriaEgreso),
    ('Bitácora de auditoría', RegistroAuditoria),
    # "Acciones recientes" de /admin/. No es dato de negocio, pero si se deja,
    # el admin del sistema entregado abre la portada y ve una lista de
    # movimientos de prueba que ya no existen.
    ('Historial de acciones de /admin/', LogEntry),
]


class Command(BaseCommand):
    help = 'Borra los datos capturados del portal y conserva las cuentas de usuario.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirmar', action='store_true',
            help='Ejecuta el borrado. Sin esta bandera solo se muestra qué se borraría.',
        )

    def handle(self, *args, **opciones):
        conteos = [(etiqueta, modelo, modelo.objects.count()) for etiqueta, modelo in EN_ORDEN]
        total = sum(c for _, _, c in conteos)

        self.stdout.write('Registros que se van a borrar:')
        for etiqueta, _, cuenta in conteos:
            self.stdout.write(f'  {cuenta:>7}  {etiqueta}')
        self.stdout.write(f'  {total:>7}  TOTAL')

        self._resumen_de_lo_que_se_conserva()

        if not opciones['confirmar']:
            self.stdout.write(self.style.WARNING(
                '\nEnsayo: no se borró nada. Vuelve a correrlo con --confirmar para hacerlo de verdad.'
            ))
            return

        if not total:
            self.stdout.write(self.style.SUCCESS('\nNo hay nada que borrar: el portal ya está limpio.'))
            return

        archivos = self._borrar_archivos_de_donativos()

        with transaction.atomic():
            for etiqueta, modelo, _ in conteos:
                borrados, _ = modelo.objects.all().delete()
                self.stdout.write(f'  borrado: {etiqueta} ({borrados} filas, incluidas las dependientes)')

        self.stdout.write(self.style.SUCCESS(
            f'\nListo. Se borraron {total} registros y {archivos} archivos de donativos.'
        ))
        self._resumen_de_lo_que_se_conserva()

    def _borrar_archivos_de_donativos(self):
        """Los XML/PDF de los CFDI viven en MEDIA_ROOT, no en la base: si solo
        se borran las filas, los archivos quedan huérfanos en el disco."""
        borrados = 0
        for donativo in Donativo.objects.all():
            for campo in (donativo.archivo_xml, donativo.archivo_pdf):
                if campo:
                    campo.delete(save=False)
                    borrados += 1
        return borrados

    def _resumen_de_lo_que_se_conserva(self):
        from django.contrib.auth.models import Group, User

        usuarios = User.objects.count()
        grupos = Group.objects.count()
        self.stdout.write(
            f'\nSe conservan: {usuarios} cuenta(s) de usuario y {grupos} grupo(s) de permisos.'
        )
        if not usuarios:
            self.stdout.write(self.style.ERROR(
                'OJO: no hay ninguna cuenta. Nadie podrá entrar al portal hasta crear un superusuario.'
            ))

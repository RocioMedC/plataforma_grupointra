from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from apps.portafolio.models import (
    ImportacionInstrumento,
    Instrumento,
)
from apps.portafolio.services_importacion_instrumentos import (
    leer_excel,
    validar,
)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('ruta')
        parser.add_argument(
            '--dry-run',
            action='store_true',
        )

    def handle(self, *args, **options):
        archivos = sorted(
            Path(options['ruta']).glob('*.xlsx')
        )

        errores = []

        for archivo in archivos:
            try:
                datos = validar(
                    leer_excel(archivo)
                )

                p = datos['preguntas'][0]

                instrumento = Instrumento.objects.get(
                    clave=p['instrumento_clave'],
                    version=str(p['version']),
                )

                metadatos = {
                    **datos['instrumento'],
                    'variante': p.get('variante'),
                    'poblacion': p.get('poblacion'),
                    'edad_min': p.get('edad_min'),
                    'edad_max': p.get('edad_max'),
                }

                actual = (
                    ImportacionInstrumento.objects
                    .filter(
                        instrumento=instrumento
                    )
                    .first()
                )

                accion = (
                    'sin cambios'
                    if (
                        actual
                        and actual.huella_contenido
                        == datos['huella']
                    )
                    else 'completar'
                )

                self.stdout.write(
                    f'{instrumento.clave}: {accion}'
                )

                if (
                    not options['dry_run']
                    and accion == 'completar'
                ):
                    with transaction.atomic():
                        ImportacionInstrumento.objects.update_or_create(
                            instrumento=instrumento,
                            defaults={
                                'documento': (
                                    instrumento.documento_origen
                                ),
                                'huella_contenido': datos['huella'],
                                'metadatos': metadatos,
                            },
                        )

            except Exception as error:
                errores.append(
                    f'{archivo.name}: {error}'
                )

        if errores:
            raise CommandError(
                '\n'.join(errores)
            )
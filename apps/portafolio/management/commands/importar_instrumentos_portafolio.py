from pathlib import Path

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.portafolio.services_importacion_instrumentos import importar


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('ruta')
        parser.add_argument(
            '--dry-run',
            action='store_true',
        )
        parser.add_argument('--archivo')
        parser.add_argument('--clave')

    def handle(self, *args, **options):
        ruta = Path(options['ruta'])

        archivos = (
            [ruta]
            if ruta.is_file()
            else sorted(ruta.glob('*.xlsx'))
        )

        if options['archivo']:
            archivos = [
                archivo
                for archivo in archivos
                if archivo.name == options['archivo']
            ]

        if not archivos:
            raise CommandError(
                'No se encontraron archivos Excel.'
            )

        fallos = []

        for archivo in archivos:
            try:
                reporte = importar(
                    archivo,
                    dry_run=options['dry_run'],
                )

                if (
                    options['clave']
                    and reporte['clave'] != options['clave']
                ):
                    continue

                self.stdout.write(
                    self.style.SUCCESS(
                        str(reporte)
                    )
                )

            except Exception as error:
                fallos.append(
                    f'{archivo.name}: {error}'
                )

                self.stderr.write(
                    self.style.ERROR(
                        fallos[-1]
                    )
                )

        if fallos:
            raise CommandError(
                f'{len(fallos)} archivo(s) no importables.'
            )
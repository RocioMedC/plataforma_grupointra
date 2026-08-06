from django.db import migrations


CALCULADORAS_ORIENTATIVAS = (
    (
        'dass-21-adolescentes',
        'calc-dass21-adolescentes-v1',
        '1.0',
    ),
    (
        'rse-autoestima',
        'calc-rse-v1',
        '1.0',
    ),
)


def _actualizar_estado(calculadora, estado):
    definicion = dict(calculadora.definicion or {})
    definicion['estado'] = estado
    calculadora.estado = estado
    calculadora.definicion = definicion
    calculadora.save(update_fields=['estado', 'definicion'])


def ajustar_calculadoras_adolescentes(apps, schema_editor):
    CalculadoraInstrumento = apps.get_model(
        'portafolio',
        'CalculadoraInstrumento',
    )

    for instrumento_clave, calculadora_clave, version in CALCULADORAS_ORIENTATIVAS:
        for calculadora in CalculadoraInstrumento.objects.filter(
            instrumento__clave=instrumento_clave,
            instrumento__version=version,
            clave=calculadora_clave,
            version_regla=version,
            estado='activa',
        ):
            _actualizar_estado(calculadora, 'orientativa')

    # Revierte exclusivamente el cambio temporal previo de esta misma variante.
    for calculadora in CalculadoraInstrumento.objects.filter(
        instrumento__clave='ersp-plutchik-adolescentes',
        instrumento__version='1.0',
        clave='calc-ersp-adolescentes-v1',
        version_regla='1.0',
        estado='orientativa',
    ):
        _actualizar_estado(calculadora, 'bloqueada')


class Migration(migrations.Migration):
    dependencies = [
        ('portafolio', '0007_habilitar_calculadora_plutchik_orientativa'),
    ]

    operations = [
        migrations.RunPython(
            ajustar_calculadoras_adolescentes,
            migrations.RunPython.noop,
        ),
    ]

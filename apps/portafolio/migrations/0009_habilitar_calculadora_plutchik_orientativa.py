from django.db import migrations


def habilitar_calculadora_plutchik(apps, schema_editor):
    CalculadoraInstrumento = apps.get_model(
        'portafolio',
        'CalculadoraInstrumento',
    )
    for calculadora in CalculadoraInstrumento.objects.filter(
        instrumento__clave='ersp-plutchik-adolescentes',
        instrumento__version='1.0',
        clave='calc-ersp-adolescentes-v1',
        version_regla='1.0',
        estado='bloqueada',
    ):
        definicion = dict(calculadora.definicion or {})
        definicion['estado'] = 'orientativa'
        calculadora.estado = 'orientativa'
        calculadora.definicion = definicion
        calculadora.save(update_fields=['estado', 'definicion'])


class Migration(migrations.Migration):
    dependencies = [
        ('portafolio', '0008_calculadoras_adolescentes_orientativas'),
    ]

    operations = [
        migrations.RunPython(
            habilitar_calculadora_plutchik,
            migrations.RunPython.noop,
        ),
    ]

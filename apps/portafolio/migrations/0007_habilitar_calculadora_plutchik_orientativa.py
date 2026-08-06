from django.db import migrations


def habilitar_calculadora_plutchik(apps, schema_editor):
    CalculadoraInstrumento = apps.get_model('portafolio', 'CalculadoraInstrumento')

    for calculadora in CalculadoraInstrumento.objects.filter(
        instrumento__clave='ersp-plutchik-adolescentes',
        estado='bloqueada',
    ):
        definicion = dict(calculadora.definicion or {})
        definicion['estado'] = 'orientativa'
        calculadora.estado = 'orientativa'
        calculadora.definicion = definicion
        calculadora.save(update_fields=['estado', 'definicion'])


class Migration(migrations.Migration):
    dependencies = [
        ('portafolio', '0006_remove_documento_huella_contenido_and_more'),
    ]

    operations = [
        migrations.RunPython(
            habilitar_calculadora_plutchik,
            migrations.RunPython.noop,
        ),
    ]

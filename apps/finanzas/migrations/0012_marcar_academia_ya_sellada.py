from django.db import migrations


def marcar_como_selladas(apps, schema_editor):
    """Las nóminas de Academia capturadas ANTES de la Fase 4 ya generaron sus
    Egresos en el momento de la captura (ese era el flujo viejo: capturar =
    sellar). Con el campo `estado` nuevo quedarían en Borrador, y darles
    "Sellar" generaría sus egresos por segunda vez — es decir, pagarle dos
    veces al docente.

    Esta migración las marca como selladas basándose en la evidencia real:
    que ya exista un Egreso con su referencia. No se apoya en la fecha de
    creación ni en un corte arbitrario.
    """
    NominaAcademia = apps.get_model('finanzas', 'NominaAcademia')
    Egreso = apps.get_model('finanzas', 'Egreso')

    for nomina in NominaAcademia.objects.filter(estado='borrador'):
        if Egreso.objects.filter(referencia_externa__startswith=f'academia:nomina:{nomina.pk}:').exists():
            nomina.estado = 'sellada'
            nomina.save(update_fields=['estado'])


def revertir(apps, schema_editor):
    # Volver a marcarlas como borrador reintroduciría justamente el riesgo de
    # doble pago que esta migración evita, así que la reversa no hace nada.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('finanzas', '0011_nominaacademia_estado_nominaacademia_fecha_pago_and_more'),
    ]

    operations = [
        migrations.RunPython(marcar_como_selladas, revertir),
    ]

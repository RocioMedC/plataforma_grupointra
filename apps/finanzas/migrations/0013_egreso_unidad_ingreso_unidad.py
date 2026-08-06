from django.db import migrations, models

# Conceptos de Ingreso que son de la escuela, no de la clínica. Se usan solo
# para clasificar lo ya capturado antes de que existiera el campo `unidad`;
# de aquí en adelante la unidad se elige a mano en el formulario y no se
# infiere del concepto (un concepto agregado desde Configuración puede ser
# de cualquiera de las dos).
CONCEPTOS_ACADEMIA = [
    'inscripcion_diplomado', 'mensualidad_diplomado',
    'inscripcion_taller', 'mensualidad_taller', 'curso_certificacion',
]


def clasificar_historico(apps, schema_editor):
    """Reparte lo ya capturado entre Intra y Academia. Todo nace en 'intra'
    por el default del campo, así que aquí solo se corrige lo que sí es de
    la escuela: los egresos de nómina de Academia (los genera
    `nomina_academia.sellar_nomina_academia`) y los ingresos de diplomados,
    talleres y cursos. Lo demás — consultas del Reporte de Recepción, nómina
    de terapeutas, renta, servicios, insumos — se queda en Intra."""
    Egreso = apps.get_model('finanzas', 'Egreso')
    Ingreso = apps.get_model('finanzas', 'Ingreso')
    Egreso.objects.filter(categoria='nomina_academia').update(unidad='academia')
    Ingreso.objects.filter(concepto__in=CONCEPTOS_ACADEMIA).update(unidad='academia')


def volver_todo_a_intra(apps, schema_editor):
    """Reversa: el campo se va a borrar de todos modos, pero dejar la
    migración reversible permite hacer rollback sin trabarse."""
    apps.get_model('finanzas', 'Egreso').objects.update(unidad='intra')
    apps.get_model('finanzas', 'Ingreso').objects.update(unidad='intra')


class Migration(migrations.Migration):

    dependencies = [
        ('finanzas', '0012_marcar_academia_ya_sellada'),
    ]

    operations = [
        migrations.AddField(
            model_name='egreso',
            name='unidad',
            field=models.CharField(choices=[('intra', 'Intra'), ('academia', 'Academia')], default='intra', max_length=10),
        ),
        migrations.AddField(
            model_name='ingreso',
            name='unidad',
            field=models.CharField(choices=[('intra', 'Intra'), ('academia', 'Academia')], default='intra', max_length=10),
        ),
        migrations.RunPython(clasificar_historico, volver_todo_a_intra),
    ]

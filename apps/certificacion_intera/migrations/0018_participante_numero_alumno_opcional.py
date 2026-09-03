from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('certificacion_intera', '0017_alter_aplicacioninstrumento_estado'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='participante',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='participante',
            name='numero_alumno',
            field=models.CharField(
                blank=True,
                default='',
                max_length=50,
                verbose_name='Número de alumno / lista (opcional)',
            ),
        ),
        migrations.AlterField(
            model_name='entrevistaseguimiento',
            name='numero_alumno_confirmado',
            field=models.CharField(
                blank=True,
                default='',
                max_length=50,
                verbose_name='Número de alumno / lista (opcional)',
            ),
        ),
    ]

"""Estructura reutilizable de la entrevista 1:1; no contiene respuestas individuales."""

from .models import (
    Instrumento,
    PreguntaInstrumento,
    RevisionInstrumento,
    SeccionInstrumento,
)


CLAVE_ENTREVISTA = 'entrevista-1a1'

SECCIONES = [
    (
        'MOT',
        'Motivación para concluir el programa',
    ),
    (
        'DES',
        'Riesgo de deserción',
    ),
    (
        'RES',
        'Resiliencia y superación',
    ),
    (
        'MOD',
        'MODORIS',
    ),
]

PREGUNTAS = [
    (
        'MOT',
        'MOT-01',
        '¿Por qué eligió este programa para estudiar?',
        'texto_libre',
        True,
        None,
    ),
    (
        'MOT',
        'MOT-02',
        '¿Tienes algún plan para concluir tu carrera?',
        'si_no',
        True,
        None,
    ),
    (
        'MOT',
        'MOT-03',
        '¿Cuál?',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'MOT-02',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'MOT',
        'MOT-04',
        (
            'Del 1 al 10, ¿qué tan motivado se encuentra '
            'para concluir el programa?'
        ),
        'escala',
        True,
        None,
    ),
    (
        'DES',
        'DES-01',
        '¿Usted o su familia padece alguna enfermedad crónica?',
        'si_no',
        True,
        None,
    ),
    (
        'DES',
        'DES-02',
        '¿Qué enfermedad?',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'DES-01',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'DES',
        'DES-03',
        'Parentesco',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'DES-01',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'DES',
        'DES-04',
        '¿Usted o su familia padece alguna enfermedad mental?',
        'si_no',
        True,
        None,
    ),
    (
        'DES',
        'DES-05',
        '¿Qué enfermedad?',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'DES-04',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'DES',
        'DES-06',
        'Parentesco',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'DES-04',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'DES',
        'DES-07',
        (
            'Si ocurriera algo que te hiciera abandonar '
            'la escuela, ¿qué sería?'
        ),
        'texto_libre',
        True,
        None,
    ),
    (
        'DES',
        'DES-08',
        '¿Quién soporta tus gastos personales y educativos?',
        'texto_libre',
        True,
        None,
    ),
    (
        'DES',
        'DES-09',
        '¿Cómo podrías solventar tus gastos de otra manera?',
        'texto_libre',
        True,
        None,
    ),
    (
        'RES',
        'RES-01',
        '¿Has sido víctima de algún tipo de acoso escolar?',
        'si_no',
        True,
        None,
    ),
    (
        'RES',
        'RES-02',
        (
            '¿Conoces qué es el acoso escolar o bullying '
            'y sus consecuencias?'
        ),
        'si_no',
        True,
        None,
    ),
    (
        'RES',
        'RES-03',
        'Observaciones',
        'texto_libre',
        False,
        None,
    ),
    (
        'MOD',
        'MOD-01',
        'En las últimas semanas, ¿ha deseado estar muerto?',
        'si_no',
        True,
        None,
    ),
    (
        'MOD',
        'MOD-02',
        (
            'En las últimas semanas, ¿ha sentido que usted '
            'o su familia estarían mejor si estuviera muerto?'
        ),
        'si_no',
        True,
        None,
    ),
    (
        'MOD',
        'MOD-03',
        'En la última semana, ¿ha pensado en suicidarse?',
        'si_no',
        True,
        None,
    ),
    (
        'MOD',
        'MOD-04',
        '¿Alguna vez ha intentado suicidarse?',
        'si_no',
        True,
        None,
    ),
    (
        'MOD',
        'MOD-05',
        '¿Cómo lo hizo?',
        'texto_libre',
        False,
        {
            'pregunta_clave': 'MOD-04',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'MOD',
        'MOD-06',
        '¿Cuándo lo hizo?',
        'texto_corto',
        False,
        {
            'pregunta_clave': 'MOD-04',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
    (
        'MOD',
        'MOD-07',
        '¿Está pensando en suicidarse en este momento?',
        'si_no',
        True,
        None,
    ),
    (
        'MOD',
        'MOD-08',
        'Describa estos pensamientos: planes, intención o preparativos',
        'texto_libre',
        False,
        {
            'pregunta_clave': 'MOD-07',
            'operador': 'igual',
            'valor': 'si',
        },
    ),
]


def publicar_revision(instrumento):
    estructura = {
        'secciones': [
            {
                'clave': seccion.clave,
                'nombre': seccion.nombre,
                'descripcion': seccion.descripcion,
                'orden': seccion.orden,
            }
            for seccion in instrumento.secciones.all()
        ],
        'preguntas': [
            {
                'id': pregunta.id,
                'clave': pregunta.clave,
                'texto': pregunta.texto,
                'tipo_respuesta': pregunta.tipo_respuesta,
                'opciones': pregunta.opciones,
                'requerida': pregunta.requerida,
                'seccion': (
                    pregunta.seccion.clave
                    if pregunta.seccion
                    else None
                ),
                'condicion_visibilidad': (
                    pregunta.condicion_visibilidad
                ),
            }
            for pregunta in instrumento.preguntas.select_related(
                'seccion'
            )
        ],
    }

    return RevisionInstrumento.objects.get_or_create(
        instrumento=instrumento,
        version=instrumento.version,
        defaults={
            'estructura': estructura,
        },
    )[0]


def cargar_plantilla_entrevista_1a1():
    instrumento, _ = Instrumento.objects.get_or_create(
        clave=CLAVE_ENTREVISTA,
        defaults={
            'nombre': 'Entrevista 1:1',
            'descripcion': (
                'Plantilla privada para Certificación INTERA'
            ),
            'activo': True,
            'version': '1.0',
        },
    )

    secciones = {
        clave: SeccionInstrumento.objects.get_or_create(
            instrumento=instrumento,
            clave=clave,
            defaults={
                'nombre': nombre,
                'orden': indice + 1,
            },
        )[0]
        for indice, (clave, nombre) in enumerate(SECCIONES)
    }

    opciones_si_no = [
        {
            'valor': 'si',
            'etiqueta': 'Sí',
        },
        {
            'valor': 'no',
            'etiqueta': 'No',
        },
    ]

    for orden, (
        seccion,
        clave,
        texto,
        tipo,
        requerida,
        condicion,
    ) in enumerate(PREGUNTAS, 1):
        opciones = (
            opciones_si_no
            if tipo == 'si_no'
            else (
                [
                    {
                        'valor': str(indice),
                        'etiqueta': str(indice),
                    }
                    for indice in range(1, 11)
                ]
                if clave == 'MOT-04'
                else None
            )
        )

        PreguntaInstrumento.objects.update_or_create(
            instrumento=instrumento,
            clave=clave,
            defaults={
                'seccion': secciones[seccion],
                'orden': orden,
                'texto': texto,
                'tipo_respuesta': tipo,
                'opciones': opciones,
                'requerida': requerida,
                'condicion_visibilidad': condicion,
            },
        )

    return instrumento, publicar_revision(instrumento)
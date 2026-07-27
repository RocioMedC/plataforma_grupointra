"""Ayudas para armar textos que van a campos con largo limitado.

Existe por una diferencia real entre desarrollo y producción: SQLite (local)
**no** valida el largo de un CharField, y Postgres (Railway) **sí** —
responde `DataError: value too long for type character varying(N)` y el
usuario ve un 500. Un concepto armado a mano con el nombre de una persona y
un periodo adentro puede pasarse de largo sin que ninguna prueba local se
entere.
"""


def recortar(texto, largo):
    """Recorta a `largo` caracteres, dejando un '…' visible cuando hubo
    recorte para que no parezca que el dato venía cortado de origen."""
    texto = str(texto or '')
    if len(texto) <= largo:
        return texto
    return texto[: largo - 1].rstrip() + '…'


def concepto_egreso(texto):
    """Recorta al largo de `Egreso.concepto`. Se importa el modelo aquí
    dentro para no crear un ciclo de importación con models.py."""
    from .models import Egreso

    return recortar(texto, Egreso._meta.get_field('concepto').max_length)

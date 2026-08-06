"""Criterio único de "cuánto dinero es real" para todo el módulo.

Vive aparte de `views.py` porque lo consultan tanto las pantallas (tablero,
Reportes) como los documentos que se descargan (`reportes.py`). Si estas
reglas se duplicaran, el Estado de resultados en pantalla y el PDF del mismo
periodo podrían dar números distintos, que es justo lo que no debe pasar.
"""

from decimal import Decimal

from django.db.models import Sum

from .models import Donativo, Egreso, Ingreso


def suma(queryset, campo='monto'):
    return queryset.aggregate(total=Sum(campo))['total'] or Decimal('0')


def ingresos_efectivos(queryset):
    """Ingresos que ya son dinero real: el monto completo si está Pagado,
    solo lo cobrado (monto_pagado) si está Parcial. Un ingreso Pendiente no
    cuenta todavía — así lo pidió Administración al revisar el tablero."""
    pagado = suma(queryset.filter(estatus=Ingreso.Estatus.PAGADO))
    parcial = suma(queryset.filter(estatus=Ingreso.Estatus.PARCIAL), 'monto_pagado')
    return pagado + parcial


def egresos_efectivos(queryset):
    """Egresos ya pagados; uno Pendiente no cuenta hasta que se pague."""
    return suma(queryset.filter(estatus=Egreso.Estatus.PAGADO))


def donativos_efectivos(queryset):
    """Donativos vigentes o en trámite; uno Cancelado no debe sumar."""
    return suma(queryset.exclude(estatus_cfdi=Donativo.EstatusCFDI.CANCELADO))

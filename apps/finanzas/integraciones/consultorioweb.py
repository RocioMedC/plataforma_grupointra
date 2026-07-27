import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class ConsultorioWebError(Exception):
    """Error de comunicación con la API de ConsultorioWeb (red, timeout,
    autenticación o respuesta inesperada)."""


# ConsultorioWeb corre en Railway y su servicio se duerme cuando nadie lo
# usa. La primera llamada del día paga el arranque en frío del contenedor
# —bastante más de los 10s que teníamos— aunque ya despierto conteste en
# menos de 5s hasta para un año entero de citas. De ahí las dos medidas de
# abajo: un plazo holgado y un reintento.
TIMEOUT_POR_DEFECTO = int(getattr(settings, 'CONSULTORIOWEB_TIMEOUT', 45))


def _get(ruta, params, timeout):
    url = f'{settings.CONSULTORIOWEB_API_URL.rstrip("/")}{ruta}'
    cabeceras = {'X-API-Key': settings.CONSULTORIOWEB_API_KEY}
    try:
        respuesta = requests.get(url, params=params, timeout=timeout, headers=cabeceras)
        respuesta.raise_for_status()
    except requests.Timeout:
        # Un timeout casi siempre es el arranque en frío: esa primera llamada
        # ya dejó el servicio despierto, así que el reintento suele contestar
        # de inmediato. Se reintenta solo en timeout, no en cualquier error:
        # repetir un 500 o un 403 no arregla nada.
        logger.warning('ConsultorioWeb no respondió en %ss (%s); reintentando una vez.', timeout, ruta)
        try:
            respuesta = requests.get(url, params=params, timeout=timeout, headers=cabeceras)
            respuesta.raise_for_status()
        except requests.RequestException as exc:
            raise ConsultorioWebError(
                'ConsultorioWeb no respondió a tiempo, ni siquiera al segundo intento. '
                'Suele pasar cuando ese servidor lleva rato sin usarse: espera un momento '
                'y vuelve a intentar.'
            ) from exc
    except requests.RequestException as exc:
        raise ConsultorioWebError(f'No se pudo conectar con ConsultorioWeb: {exc}') from exc
    return respuesta.json()


def obtener_cortes_semanales(fecha_inicio=None, fecha_fin=None, timeout=None):
    """Llama a GET /api/nomina-semanal/ de ConsultorioWeb y regresa la lista
    de cortes tal cual la entrega la API (sin filtrar por estatus: eso es
    responsabilidad de la capa de negocio, ver nomina_semanal.py)."""
    params = {}
    if fecha_inicio:
        params['fecha_inicio'] = fecha_inicio
    if fecha_fin:
        params['fecha_fin'] = fecha_fin
    return _get('/api/nomina-semanal/', params, timeout or TIMEOUT_POR_DEFECTO)


def obtener_citas_recepcion(fecha_inicio=None, fecha_fin=None, timeout=None):
    """Llama a GET /api/reporte-general/ de ConsultorioWeb y regresa la lista
    de citas del rango tal cual la entrega la API (sin aplicar la regla de
    qué cuenta como ingreso: eso es responsabilidad de
    integraciones/importador_recepcion.py). Mismo formato de dict que espera
    esa capa (ver integraciones/reporte_recepcion.py::leer_reporte_excel),
    excepto que fecha/hora vienen como strings ISO en vez de objetos date/time."""
    params = {}
    if fecha_inicio:
        params['fecha_inicio'] = fecha_inicio
    if fecha_fin:
        params['fecha_fin'] = fecha_fin
    return _get('/api/reporte-general/', params, timeout or TIMEOUT_POR_DEFECTO)

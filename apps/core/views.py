from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.core.configuracion.modulos import modulos_para


@login_required
def dashboard_view(request):
    modulos = modulos_para(request.user)
    accesos_rapidos = [m for m in modulos if m['disponible']][:3]

    contexto = {
        'modulos': modulos,
        'accesos_rapidos': accesos_rapidos,
    }
    return render(request, 'core/dashboard.html', contexto)


def csrf_failure_view(request, reason=''):
    """`CSRF_FAILURE_VIEW` (ver settings.py): reemplaza la página en blanco
    "403 Forbidden" que Django muestra por default cuando un formulario se
    rechaza por CSRF. El caso típico que reportaron los usuarios: usar el
    botón "atrás" del navegador para volver a una pantalla que se renderizó
    hace rato y reenviar un formulario desde ahí — el token de esa página
    vieja ya no es válido. No hay nada que recuperar de la petición
    original (por diseño, CSRF se rechaza antes de que la vista corra), así
    que esto solo le explica al usuario qué pasó y le da un botón para
    volver a intentar con una página fresca, en vez de un error mudo."""
    return render(request, 'core/csrf_error.html', status=403)

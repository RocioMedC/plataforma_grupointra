class NoCacheMiddleware:
    """Evita que el navegador sirva una página protegida desde su caché local
    (botón "atrás") después de cerrar sesión: sin este header, un usuario que
    cierra sesión y luego presiona "atrás" puede seguir viendo el Tablero o
    Finanzas con los datos que ya estaban renderizados en esa pestaña, sin
    que el servidor vuelva a pedir credenciales. No aplica a /static/ ni
    /media/, que sí deben poder cachearse."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/static/') or request.path.startswith('/media/'):
            return response
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response

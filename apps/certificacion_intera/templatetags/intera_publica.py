from django import template


register = template.Library()


NOMBRES_PUBLICOS_POR_CLAVE = {
    'ersp-plutchik-adolescentes': 'Escala de Plutchik',
    'rse-autoestima': 'Escala de Rosenberg',
}


@register.filter
def nombre_publico_intera(instrumento):
    """Presenta nombres adecuados al participante sin alterar Portafolio."""
    if instrumento is None:
        return ''
    return NOMBRES_PUBLICOS_POR_CLAVE.get(
        instrumento.clave,
        instrumento.nombre,
    )

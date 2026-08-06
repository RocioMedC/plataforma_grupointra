from functools import wraps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from apps.core.permisos.grupos import usuario_pertenece_a
from .forms import DocumentoForm, InstrumentoForm, PlantillaPDFForm, PreguntaInstrumentoForm, RecursoCompartidoForm, ReporteForm
from .models import Documento, Instrumento, PlantillaPDF, PreguntaInstrumento, RecursoCompartido, Reporte
from .services_importacion import importar_preguntas_desde_documento

CATALOGOS = {
    'instrumento': (Instrumento, InstrumentoForm, 'portafolio:instrumentos'),
    'documento': (Documento, DocumentoForm, 'portafolio:documentos'),
    'plantilla': (PlantillaPDF, PlantillaPDFForm, 'portafolio:plantillas'),
    'reporte': (Reporte, ReporteForm, 'portafolio:reportes'),
    'recurso': (RecursoCompartido, RecursoCompartidoForm, 'portafolio:recursos'),
}


def acceso_portafolio_requerido(vista):
    @wraps(vista)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not usuario_pertenece_a(request.user, 'Dirección', 'Sistemas', 'Certificación'):
            raise PermissionDenied
        return vista(request, *args, **kwargs)
    return wrapper


@acceso_portafolio_requerido
def dashboard_view(request):
    return render(request, 'portafolio/dashboard.html', {'vista_actual': 'dashboard', 'totales': [('Instrumentos', Instrumento.objects.count(), 'portafolio:instrumentos'), ('Documentos', Documento.objects.count(), 'portafolio:documentos'), ('Plantillas PDF', PlantillaPDF.objects.count(), 'portafolio:plantillas'), ('Reportes', Reporte.objects.count(), 'portafolio:reportes'), ('Recursos', RecursoCompartido.objects.count(), 'portafolio:recursos')]})


def _catalogo(request, modelo, template, titulo, vista, crear_url, form_class=None, instrumento=None):
    if request.method == 'POST' and form_class:
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            if instrumento: item.instrumento = instrumento
            item.save()
            if instrumento:
                return redirect('portafolio:preguntas', instrumento_id=instrumento.id)
            return redirect(crear_url)
    items = modelo.all() if hasattr(modelo, 'all') else modelo.objects.all()
    return render(request, template, {'vista_actual': vista, 'titulo': titulo, 'items': items, 'form': form_class() if form_class else None, 'instrumento': instrumento, 'es_instrumento': modelo is Instrumento})


@acceso_portafolio_requerido
def instrumentos_view(request): return _catalogo(request, Instrumento, 'portafolio/catalogo.html', 'Instrumentos', 'instrumentos', 'portafolio:instrumentos', InstrumentoForm)


@acceso_portafolio_requerido
def importar_preguntas_view(request, instrumento_id):
    instrumento = get_object_or_404(Instrumento, id=instrumento_id)
    if request.method != 'POST':
        return redirect('portafolio:instrumentos')
    try:
        total = importar_preguntas_desde_documento(instrumento)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
    else:
        messages.success(request, f'Se importaron {total} preguntas desde el Documento origen de Portafolio.')
    return redirect('portafolio:instrumentos')
@acceso_portafolio_requerido
def preguntas_view(request, instrumento_id):
    instrumento = get_object_or_404(Instrumento, id=instrumento_id)
    return _catalogo(request, instrumento.preguntas, 'portafolio/catalogo.html', f'Preguntas · {instrumento.nombre}', 'instrumentos', 'portafolio:preguntas', PreguntaInstrumentoForm, instrumento)


@acceso_portafolio_requerido
def pregunta_editar_view(request, pregunta_id):
    pregunta = get_object_or_404(PreguntaInstrumento, id=pregunta_id)
    form = PreguntaInstrumentoForm(request.POST or None, instance=pregunta)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('portafolio:preguntas', instrumento_id=pregunta.instrumento_id)
    return render(request, 'portafolio/editar.html', {'titulo': 'Editar pregunta', 'form': form})


@acceso_portafolio_requerido
def pregunta_eliminar_view(request, pregunta_id):
    pregunta = get_object_or_404(PreguntaInstrumento, id=pregunta_id)
    instrumento_id = pregunta.instrumento_id
    if request.method == 'POST':
        pregunta.delete()
        return redirect('portafolio:preguntas', instrumento_id=instrumento_id)
    return render(request, 'portafolio/eliminar.html', {'item': pregunta})
@acceso_portafolio_requerido
def documentos_view(request):
    form = DocumentoForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        documento = form.save(commit=False); documento.cargado_por = request.user; documento.save()
        return redirect('portafolio:documentos')
    documentos = Documento.objects.select_related('categoria', 'cargado_por').all()
    busqueda = request.GET.get('q', '').strip(); categoria = request.GET.get('categoria', '')
    if busqueda: documentos = documentos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda))
    if categoria: documentos = documentos.filter(categoria_id=categoria)
    from .models import CategoriaDocumento
    return render(request, 'portafolio/documentos.html', {'vista_actual': 'documentos', 'form': form, 'items': documentos, 'busqueda': busqueda, 'categoria_actual': categoria, 'categorias': CategoriaDocumento.objects.filter(activa=True)})
@acceso_portafolio_requerido
def plantillas_view(request): return _catalogo(request, PlantillaPDF, 'portafolio/catalogo.html', 'Plantillas PDF', 'plantillas', 'portafolio:plantillas', PlantillaPDFForm)
@acceso_portafolio_requerido
def reportes_view(request): return _catalogo(request, Reporte, 'portafolio/catalogo.html', 'Reportes', 'reportes', 'portafolio:reportes', ReporteForm)
@acceso_portafolio_requerido
def recursos_view(request): return _catalogo(request, RecursoCompartido, 'portafolio/catalogo.html', 'Recursos compartidos', 'recursos', 'portafolio:recursos', RecursoCompartidoForm)


@acceso_portafolio_requerido
def editar_view(request, tipo, item_id):
    modelo, form_class, destino = CATALOGOS[tipo]
    item = get_object_or_404(modelo, id=item_id)
    form = form_class(request.POST or None, request.FILES or None, instance=item)
    if request.method == 'POST' and form.is_valid(): form.save(); return redirect(destino)
    return render(request, 'portafolio/editar.html', {'titulo': f'Editar {item}', 'form': form, 'volver': destino})


@acceso_portafolio_requerido
def eliminar_view(request, tipo, item_id):
    modelo, _, destino = CATALOGOS[tipo]
    item = get_object_or_404(modelo, id=item_id)
    if request.method == 'POST': item.delete(); return redirect(destino)
    return render(request, 'portafolio/eliminar.html', {'item': item, 'volver': destino})

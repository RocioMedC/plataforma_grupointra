"""Adaptador del contexto documental propio de Certificacion INTERA."""

from django import forms

from apps.portafolio.forms import DocumentoContextualForm

from .models import ProcesoCertificacion

MODULO_DOCUMENTAL = 'certificacion_intera'
TIPO_PROCESO_DOCUMENTAL = 'proceso_certificacion'


def contexto_documental_proceso(proceso):
    return {
        'modulo': MODULO_DOCUMENTAL,
        'tipo_proceso': TIPO_PROCESO_DOCUMENTAL,
        'id_externo': str(proceso.pk),
    }


def presentar_documentos_centro(documentos, procesos):
    """Agrega etiquetas funcionales sin copiar metadatos documentales."""
    procesos_por_id = {str(proceso.pk): proceso for proceso in procesos}
    resultado = []
    for documento in documentos:
        relaciones = list(getattr(documento, 'relaciones_modulo_contexto', ()))
        if documento.ambito == documento.Ambito.GENERAL:
            alcance, proceso = 'General', None
        elif any(not relacion.tipo_proceso for relacion in relaciones):
            alcance, proceso = 'INTERA', None
        else:
            relacionados = [
                procesos_por_id.get(relacion.id_externo)
                for relacion in relaciones
                if relacion.tipo_proceso == TIPO_PROCESO_DOCUMENTAL
            ]
            relacionados = [item for item in relacionados if item]
            alcance = 'Proceso'
            proceso = relacionados[0] if len(relacionados) == 1 else None
            if len(relacionados) > 1:
                alcance = 'Varios procesos'
        resultado.append({
            'documento': documento,
            'alcance': alcance,
            'proceso': proceso,
        })
    return resultado


class DocumentoCentroInteraForm(DocumentoContextualForm):
    ALCANCE_MODULO = 'modulo'
    ALCANCE_PROCESO = 'proceso'

    alcance = forms.ChoiceField(
        label='¿Dónde se utilizará este documento?',
        choices=(
            (ALCANCE_MODULO, 'Certificación INTERA'),
            (ALCANCE_PROCESO, 'Proceso de certificación'),
        ),
    )
    proceso = forms.ModelChoiceField(
        queryset=ProcesoCertificacion.objects.none(), required=False,
        label='Proceso de certificación',
    )

    def __init__(self, *args, procesos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proceso'].queryset = procesos if procesos is not None else ProcesoCertificacion.objects.none()

    def clean(self):
        datos = super().clean()
        if datos.get('alcance') == self.ALCANCE_PROCESO and not datos.get('proceso'):
            self.add_error('proceso', 'Selecciona un proceso de certificación.')
        return datos

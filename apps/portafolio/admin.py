from django.contrib import admin

from .models import (
    CategoriaDocumento,
    Documento,
    Instrumento,
    PlantillaPDF,
    PreguntaInstrumento,
    RecursoCompartido,
    Reporte,
    RevisionInstrumento,
    SeccionInstrumento,
)


admin.site.register(
    (
        CategoriaDocumento,
        Instrumento,
        PreguntaInstrumento,
        SeccionInstrumento,
        RevisionInstrumento,
        Documento,
        PlantillaPDF,
        Reporte,
        RecursoCompartido,
    )
)
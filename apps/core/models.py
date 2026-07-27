"""Modelos del núcleo del portal.

Los sub-paquetes de `apps/core` (auditoria, usuarios, configuracion...) son
organizativos, no apps Django aparte, así que sus modelos se importan aquí
para que Django los descubra y les genere migraciones dentro de la app
`core`.
"""

from .auditoria.models import RegistroAuditoria  # noqa: F401

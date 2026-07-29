"""
Formularios del módulo Administración.

Activos: ``rendiciones``, ``maestros_rendicion`` (R003), ``bancos`` (B004).
Esqueleto: facturación, factoring, R004+.
"""
from .bancos import *  # noqa: F401,F403
from .maestros_rendicion import *  # noqa: F401,F403
from .rendiciones import *  # noqa: F401,F403

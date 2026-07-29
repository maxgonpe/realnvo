"""
A004 — Matriz de permisos del módulo Administración.

Pendiente de implementar (grupos Django o permisos custom).
Códigos tentativos alineados a la Gantt.
"""

# Códigos de permiso (esqueleto)
PERM_RENDICION_VER = "adm.rendicion.ver"
PERM_RENDICION_CREAR = "adm.rendicion.crear"
PERM_RENDICION_PRESENTAR = "adm.rendicion.presentar"
PERM_RENDICION_REVISAR = "adm.rendicion.revisar"
PERM_RENDICION_APROBAR = "adm.rendicion.aprobar"
PERM_RENDICION_LIQUIDAR = "adm.rendicion.liquidar"

PERM_BANCO_VER = "adm.banco.ver"
PERM_BANCO_IMPORTAR = "adm.banco.importar"
PERM_BANCO_CONCILIAR = "adm.banco.conciliar"
PERM_BANCO_CERRAR = "adm.banco.cerrar"
PERM_BANCO_CLASIFICAR = "adm.banco.clasificar"
PERM_BANCO_RECLASIFICAR = "adm.banco.reclasificar"
PERM_BANCO_RECLASIFICAR_CONCILIADO = "adm.banco.reclasificar_conciliado"
PERM_BANCO_HISTORIAL_CLASIFICACION = "adm.banco.ver_historial_clasificacion"

PERM_FACTURA_VER = "adm.factura.ver"
PERM_FACTURA_REGISTRAR = "adm.factura.registrar"
PERM_PAGO_REGISTRAR = "adm.pago.registrar"
PERM_COBRANZA_GESTIONAR = "adm.cobranza.gestionar"

PERM_FACTORING_VER = "adm.factoring.ver"
PERM_FACTORING_OPERAR = "adm.factoring.operar"


def usuario_tiene_permiso(user, codigo: str) -> bool:
    """
    TODO(A004): evaluar grupos / permisos reales.
    MVP: autenticados pueden clasificar; solo staff/superuser
    reclasifican movimientos ya conciliados.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if codigo in (
        PERM_BANCO_CLASIFICAR,
        PERM_BANCO_RECLASIFICAR,
        PERM_BANCO_HISTORIAL_CLASIFICACION,
        PERM_BANCO_VER,
        PERM_BANCO_IMPORTAR,
    ):
        return True
    if codigo == PERM_BANCO_RECLASIFICAR_CONCILIADO:
        return bool(getattr(user, "is_staff", False))
    return False

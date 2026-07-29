"""
Servicios de dominio (reglas de negocio, transacciones).

Las vistas no deben contener lógica financiera crítica:
usar servicios con ``transaction.atomic()`` y, cuando haya
movimientos de dinero, ``select_for_update()``.
"""

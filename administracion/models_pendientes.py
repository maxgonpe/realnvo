"""
Modelos pendientes detectados en las mini-especificaciones.

NO son modelos Django activos. No generan migraciones.
Cuando se implemente una tarea Gantt que los necesite:
1. Copiar la clase a models.py (o al paquete models/).
2. Ajustar campos según la ficha de la tarea.
3. Crear migración.
4. Actualizar CONTROL_AVANCE.md (gaps → hecho).

Referencias:
- Bloque 6 → AdjuntoDetalleRendicion (R007)
- Bloque 9 → ReglaCruceBancario, SugerenciaCruceBancario
- Bloque 1 / R018 → posible AlertaRendicion o ampliación de AlertaCobranza
"""

# ---------------------------------------------------------------------------
# R007 — Múltiples adjuntos por gasto
# ---------------------------------------------------------------------------
# class AdjuntoDetalleRendicion(ModeloAuditoria):
#     detalle = FK(DetalleRendicion, related_name="adjuntos")
#     archivo = FileField(...)
#     nombre_original = CharField(...)
#     tipo_mime = CharField(...)
#     sha256 = CharField(...)  # anti-duplicados

# B004 — PlantillaMapeoCartola / CampoMapeoCartola → implementados en models.py

# ---------------------------------------------------------------------------
# B012 / B013 — Reglas y sugerencias de cruce
# ---------------------------------------------------------------------------
# class ReglaCruceBancario(ModeloAuditoria):
#     nombre, cuenta_bancaria, tipo_movimiento, destino, modo,
#     prioridad, puntaje_minimo, tolerancia_monto/dias, patrones, activa
#
# class SugerenciaCruceBancario(ModeloAuditoria):
#     movimiento, regla, destino_tipo, destino_id, puntaje, estado

# ---------------------------------------------------------------------------
# B016 — Evidencia de reversas (opcional; puede ser EventoConciliacion)
# ---------------------------------------------------------------------------
# class EventoConciliacion(ModeloAuditoria):
#     conciliacion / movimiento, tipo (APLICAR/REVERSAR/REABRIR/CERRAR),
#     payload JSON, usuario, correlation_id

# ---------------------------------------------------------------------------
# R018 — Alertas de rendiciones
# ---------------------------------------------------------------------------
# Opción A: ampliar AlertaCobranza.Tipo con códigos de rendición
# Opción B: class AlertaRendicion(ModeloAuditoria): ...

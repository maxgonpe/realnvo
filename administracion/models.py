"""
Modelos del módulo Administración y Finanzas — fase 1.

Áreas incluidas:
  - Banco y conciliación bancaria
  - Facturación, cobranza y factoring
  - Rendiciones y fondos por rendir

La contabilidad general, centros de costo avanzados y asientos automáticos
quedan fuera de esta etapa.
"""
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone


# ---------------------------------------------------------------------------
# Base de auditoría
# ---------------------------------------------------------------------------

class ModeloAuditoria(models.Model):
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_creados",
    )
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_actualizados",
    )

    class Meta:
        abstract = True


# ===========================================================================
# BANCO Y CONCILIACIÓN
# ===========================================================================

class Banco(ModeloAuditoria):
    nombre = models.CharField(max_length=120, unique=True)
    codigo = models.CharField(
        max_length=20,
        blank=True,
        help_text="Código interno o SBIF. Opcional; único si se informa.",
    )
    activo = models.BooleanField(default=True)
    # B001 — acceso a cartolas PDF cifradas (nunca plaintext en BD)
    clave_cartola_cifrada = models.TextField(
        blank=True,
        help_text="Clave PDF de cartolas, cifrada. No se muestra en claro.",
    )
    clave_cartola_actualizada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "adm_banco"
        ordering = ["nombre"]
        verbose_name = "Banco"
        verbose_name_plural = "Bancos"
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                condition=~models.Q(codigo=""),
                name="uniq_adm_banco_codigo_no_vacio",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def tiene_clave_cartola(self) -> bool:
        return bool(self.clave_cartola_cifrada)


class CuentaBancaria(ModeloAuditoria):
    class TipoCuenta(models.TextChoices):
        CORRIENTE = "CORRIENTE", "Cuenta corriente"
        VISTA = "VISTA", "Cuenta vista"
        AHORRO = "AHORRO", "Cuenta de ahorro"
        OTRO = "OTRO", "Otro"

    banco = models.ForeignKey(
        Banco, on_delete=models.PROTECT, related_name="cuentas"
    )
    nombre = models.CharField(
        max_length=120,
        help_text="Alias visible, p. ej. Cuenta corriente principal.",
    )
    numero_cuenta = models.CharField(max_length=40)
    tipo_cuenta = models.CharField(
        max_length=20, choices=TipoCuenta.choices, default=TipoCuenta.CORRIENTE
    )
    moneda = models.CharField(max_length=3, default="CLP")
    titular = models.CharField(max_length=150, blank=True)
    rut_titular = models.CharField(max_length=20, blank=True)
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_cuenta_bancaria"
        ordering = ["banco__nombre", "nombre"]
        verbose_name = "Cuenta bancaria"
        verbose_name_plural = "Cuentas bancarias"
        constraints = [
            models.UniqueConstraint(
                fields=["banco", "numero_cuenta"],
                name="uniq_adm_cuenta_banco_numero",
            ),
        ]

    def __str__(self):
        return f"{self.banco.nombre} — {self.numero_cuenta}"

    def numero_enmascarado(self) -> str:
        n = self.numero_cuenta or ""
        if len(n) <= 4:
            return n
        return ("*" * (len(n) - 4)) + n[-4:]


class PlantillaMapeoCartola(ModeloAuditoria):
    """B004 — Configuración de columnas / parser para interpretar cartolas."""

    class FormatoArchivo(models.TextChoices):
        CSV = "CSV", "CSV"
        XLSX = "XLSX", "Excel XLSX"
        PDF = "PDF", "PDF bancario"

    class ParserCodigo(models.TextChoices):
        GENERICO = "GENERICO", "Genérico CSV/XLSX"
        BANCO_ESTADO = "BANCO_ESTADO", "Banco Estado / CuentaRUT PDF"
        BANCO_FALABELLA = "BANCO_FALABELLA", "Banco Falabella PDF"
        BANCO_CHILE = "BANCO_CHILE", "Banco de Chile PDF"

    banco = models.ForeignKey(
        Banco,
        on_delete=models.PROTECT,
        related_name="plantillas_cartola",
    )
    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="plantillas_cartola",
        help_text="Opcional. Si se indica, tiene prioridad sobre la plantilla general del banco.",
    )
    nombre = models.CharField(max_length=120)
    formato_archivo = models.CharField(
        max_length=10,
        choices=FormatoArchivo.choices,
        default=FormatoArchivo.CSV,
    )
    parser_codigo = models.CharField(
        max_length=30,
        choices=ParserCodigo.choices,
        default=ParserCodigo.GENERICO,
        help_text="Parser PDF específico del banco, o genérico para CSV/XLSX.",
    )
    nombre_hoja = models.CharField(max_length=100, blank=True)
    fila_encabezado = models.PositiveIntegerField(default=1)
    fila_inicio_datos = models.PositiveIntegerField(default=2)
    separador_csv = models.CharField(max_length=5, default=";")
    codificacion = models.CharField(max_length=30, default="utf-8-sig")
    formato_fecha = models.CharField(max_length=30, default="%d/%m/%Y")
    fecha_sin_anio = models.BooleanField(
        default=False,
        help_text="Si la cartola imprime solo día/mes (p. ej. Banco de Chile).",
    )
    separador_decimal = models.CharField(
        max_length=1,
        default="",
        blank=True,
        help_text="Vacío = montos enteros (sin decimales). Puntos se tratan como miles.",
    )
    separador_miles = models.CharField(max_length=1, default=".")
    simbolo_moneda = models.CharField(max_length=5, blank=True, default="$")
    identificador_saldo_inicial = models.CharField(
        max_length=80, blank=True, default="SALDO INICIAL"
    )
    identificador_saldo_final = models.CharField(
        max_length=80, blank=True, default="SALDO FINAL"
    )
    ignorar_filas_vacias = models.BooleanField(default=True)
    activa = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_plantilla_mapeo_cartola"
        ordering = ["banco__nombre", "nombre", "-version"]
        verbose_name = "Plantilla de mapeo de cartola"
        verbose_name_plural = "Plantillas de mapeo de cartola"

    def __str__(self):
        alcance = (
            self.cuenta_bancaria.numero_cuenta
            if self.cuenta_bancaria_id
            else "todas las cuentas"
        )
        return f"{self.nombre} v{self.version} ({self.banco} / {alcance})"


class CampoMapeoCartola(ModeloAuditoria):
    """B004 — Columna de cartola → campo del sistema."""

    class CampoDestino(models.TextChoices):
        FECHA_OPERACION = "FECHA_OPERACION", "Fecha operación"
        FECHA_CONTABLE = "FECHA_CONTABLE", "Fecha contable"
        FECHA_VALOR = "FECHA_VALOR", "Fecha valor"
        TIPO = "TIPO", "Tipo de movimiento"
        MONTO = "MONTO", "Monto único"
        MONTO_INGRESO = "MONTO_INGRESO", "Monto ingreso"
        MONTO_EGRESO = "MONTO_EGRESO", "Monto egreso"
        SALDO = "SALDO", "Saldo"
        DESCRIPCION = "DESCRIPCION", "Descripción"
        REFERENCIA = "REFERENCIA", "Referencia"
        NUMERO_DOCUMENTO = "NUMERO_DOCUMENTO", "Número documento"
        IDENTIFICADOR_EXTERNO = "IDENTIFICADOR_EXTERNO", "Identificador externo"
        CONTRAPARTE = "CONTRAPARTE", "Contraparte"
        RUT_CONTRAPARTE = "RUT_CONTRAPARTE", "RUT contraparte"
        CUENTA_CONTRAPARTE = "CUENTA_CONTRAPARTE", "Cuenta contraparte"

    plantilla = models.ForeignKey(
        PlantillaMapeoCartola,
        on_delete=models.CASCADE,
        related_name="campos",
    )
    campo_destino = models.CharField(
        max_length=40,
        choices=CampoDestino.choices,
    )
    columna_origen = models.CharField(max_length=150)
    obligatorio = models.BooleanField(default=False)
    valor_defecto = models.CharField(max_length=255, blank=True)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "adm_campo_mapeo_cartola"
        ordering = ["orden", "id"]
        verbose_name = "Campo de mapeo de cartola"
        verbose_name_plural = "Campos de mapeo de cartola"
        constraints = [
            models.UniqueConstraint(
                fields=["plantilla", "campo_destino"],
                name="uniq_adm_campo_mapeo_plantilla_destino",
            ),
        ]

    def __str__(self):
        return f"{self.columna_origen} → {self.get_campo_destino_display()}"


class ImportacionCartola(ModeloAuditoria):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VALIDADA = "VALIDADA", "Validada"
        PROCESADA = "PROCESADA", "Procesada"
        CON_ERRORES = "CON_ERRORES", "Con errores"
        ANULADA = "ANULADA", "Anulada"

    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT, related_name="importaciones"
    )
    plantilla = models.ForeignKey(
        PlantillaMapeoCartola,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="importaciones",
    )
    fecha_desde = models.DateField()
    fecha_hasta = models.DateField()
    archivo = models.FileField(
        upload_to="administracion/cartolas/%Y/%m/", blank=True, null=True
    )
    nombre_archivo = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(max_length=64)
    total_movimientos = models.PositiveIntegerField(default=0)
    total_filas = models.PositiveIntegerField(default=0)
    total_validas = models.PositiveIntegerField(default=0)
    total_importadas = models.PositiveIntegerField(default=0)
    total_duplicadas = models.PositiveIntegerField(default=0)
    total_errores = models.PositiveIntegerField(default=0)
    validada_en = models.DateTimeField(null=True, blank=True)
    procesada_en = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    observaciones = models.TextField(blank=True)
    error_importacion = models.TextField(blank=True)

    class Meta:
        db_table = "adm_importacion_cartola"
        ordering = ["-creado_en"]
        verbose_name = "Importación de cartola"
        verbose_name_plural = "Importaciones de cartola"
        constraints = [
            models.UniqueConstraint(
                fields=["cuenta_bancaria", "sha256"],
                name="uniq_adm_cartola_cuenta_sha256",
            ),
            models.CheckConstraint(
                check=Q(fecha_hasta__gte=models.F("fecha_desde")),
                name="chk_adm_cartola_rango_fechas",
            ),
        ]

    def __str__(self):
        return (
            f"Cartola {self.cuenta_bancaria} "
            f"({self.fecha_desde} → {self.fecha_hasta})"
        )


class CartolaBancaria(ModeloAuditoria):
    """
    Cabecera de una cartola importada (titular, período, saldos y totales).
    Los montos son enteros en pesos (sin decimales), según decisión de negocio.
    """

    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT, related_name="cartolas"
    )
    importacion = models.OneToOneField(
        ImportacionCartola,
        on_delete=models.CASCADE,
        related_name="cartola",
        null=True,
        blank=True,
    )
    tipo_documento = models.CharField(max_length=80, blank=True)
    tipo_cuenta_texto = models.CharField(max_length=80, blank=True)
    numero_cartola = models.CharField(max_length=40, blank=True)
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_inicio_periodo = models.DateField()
    fecha_fin_periodo = models.DateField()
    pagina_actual = models.PositiveIntegerField(null=True, blank=True)
    total_paginas = models.PositiveIntegerField(null=True, blank=True)
    referencia_documento = models.CharField(max_length=120, blank=True)
    nombre_titular = models.CharField(max_length=150, blank=True)
    tratamiento_titular = models.CharField(max_length=40, blank=True)
    correo_electronico = models.EmailField(blank=True)
    numero_cuenta_texto = models.CharField(max_length=50, blank=True)
    moneda = models.CharField(max_length=10, default="CLP")
    sucursal_cuenta = models.CharField(max_length=120, blank=True)
    codigo_sucursal_cuenta = models.CharField(max_length=40, blank=True)
    ejecutivo_cuenta = models.CharField(max_length=120, blank=True)
    telefono_banco = models.CharField(max_length=40, blank=True)

    saldo_inicial = models.BigIntegerField(null=True, blank=True)
    saldo_final = models.BigIntegerField(null=True, blank=True)
    saldo_disponible = models.BigIntegerField(null=True, blank=True)
    retenciones_total = models.BigIntegerField(null=True, blank=True)
    retencion_un_dia = models.BigIntegerField(null=True, blank=True)
    retencion_mas_un_dia = models.BigIntegerField(null=True, blank=True)

    total_depositos = models.BigIntegerField(null=True, blank=True)
    total_otros_abonos = models.BigIntegerField(null=True, blank=True)
    total_abonos = models.BigIntegerField(null=True, blank=True)
    total_cheques = models.BigIntegerField(null=True, blank=True)
    total_giros = models.BigIntegerField(null=True, blank=True)
    total_giros_autoservicio = models.BigIntegerField(null=True, blank=True)
    total_redcompra = models.BigIntegerField(null=True, blank=True)
    total_comisiones = models.BigIntegerField(null=True, blank=True)
    total_impuestos = models.BigIntegerField(null=True, blank=True)
    total_otros_cargos = models.BigIntegerField(null=True, blank=True)
    total_cargos = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "adm_cartola_bancaria"
        ordering = ["-fecha_fin_periodo", "-id"]
        verbose_name = "Cartola bancaria"
        verbose_name_plural = "Cartolas bancarias"

    def __str__(self):
        return (
            f"Cartola {self.numero_cartola or self.pk} — "
            f"{self.cuenta_bancaria} ({self.fecha_inicio_periodo}→{self.fecha_fin_periodo})"
        )


class MovimientoBancario(ModeloAuditoria):
    class Tipo(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"

    class EstadoConciliacion(models.TextChoices):
        NO_CONCILIADO = "NO_CONCILIADO", "No conciliado"
        PARCIAL = "PARCIAL", "Parcialmente conciliado"
        CONCILIADO = "CONCILIADO", "Conciliado"
        EXCLUIDO = "EXCLUIDO", "Excluido"

    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT, related_name="movimientos"
    )
    importacion = models.ForeignKey(
        ImportacionCartola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    cartola = models.ForeignKey(
        CartolaBancaria,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    fecha_operacion = models.DateField()
    fecha_contable = models.DateField(null=True, blank=True)
    fecha_valor = models.DateField(null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    # Montos enteros en pesos (sin decimales)
    monto = models.BigIntegerField(validators=[MinValueValidator(1)])
    monto_cargo = models.BigIntegerField(default=0)
    monto_abono = models.BigIntegerField(default=0)
    saldo_bancario = models.BigIntegerField(null=True, blank=True)
    descripcion_original = models.TextField(blank=True)
    descripcion_movimiento = models.TextField(blank=True)
    referencia_bancaria = models.CharField(max_length=100, blank=True)
    numero_documento = models.CharField(max_length=60, blank=True)
    identificador_externo = models.CharField(max_length=120, blank=True)
    contraparte = models.CharField(max_length=200, blank=True)
    rut_contraparte = models.CharField(max_length=20, blank=True)
    cuenta_contraparte = models.CharField(max_length=40, blank=True)
    sucursal_movimiento = models.CharField(max_length=120, blank=True)
    codigo_sucursal_movimiento = models.CharField(max_length=40, blank=True)
    tipo_movimiento = models.CharField(max_length=40, blank=True)
    canal_movimiento = models.CharField(max_length=40, blank=True)
    fecha_operacion_original = models.DateField(null=True, blank=True)
    hora_operacion_original = models.CharField(max_length=10, blank=True)
    numero_fila_origen = models.PositiveIntegerField(null=True, blank=True)
    numero_pagina_origen = models.PositiveIntegerField(null=True, blank=True)
    datos_originales = models.JSONField(default=dict, blank=True)
    fingerprint = models.CharField(max_length=64)
    estado_conciliacion = models.CharField(
        max_length=20,
        choices=EstadoConciliacion.choices,
        default=EstadoConciliacion.NO_CONCILIADO,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_movimiento_bancario"
        ordering = ["-fecha_operacion", "-id"]
        verbose_name = "Movimiento bancario"
        verbose_name_plural = "Movimientos bancarios"
        indexes = [
            models.Index(fields=["fecha_operacion"]),
            models.Index(fields=["estado_conciliacion"]),
            models.Index(fields=["tipo"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["cuenta_bancaria", "fingerprint"],
                name="uniq_adm_movimiento_fingerprint",
            ),
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_movimiento_monto_positivo",
            ),
        ]

    def __str__(self):
        return f"{self.fecha_operacion} {self.tipo} {self.monto}"

    @property
    def monto_aplicado(self):
        total = self.aplicaciones.filter(activa=True).aggregate(
            t=Sum("monto")
        )["t"]
        if total is None:
            return 0
        return int(total)

    @property
    def saldo_por_conciliar(self):
        return int(self.monto) - self.monto_aplicado

    @property
    def estado_calculado(self):
        if self.estado_conciliacion == self.EstadoConciliacion.EXCLUIDO:
            return self.EstadoConciliacion.EXCLUIDO
        aplicado = self.monto_aplicado
        if aplicado <= 0:
            return self.EstadoConciliacion.NO_CONCILIADO
        if aplicado < int(self.monto):
            return self.EstadoConciliacion.PARCIAL
        return self.EstadoConciliacion.CONCILIADO

    def actualizar_estado_conciliacion(self, guardar=True):
        nuevo = self.estado_calculado
        if self.estado_conciliacion != nuevo:
            self.estado_conciliacion = nuevo
            if guardar:
                self.save(update_fields=["estado_conciliacion", "actualizado_en"])
        return nuevo

    @property
    def clasificacion_activa(self):
        return self.clasificaciones.filter(activa=True).first()


class ClasificacionMovimientoBancario(ModeloAuditoria):
    """
    B008 — Clasificación administrativa del movimiento.
    No altera el dato bancario original ni crea aplicaciones.
    Solo una clasificación activa por movimiento.
    """

    class Categoria(models.TextChoices):
        # Ingresos
        PAGO_CLIENTE = "PAGO_CLIENTE", "Pago de cliente"
        ANTICIPO_FACTORING = "ANTICIPO_FACTORING", "Anticipo de factoring"
        LIQUIDACION_FACTORING = "LIQUIDACION_FACTORING", "Liquidación de factoring"
        DEVOLUCION_RESPONSABLE = "DEVOLUCION_RESPONSABLE", "Devolución de responsable"
        TRANSFERENCIA_INTERNA = "TRANSFERENCIA_INTERNA", "Transferencia interna"
        OTRO_INGRESO = "OTRO_INGRESO", "Otro ingreso"
        # Egresos
        ENTREGA_FONDO = "ENTREGA_FONDO", "Entrega de fondo"
        REEMBOLSO_RENDICION = "REEMBOLSO_RENDICION", "Reembolso de rendición"
        DEVOLUCION_CLIENTE = "DEVOLUCION_CLIENTE", "Devolución a cliente"
        COMISION_FACTORING = "COMISION_FACTORING", "Comisión de factoring"
        COBRO_RECURSO = "COBRO_RECURSO", "Cobro de recurso"
        GASTO_BANCARIO = "GASTO_BANCARIO", "Gasto bancario"
        OTRO_EGRESO = "OTRO_EGRESO", "Otro egreso"

    CATEGORIAS_INGRESO = {
        Categoria.PAGO_CLIENTE,
        Categoria.ANTICIPO_FACTORING,
        Categoria.LIQUIDACION_FACTORING,
        Categoria.DEVOLUCION_RESPONSABLE,
        Categoria.TRANSFERENCIA_INTERNA,
        Categoria.OTRO_INGRESO,
    }
    CATEGORIAS_EGRESO = {
        Categoria.ENTREGA_FONDO,
        Categoria.REEMBOLSO_RENDICION,
        Categoria.DEVOLUCION_CLIENTE,
        Categoria.COMISION_FACTORING,
        Categoria.COBRO_RECURSO,
        Categoria.GASTO_BANCARIO,
        Categoria.TRANSFERENCIA_INTERNA,
        Categoria.OTRO_EGRESO,
    }
    CATEGORIAS_OTRO = {Categoria.OTRO_INGRESO, Categoria.OTRO_EGRESO}

    class Origen(models.TextChoices):
        MANUAL = "MANUAL", "Manual"

    movimiento = models.ForeignKey(
        MovimientoBancario,
        on_delete=models.PROTECT,
        related_name="clasificaciones",
    )
    categoria = models.CharField(max_length=40, choices=Categoria.choices)
    contraparte_normalizada = models.CharField(max_length=200, blank=True)
    rut_contraparte_normalizado = models.CharField(max_length=20, blank=True)
    observacion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    origen = models.CharField(
        max_length=20, choices=Origen.choices, default=Origen.MANUAL
    )
    clasificado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clasificaciones_movimiento",
    )
    clasificado_en = models.DateTimeField(default=timezone.now)
    clasificacion_anterior = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reclasificaciones",
    )

    class Meta:
        db_table = "adm_clasificacion_movimiento_bancario"
        ordering = ["-clasificado_en", "-id"]
        verbose_name = "Clasificación de movimiento bancario"
        verbose_name_plural = "Clasificaciones de movimientos bancarios"
        constraints = [
            models.UniqueConstraint(
                fields=["movimiento"],
                condition=Q(activa=True),
                name="uniq_adm_clasificacion_activa",
            ),
        ]
        indexes = [
            models.Index(fields=["categoria"]),
            models.Index(fields=["activa"]),
        ]

    def __str__(self):
        estado = "activa" if self.activa else "histórica"
        return f"{self.get_categoria_display()} ({estado}) ← mov {self.movimiento_id}"

    @classmethod
    def categorias_para_tipo(cls, tipo_movimiento: str):
        if tipo_movimiento == MovimientoBancario.Tipo.INGRESO:
            return [
                (c.value, c.label)
                for c in cls.Categoria
                if c.value in cls.CATEGORIAS_INGRESO
            ]
        if tipo_movimiento == MovimientoBancario.Tipo.EGRESO:
            return [
                (c.value, c.label)
                for c in cls.Categoria
                if c.value in cls.CATEGORIAS_EGRESO
            ]
        return []

    def clean(self):
        if not self.movimiento_id:
            return
        tipo = self.movimiento.tipo
        validas = {c for c, _ in self.categorias_para_tipo(tipo)}
        if self.categoria and self.categoria not in validas:
            raise ValidationError(
                {
                    "categoria": (
                        f"La categoría {self.categoria} no es compatible "
                        f"con un movimiento de tipo {tipo}."
                    )
                }
            )
        if self.categoria in self.CATEGORIAS_OTRO and not (
            self.observacion or ""
        ).strip():
            raise ValidationError(
                {"observacion": "Las categorías «OTRO» requieren observación."}
            )


class ConciliacionBancaria(ModeloAuditoria):
    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        CERRADA = "CERRADA", "Cerrada"
        ANULADA = "ANULADA", "Anulada"

    cuenta_bancaria = models.ForeignKey(
        CuentaBancaria, on_delete=models.PROTECT, related_name="conciliaciones"
    )
    periodo_desde = models.DateField()
    periodo_hasta = models.DateField()
    saldo_libro = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    saldo_banco = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    diferencia = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ABIERTA
    )
    cerrado_en = models.DateTimeField(null=True, blank=True)
    cerrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conciliaciones_cerradas",
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_conciliacion_bancaria"
        ordering = ["-periodo_hasta"]
        verbose_name = "Conciliación bancaria"
        verbose_name_plural = "Conciliaciones bancarias"
        constraints = [
            models.CheckConstraint(
                check=Q(periodo_hasta__gte=models.F("periodo_desde")),
                name="chk_adm_conciliacion_rango",
            ),
        ]

    def __str__(self):
        return (
            f"Conciliación {self.cuenta_bancaria} "
            f"{self.periodo_desde} → {self.periodo_hasta}"
        )


class ExclusionMovimientoBancario(ModeloAuditoria):
    movimiento = models.OneToOneField(
        MovimientoBancario,
        on_delete=models.PROTECT,
        related_name="exclusion",
    )
    motivo = models.TextField()
    excluido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exclusiones_movimiento",
    )
    excluido_en = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "adm_exclusion_movimiento_bancario"
        verbose_name = "Exclusión de movimiento bancario"
        verbose_name_plural = "Exclusiones de movimientos bancarios"

    def __str__(self):
        return f"Exclusión movimiento {self.movimiento_id}"

    def clean(self):
        if not self.motivo or not self.motivo.strip():
            raise ValidationError({"motivo": "Debe indicar un motivo de exclusión."})


# ===========================================================================
# FACTURACIÓN, COBRANZA Y FACTORING
# ===========================================================================

class FacturaVenta(ModeloAuditoria):
    class EstadoDocumental(models.TextChoices):
        EMITIDA = "EMITIDA", "Emitida"
        ANULADA = "ANULADA", "Anulada"
        NOTA_CREDITO = "NOTA_CREDITO", "Nota de crédito"

    class EstadoCobranza(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        VENCIDA = "VENCIDA", "Vencida"
        PARCIAL = "PARCIAL", "Pagada parcialmente"
        PAGADA = "PAGADA", "Pagada"
        CEDIDA_FACTORING = "CEDIDA_FACTORING", "Cedida a factoring"
        ANULADA = "ANULADA", "Anulada"

    cliente = models.ForeignKey(
        "extintores.Cliente",
        on_delete=models.PROTECT,
        related_name="facturas_venta",
    )
    numero = models.PositiveIntegerField()
    orden_compra = models.CharField(max_length=80, blank=True)
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    contacto = models.CharField(max_length=150, blank=True)
    correo = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    neto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    tasa_iva = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal("0.1900")
    )
    iva = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estado_documental = models.CharField(
        max_length=20,
        choices=EstadoDocumental.choices,
        default=EstadoDocumental.EMITIDA,
    )
    estado_cobranza = models.CharField(
        max_length=20,
        choices=EstadoCobranza.choices,
        default=EstadoCobranza.PENDIENTE,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_factura_venta"
        ordering = ["-fecha_emision", "-numero"]
        verbose_name = "Factura de venta"
        verbose_name_plural = "Facturas de venta"
        constraints = [
            models.UniqueConstraint(
                fields=["numero"],
                name="uniq_adm_factura_numero",
            ),
            models.CheckConstraint(
                check=Q(total__gt=0),
                name="chk_adm_factura_total_positivo",
            ),
        ]
        indexes = [
            models.Index(fields=["estado_cobranza"]),
            models.Index(fields=["fecha_emision"]),
            models.Index(fields=["fecha_vencimiento"]),
        ]

    def __str__(self):
        return f"Factura {self.numero} — {self.cliente}"

    @property
    def monto_pagado(self):
        total = self.aplicaciones_pago.filter(
            estado=AplicacionPagoFactura.Estado.APLICADA
        ).aggregate(t=Sum("monto"))["t"]
        return total or Decimal("0.00")

    @property
    def saldo_pendiente(self):
        return max(self.total - self.monto_pagado, Decimal("0.00"))

    @property
    def dias_vencida(self):
        if not self.fecha_vencimiento:
            return 0
        if self.saldo_pendiente <= 0:
            return 0
        hoy = timezone.localdate()
        if hoy <= self.fecha_vencimiento:
            return 0
        return (hoy - self.fecha_vencimiento).days

    @property
    def estado_cobranza_calculado(self):
        if self.estado_documental == self.EstadoDocumental.ANULADA:
            return self.EstadoCobranza.ANULADA
        try:
            op = self.operacion_factoring
        except OperacionFactoring.DoesNotExist:
            op = None
        if op is not None and op.estado not in (
            OperacionFactoring.Estado.CERRADA,
            OperacionFactoring.Estado.ANULADA,
        ):
            return self.EstadoCobranza.CEDIDA_FACTORING
        pagado = self.monto_pagado
        if pagado <= 0:
            if self.fecha_vencimiento and timezone.localdate() > self.fecha_vencimiento:
                return self.EstadoCobranza.VENCIDA
            return self.EstadoCobranza.PENDIENTE
        if pagado < self.total:
            return self.EstadoCobranza.PARCIAL
        return self.EstadoCobranza.PAGADA

    def actualizar_estado_cobranza(self, guardar=True):
        nuevo = self.estado_cobranza_calculado
        if self.estado_cobranza != nuevo:
            self.estado_cobranza = nuevo
            if guardar:
                self.save(update_fields=["estado_cobranza", "actualizado_en"])
        return nuevo


class GestionCobranza(ModeloAuditoria):
    class TipoContacto(models.TextChoices):
        LLAMADA = "LLAMADA", "Llamada"
        CORREO = "CORREO", "Correo"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        VISITA = "VISITA", "Visita"
        OTRO = "OTRO", "Otro"

    factura = models.ForeignKey(
        FacturaVenta, on_delete=models.CASCADE, related_name="gestiones_cobranza"
    )
    fecha = models.DateTimeField(default=timezone.now)
    tipo_contacto = models.CharField(
        max_length=20, choices=TipoContacto.choices, default=TipoContacto.CORREO
    )
    contacto = models.CharField(max_length=150, blank=True)
    mensaje = models.TextField(blank=True)
    respuesta = models.TextField(blank=True)
    proximo_contacto = models.DateField(null=True, blank=True)
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gestiones_cobranza",
    )

    class Meta:
        db_table = "adm_gestion_cobranza"
        ordering = ["-fecha"]
        verbose_name = "Gestión de cobranza"
        verbose_name_plural = "Gestiones de cobranza"

    def __str__(self):
        return f"Gestión factura {self.factura.numero} — {self.fecha:%Y-%m-%d}"


class EmpresaFactoring(ModeloAuditoria):
    nombre = models.CharField(max_length=150, unique=True)
    rut = models.CharField(max_length=20, blank=True)
    correo = models.CharField(max_length=150, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    activa = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_empresa_factoring"
        ordering = ["nombre"]
        verbose_name = "Empresa de factoring"
        verbose_name_plural = "Empresas de factoring"

    def __str__(self):
        return self.nombre


class OperacionFactoring(ModeloAuditoria):
    class Estado(models.TextChoices):
        CEDIDA = "CEDIDA", "Cedida"
        ANTICIPADA = "ANTICIPADA", "Anticipada"
        POR_COBRAR_CLIENTE = "POR_COBRAR_CLIENTE", "Por cobrar al cliente"
        CLIENTE_PAGO_FACTOR = "CLIENTE_PAGO_FACTOR", "Cliente pagó al factor"
        FACTOR_DEBE_LIQUIDAR = "FACTOR_DEBE_LIQUIDAR", "Factor debe liquidar a ER"
        LIQUIDADA = "LIQUIDADA", "Liquidada"
        EN_MORA = "EN_MORA", "En mora"
        COBRO_RECURSO = "COBRO_RECURSO", "Cobro con recurso"
        CERRADA = "CERRADA", "Cerrada"
        ANULADA = "ANULADA", "Anulada"

    factura = models.OneToOneField(
        FacturaVenta,
        on_delete=models.PROTECT,
        related_name="operacion_factoring",
    )
    empresa_factoring = models.ForeignKey(
        EmpresaFactoring,
        on_delete=models.PROTECT,
        related_name="operaciones",
    )
    fecha_cesion = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    con_recurso = models.BooleanField(default=True)
    monto_cedido = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    monto_anticipo = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    comision = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    retencion = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    fecha_pago_cliente_factor = models.DateField(null=True, blank=True)
    fecha_liquidacion = models.DateField(null=True, blank=True)
    fecha_notificacion_mora = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.CEDIDA,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_operacion_factoring"
        ordering = ["-fecha_cesion"]
        verbose_name = "Operación de factoring"
        verbose_name_plural = "Operaciones de factoring"

    def __str__(self):
        return f"Factoring factura {self.factura.numero} — {self.estado}"


class EventoFactoring(ModeloAuditoria):
    class Tipo(models.TextChoices):
        FACTURA_CEDIDA = "FACTURA_CEDIDA", "Factura cedida"
        ANTICIPO_RECIBIDO = "ANTICIPO_RECIBIDO", "Anticipo recibido"
        FACTOR_NOTIFICA_MORA = "FACTOR_NOTIFICA_MORA", "Factor notifica mora"
        CLIENTE_CONTACTADO = "CLIENTE_CONTACTADO", "Cliente contactado"
        CLIENTE_PAGO_FACTOR = "CLIENTE_PAGO_FACTOR", "Cliente pagó al factor"
        FACTOR_DEBE_PAGAR_ER = "FACTOR_DEBE_PAGAR_ER", "Factor debe pagar a ER"
        COBRO_CON_RECURSO = "COBRO_CON_RECURSO", "Cobro con recurso"
        LIQUIDACION = "LIQUIDACION", "Liquidación"
        OTRO = "OTRO", "Otro"

    operacion = models.ForeignKey(
        OperacionFactoring, on_delete=models.CASCADE, related_name="eventos"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fecha = models.DateTimeField(default=timezone.now)
    detalle = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_factoring",
    )

    class Meta:
        db_table = "adm_evento_factoring"
        ordering = ["-fecha"]
        verbose_name = "Evento de factoring"
        verbose_name_plural = "Eventos de factoring"

    def __str__(self):
        return f"{self.get_tipo_display()} — op {self.operacion_id}"


class FlujoFactoring(ModeloAuditoria):
    class Tipo(models.TextChoices):
        ANTICIPO = "ANTICIPO", "Anticipo"
        LIQUIDACION = "LIQUIDACION", "Liquidación"
        COMISION = "COMISION", "Comisión"
        RETENCION = "RETENCION", "Retención"
        COBRO_RECURSO = "COBRO_RECURSO", "Cobro con recurso"
        OTRO = "OTRO", "Otro"

    class Direccion(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"

    operacion = models.ForeignKey(
        OperacionFactoring, on_delete=models.PROTECT, related_name="flujos"
    )
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    direccion = models.CharField(max_length=10, choices=Direccion.choices)
    fecha = models.DateField()
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    referencia = models.CharField(max_length=120, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_flujo_factoring"
        ordering = ["-fecha", "-id"]
        verbose_name = "Flujo de factoring"
        verbose_name_plural = "Flujos de factoring"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_flujo_factoring_monto",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} {self.direccion} {self.monto}"


class PagoCliente(ModeloAuditoria):
    class Receptor(models.TextChoices):
        EXTINTORES_REAL = "EXTINTORES_REAL", "Extintores Real"
        FACTORING = "FACTORING", "Factoring"

    class FormaPago(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        DEBITO = "DEBITO", "Débito"
        EFECTIVO = "EFECTIVO", "Efectivo"
        CHEQUE = "CHEQUE", "Cheque"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        REGISTRADO = "REGISTRADO", "Registrado"
        PARCIAL = "PARCIAL", "Parcialmente aplicado"
        APLICADO = "APLICADO", "Aplicado"
        ANULADO = "ANULADO", "Anulado"

    cliente = models.ForeignKey(
        "extintores.Cliente",
        on_delete=models.PROTECT,
        related_name="pagos_cliente",
    )
    fecha = models.DateField()
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    receptor = models.CharField(
        max_length=20,
        choices=Receptor.choices,
        default=Receptor.EXTINTORES_REAL,
    )
    forma_pago = models.CharField(
        max_length=20,
        choices=FormaPago.choices,
        default=FormaPago.TRANSFERENCIA,
    )
    referencia = models.CharField(max_length=120, blank=True)
    operacion_factoring = models.ForeignKey(
        OperacionFactoring,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pagos_recibidos_factor",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.REGISTRADO
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_pago_cliente"
        ordering = ["-fecha", "-id"]
        verbose_name = "Pago de cliente"
        verbose_name_plural = "Pagos de clientes"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_pago_cliente_monto",
            ),
        ]

    def __str__(self):
        return f"Pago {self.monto} — {self.cliente} ({self.fecha})"

    @property
    def monto_aplicado(self):
        total = self.aplicaciones.exclude(
            estado=AplicacionPagoFactura.Estado.ANULADA
        ).aggregate(t=Sum("monto"))["t"]
        return total or Decimal("0.00")

    @property
    def saldo_sin_aplicar(self):
        return self.monto - self.monto_aplicado


class AplicacionPagoFactura(ModeloAuditoria):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APLICADA = "APLICADA", "Aplicada"
        PAGO_ERRONEO_FACTORING = (
            "PAGO_ERRONEO_FACTORING",
            "Pago erróneo (factura cedida)",
        )
        ANULADA = "ANULADA", "Anulada"

    pago = models.ForeignKey(
        PagoCliente, on_delete=models.PROTECT, related_name="aplicaciones"
    )
    factura = models.ForeignKey(
        FacturaVenta, on_delete=models.PROTECT, related_name="aplicaciones_pago"
    )
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estado = models.CharField(
        max_length=30, choices=Estado.choices, default=Estado.APLICADA
    )
    fecha_aplicacion = models.DateField(default=timezone.localdate)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_aplicacion_pago_factura"
        ordering = ["-fecha_aplicacion", "-id"]
        verbose_name = "Aplicación de pago a factura"
        verbose_name_plural = "Aplicaciones de pago a facturas"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_aplicacion_pago_monto",
            ),
        ]

    def __str__(self):
        return f"${self.monto} → factura {self.factura.numero}"

    def clean(self):
        errors = {}
        if self.pago_id and self.factura_id:
            if self.pago.cliente_id != self.factura.cliente_id:
                errors["factura"] = (
                    "La factura debe pertenecer al mismo cliente del pago."
                )
            otras = self.pago.aplicaciones.exclude(
                pk=self.pk
            ).exclude(estado=self.Estado.ANULADA)
            total_otras = otras.aggregate(t=Sum("monto"))["t"] or Decimal("0")
            if total_otras + self.monto > self.pago.monto:
                errors["monto"] = (
                    "La suma de aplicaciones supera el monto del pago."
                )
            if self.estado == self.Estado.APLICADA:
                otras_fac = self.factura.aplicaciones_pago.exclude(
                    pk=self.pk
                ).filter(estado=self.Estado.APLICADA)
                total_fac = otras_fac.aggregate(t=Sum("monto"))["t"] or Decimal("0")
                if total_fac + self.monto > self.factura.total:
                    errors["monto"] = (
                        "La suma de pagos válidos supera el total de la factura."
                    )
        if errors:
            raise ValidationError(errors)


class DevolucionPagoCliente(ModeloAuditoria):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        COMPLETADA = "COMPLETADA", "Completada"
        ANULADA = "ANULADA", "Anulada"

    pago = models.ForeignKey(
        PagoCliente, on_delete=models.PROTECT, related_name="devoluciones"
    )
    aplicacion_pago = models.ForeignKey(
        AplicacionPagoFactura,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devoluciones",
    )
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    motivo = models.TextField()
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    fecha_solicitud = models.DateField(default=timezone.localdate)
    fecha_completada = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_devolucion_pago_cliente"
        ordering = ["-fecha_solicitud"]
        verbose_name = "Devolución de pago de cliente"
        verbose_name_plural = "Devoluciones de pagos de clientes"

    def __str__(self):
        return f"Devolución ${self.monto} — pago {self.pago_id}"


class AlertaCobranza(ModeloAuditoria):
    class Tipo(models.TextChoices):
        FACTURA_VENCIDA = "FACTURA_VENCIDA", "Factura vencida"
        PAGO_DIRECTO_FACTURA_CEDIDA = (
            "PAGO_DIRECTO_FACTURA_CEDIDA",
            "Pago directo sobre factura cedida",
        )
        FACTORING_VENCIDO = "FACTORING_VENCIDO", "Factoring vencido"
        FACTOR_NOTIFICA_DEUDA = (
            "FACTOR_NOTIFICA_DEUDA",
            "Factor notifica deuda a ER",
        )
        PAGO_SIN_FACTURA = "PAGO_SIN_FACTURA", "Pago sin factura identificada"
        OTRO = "OTRO", "Otro"

    class Severidad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        CRITICA = "CRITICA", "Crítica"

    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        EN_GESTION = "EN_GESTION", "En gestión"
        RESUELTA = "RESUELTA", "Resuelta"
        DESCARTADA = "DESCARTADA", "Descartada"

    tipo = models.CharField(max_length=40, choices=Tipo.choices)
    severidad = models.CharField(
        max_length=10, choices=Severidad.choices, default=Severidad.MEDIA
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.ABIERTA
    )
    titulo = models.CharField(max_length=200)
    detalle = models.TextField(blank=True)
    factura = models.ForeignKey(
        FacturaVenta,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas",
    )
    operacion_factoring = models.ForeignKey(
        OperacionFactoring,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas",
    )
    pago = models.ForeignKey(
        PagoCliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas",
    )
    abierta_en = models.DateTimeField(default=timezone.now)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="alertas_cobranza_resueltas",
    )

    class Meta:
        db_table = "adm_alerta_cobranza"
        ordering = ["-abierta_en"]
        verbose_name = "Alerta de cobranza"
        verbose_name_plural = "Alertas de cobranza"
        indexes = [
            models.Index(fields=["estado", "severidad"]),
            models.Index(fields=["tipo"]),
        ]

    def __str__(self):
        return f"[{self.severidad}] {self.titulo}"


# ===========================================================================
# RENDICIONES
# ===========================================================================

class ResponsableRendicion(ModeloAuditoria):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responsable_rendicion",
    )
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    area = models.CharField(max_length=100, blank=True)
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_responsable_rendicion"
        ordering = ["nombre"]
        verbose_name = "Responsable de rendición"
        verbose_name_plural = "Responsables de rendición"

    def __str__(self):
        return self.nombre


class CategoriaGasto(ModeloAuditoria):
    nombre = models.CharField(max_length=100, unique=True)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "adm_categoria_gasto"
        ordering = ["nombre"]
        verbose_name = "Categoría de gasto"
        verbose_name_plural = "Categorías de gasto"

    def __str__(self):
        return self.nombre


class SubcategoriaGasto(ModeloAuditoria):
    categoria = models.ForeignKey(
        CategoriaGasto, on_delete=models.PROTECT, related_name="subcategorias"
    )
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)

    class Meta:
        db_table = "adm_subcategoria_gasto"
        ordering = ["categoria__nombre", "nombre"]
        verbose_name = "Subcategoría de gasto"
        verbose_name_plural = "Subcategorías de gasto"
        constraints = [
            models.UniqueConstraint(
                fields=["categoria", "nombre"],
                name="uniq_adm_subcategoria_nombre",
            ),
        ]

    def __str__(self):
        return f"{self.categoria.nombre} / {self.nombre}"


class Rendicion(ModeloAuditoria):
    class Estado(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PRESENTADA = "PRESENTADA", "Presentada"
        EN_REVISION = "EN_REVISION", "En revisión"
        OBSERVADA = "OBSERVADA", "Observada"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        LIQUIDADA = "LIQUIDADA", "Liquidada"
        CERRADA = "CERRADA", "Cerrada"
        ANULADA = "ANULADA", "Anulada"

    numero = models.CharField(max_length=40, unique=True)
    responsable = models.ForeignKey(
        ResponsableRendicion,
        on_delete=models.PROTECT,
        related_name="rendiciones",
    )
    periodo_desde = models.DateField()
    periodo_hasta = models.DateField()
    motivo = models.CharField(max_length=200, blank=True)
    lugar_trabajo = models.CharField(max_length=200, blank=True)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.BORRADOR
    )
    fecha_presentacion = models.DateField(null=True, blank=True)
    fecha_aprobacion = models.DateField(null=True, blank=True)
    fecha_cierre = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_rendicion"
        ordering = ["-periodo_hasta", "-id"]
        verbose_name = "Rendición"
        verbose_name_plural = "Rendiciones"
        constraints = [
            models.CheckConstraint(
                check=Q(periodo_hasta__gte=models.F("periodo_desde")),
                name="chk_adm_rendicion_periodo",
            ),
        ]

    def __str__(self):
        return f"Rendición {self.numero} — {self.responsable}"

    @property
    def total_fondos(self):
        total = self.entregas_fondo.filter(anulada=False).aggregate(
            t=Sum("monto")
        )["t"]
        return total or Decimal("0.00")

    @property
    def total_rendido(self):
        total = self.detalles.exclude(
            estado_revision=DetalleRendicion.EstadoRevision.RECHAZADO
        ).aggregate(t=Sum("total"))["t"]
        return total or Decimal("0.00")

    @property
    def total_aprobado(self):
        total = self.detalles.filter(
            estado_revision=DetalleRendicion.EstadoRevision.APROBADO
        ).aggregate(t=Sum("monto_aprobado"))["t"]
        return total or Decimal("0.00")


class EntregaFondo(ModeloAuditoria):
    class FormaEntrega(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        EFECTIVO = "EFECTIVO", "Efectivo"
        GIRO_CAJERO = "GIRO_CAJERO", "Giro de cajero"
        DEBITO = "DEBITO", "Débito"
        OTRO = "OTRO", "Otro"

    rendicion = models.ForeignKey(
        Rendicion, on_delete=models.PROTECT, related_name="entregas_fondo"
    )
    fecha = models.DateField()
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    forma_entrega = models.CharField(
        max_length=20,
        choices=FormaEntrega.choices,
        default=FormaEntrega.TRANSFERENCIA,
    )
    referencia = models.CharField(max_length=120, blank=True)
    anotacion = models.CharField(max_length=200, blank=True)
    anulada = models.BooleanField(default=False)

    class Meta:
        db_table = "adm_entrega_fondo"
        ordering = ["fecha", "id"]
        verbose_name = "Entrega de fondo"
        verbose_name_plural = "Entregas de fondo"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_entrega_fondo_monto",
            ),
        ]

    def __str__(self):
        return f"Fondo ${self.monto} — rendición {self.rendicion.numero}"


class DetalleRendicion(ModeloAuditoria):
    class TipoDocumento(models.TextChoices):
        FACTURA = "FACTURA", "Factura"
        BOLETA = "BOLETA", "Boleta"
        PEAJE = "PEAJE", "Peaje"
        RECIBO = "RECIBO", "Recibo"
        OTRO = "OTRO", "Otro"
        SIN_DOCUMENTO = "SIN_DOCUMENTO", "Sin documento"

    class FormaPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        DEBITO = "DEBITO", "Débito"
        OTRO = "OTRO", "Otro"

    class EstadoRevision(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        OBSERVADO = "OBSERVADO", "Observado"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    rendicion = models.ForeignKey(
        Rendicion, on_delete=models.CASCADE, related_name="detalles"
    )
    fecha = models.DateField()
    tipo_documento = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        default=TipoDocumento.BOLETA,
    )
    numero_documento = models.CharField(max_length=60, blank=True)
    proveedor = models.CharField(max_length=150, blank=True)
    rut_proveedor = models.CharField(max_length=20, blank=True)
    sucursal = models.CharField(max_length=100, blank=True)
    categoria = models.ForeignKey(
        CategoriaGasto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detalles",
    )
    subcategoria = models.ForeignKey(
        SubcategoriaGasto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="detalles",
    )
    descripcion = models.CharField(max_length=255)
    forma_pago = models.CharField(
        max_length=20, choices=FormaPago.choices, default=FormaPago.EFECTIVO
    )
    neto = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    iva = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    estado_revision = models.CharField(
        max_length=20,
        choices=EstadoRevision.choices,
        default=EstadoRevision.PENDIENTE,
    )
    monto_aprobado = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    motivo_observacion = models.TextField(blank=True)
    justificacion_sin_documento = models.TextField(blank=True)
    comprobante = models.FileField(
        upload_to="administracion/rendiciones/%Y/%m/",
        blank=True,
        null=True,
    )

    class Meta:
        db_table = "adm_detalle_rendicion"
        ordering = ["fecha", "id"]
        verbose_name = "Detalle de rendición"
        verbose_name_plural = "Detalles de rendición"
        constraints = [
            models.CheckConstraint(
                check=Q(total__gt=0),
                name="chk_adm_detalle_rendicion_total",
            ),
        ]

    def __str__(self):
        return f"{self.fecha} — {self.descripcion} (${self.total})"

    def clean(self):
        if self.monto_aprobado is not None and self.monto_aprobado > self.total:
            raise ValidationError(
                {"monto_aprobado": "No puede superar el total del detalle."}
            )
        if self.tipo_documento == self.TipoDocumento.SIN_DOCUMENTO:
            if not self.justificacion_sin_documento.strip():
                raise ValidationError(
                    {
                        "justificacion_sin_documento": (
                            "Debe justificar el gasto sin documento."
                        )
                    }
                )


class AprobacionRendicion(ModeloAuditoria):
    class Accion(models.TextChoices):
        PRESENTADA = "PRESENTADA", "Presentada"
        EN_REVISION = "EN_REVISION", "En revisión"
        OBSERVADA = "OBSERVADA", "Observada"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        REABIERTA = "REABIERTA", "Reabierta"

    rendicion = models.ForeignKey(
        Rendicion, on_delete=models.CASCADE, related_name="aprobaciones"
    )
    accion = models.CharField(max_length=20, choices=Accion.choices)
    fecha = models.DateTimeField(default=timezone.now)
    comentario = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="aprobaciones_rendicion",
    )

    class Meta:
        db_table = "adm_aprobacion_rendicion"
        ordering = ["-fecha"]
        verbose_name = "Aprobación de rendición"
        verbose_name_plural = "Aprobaciones de rendición"

    def __str__(self):
        return f"{self.rendicion.numero} → {self.accion}"


class LiquidacionRendicion(ModeloAuditoria):
    class Resultado(models.TextChoices):
        CUADRADA = "CUADRADA", "Cuadrada"
        RESPONSABLE_DEVUELVE = (
            "RESPONSABLE_DEVUELVE",
            "Responsable debe devolver",
        )
        EMPRESA_REEMBOLSA = "EMPRESA_REEMBOLSA", "Empresa debe reembolsar"

    rendicion = models.OneToOneField(
        Rendicion, on_delete=models.PROTECT, related_name="liquidacion"
    )
    fecha = models.DateField(default=timezone.localdate)
    total_fondos_entregados = models.DecimalField(max_digits=14, decimal_places=2)
    total_gastos_aprobados = models.DecimalField(max_digits=14, decimal_places=2)
    diferencia = models.DecimalField(max_digits=14, decimal_places=2)
    resultado = models.CharField(max_length=30, choices=Resultado.choices)
    observaciones = models.TextField(blank=True)
    liquidada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="liquidaciones_rendicion",
    )

    class Meta:
        db_table = "adm_liquidacion_rendicion"
        verbose_name = "Liquidación de rendición"
        verbose_name_plural = "Liquidaciones de rendición"

    def __str__(self):
        return f"Liquidación {self.rendicion.numero} — {self.resultado}"

    @property
    def monto_regularizado(self):
        total = self.pagos.filter(anulado=False).aggregate(t=Sum("monto"))["t"]
        return total or Decimal("0.00")

    @property
    def saldo_por_regularizar(self):
        return abs(self.diferencia) - self.monto_regularizado

    def clean(self):
        esperada = self.total_fondos_entregados - self.total_gastos_aprobados
        if self.diferencia != esperada:
            raise ValidationError(
                {
                    "diferencia": (
                        "La diferencia debe ser fondos entregados − gastos aprobados."
                    )
                }
            )
        if self.diferencia == 0 and self.resultado != self.Resultado.CUADRADA:
            raise ValidationError(
                {"resultado": "Con diferencia 0 el resultado debe ser CUADRADA."}
            )
        if self.diferencia > 0 and self.resultado != self.Resultado.RESPONSABLE_DEVUELVE:
            raise ValidationError(
                {
                    "resultado": (
                        "Con diferencia positiva el responsable debe devolver."
                    )
                }
            )
        if self.diferencia < 0 and self.resultado != self.Resultado.EMPRESA_REEMBOLSA:
            raise ValidationError(
                {
                    "resultado": (
                        "Con diferencia negativa la empresa debe reembolsar."
                    )
                }
            )


class PagoLiquidacionRendicion(ModeloAuditoria):
    class Tipo(models.TextChoices):
        DEVOLUCION_RESPONSABLE = (
            "DEVOLUCION_RESPONSABLE",
            "Devolución del responsable",
        )
        REEMBOLSO_EMPRESA = "REEMBOLSO_EMPRESA", "Reembolso de la empresa"

    class FormaPago(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"
        EFECTIVO = "EFECTIVO", "Efectivo"
        DEBITO = "DEBITO", "Débito"
        OTRO = "OTRO", "Otro"

    liquidacion = models.ForeignKey(
        LiquidacionRendicion, on_delete=models.PROTECT, related_name="pagos"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fecha = models.DateField()
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    forma_pago = models.CharField(
        max_length=20,
        choices=FormaPago.choices,
        default=FormaPago.TRANSFERENCIA,
    )
    referencia = models.CharField(max_length=120, blank=True)
    anulado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "adm_pago_liquidacion_rendicion"
        ordering = ["fecha", "id"]
        verbose_name = "Pago de liquidación de rendición"
        verbose_name_plural = "Pagos de liquidación de rendición"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_pago_liquidacion_monto",
            ),
        ]

    def __str__(self):
        return f"{self.tipo} ${self.monto}"

    def clean(self):
        if not self.liquidacion_id:
            return
        otras = self.liquidacion.pagos.exclude(pk=self.pk).filter(anulado=False)
        total_otras = otras.aggregate(t=Sum("monto"))["t"] or Decimal("0")
        if total_otras + self.monto > abs(self.liquidacion.diferencia):
            raise ValidationError(
                {
                    "monto": (
                        "No se puede regularizar más que la diferencia de liquidación."
                    )
                }
            )


# ===========================================================================
# APLICACIÓN DE MOVIMIENTOS BANCARIOS (puente transversal)
# ===========================================================================

class AplicacionMovimientoBancario(ModeloAuditoria):
    """
    Distribuye un movimiento de cartola entre operaciones del sistema.
    Exactamente un destino debe estar informado.
    """

    class Destino(models.TextChoices):
        PAGO_CLIENTE = "PAGO_CLIENTE", "Pago de cliente"
        FLUJO_FACTORING = "FLUJO_FACTORING", "Flujo de factoring"
        ENTREGA_FONDO = "ENTREGA_FONDO", "Entrega de fondo"
        PAGO_LIQUIDACION = "PAGO_LIQUIDACION", "Pago liquidación rendición"
        DEVOLUCION_PAGO = "DEVOLUCION_PAGO", "Devolución de pago cliente"
        OTRO = "OTRO", "Otro"

    movimiento = models.ForeignKey(
        MovimientoBancario,
        on_delete=models.PROTECT,
        related_name="aplicaciones",
    )
    destino = models.CharField(max_length=30, choices=Destino.choices)
    monto = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    activa = models.BooleanField(default=True)
    fecha_aplicacion = models.DateField(default=timezone.localdate)
    glosa = models.CharField(max_length=255, blank=True)

    pago_cliente = models.ForeignKey(
        PagoCliente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones_bancarias",
    )
    flujo_factoring = models.ForeignKey(
        FlujoFactoring,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones_bancarias",
    )
    entrega_fondo = models.ForeignKey(
        EntregaFondo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones_bancarias",
    )
    pago_liquidacion = models.ForeignKey(
        PagoLiquidacionRendicion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones_bancarias",
    )
    devolucion_pago = models.ForeignKey(
        DevolucionPagoCliente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="aplicaciones_bancarias",
    )

    class Meta:
        db_table = "adm_aplicacion_movimiento_bancario"
        ordering = ["-fecha_aplicacion", "-id"]
        verbose_name = "Aplicación de movimiento bancario"
        verbose_name_plural = "Aplicaciones de movimientos bancarios"
        constraints = [
            models.CheckConstraint(
                check=Q(monto__gt=0),
                name="chk_adm_apl_mov_monto",
            ),
        ]

    def __str__(self):
        return f"{self.destino} ${self.monto} ← mov {self.movimiento_id}"

    def _destinos_fk(self):
        return [
            self.pago_cliente_id,
            self.flujo_factoring_id,
            self.entrega_fondo_id,
            self.pago_liquidacion_id,
            self.devolucion_pago_id,
        ]

    def clean(self):
        errors = {}
        destinos = [d for d in self._destinos_fk() if d]
        if self.destino != self.Destino.OTRO and len(destinos) != 1:
            errors["destino"] = (
                "Debe indicar exactamente un destino (o usar OTRO sin FK)."
            )
        if self.destino == self.Destino.OTRO and destinos:
            errors["destino"] = "Destino OTRO no debe tener FKs informadas."

        mapa = {
            self.Destino.PAGO_CLIENTE: self.pago_cliente_id,
            self.Destino.FLUJO_FACTORING: self.flujo_factoring_id,
            self.Destino.ENTREGA_FONDO: self.entrega_fondo_id,
            self.Destino.PAGO_LIQUIDACION: self.pago_liquidacion_id,
            self.Destino.DEVOLUCION_PAGO: self.devolucion_pago_id,
        }
        if self.destino in mapa and not mapa[self.destino]:
            errors[self.destino.lower()] = (
                f"Debe indicar el registro para destino {self.destino}."
            )

        if self.movimiento_id and self.activa:
            otras = self.movimiento.aplicaciones.exclude(pk=self.pk).filter(
                activa=True
            )
            total_otras = otras.aggregate(t=Sum("monto"))["t"] or Decimal("0")
            if total_otras + self.monto > self.movimiento.monto:
                errors["monto"] = (
                    "La suma aplicada supera el monto del movimiento bancario."
                )

            # Dirección esperada según destino
            requiere_ingreso = self.destino in (
                self.Destino.PAGO_CLIENTE,
                self.Destino.FLUJO_FACTORING,
            )
            requiere_egreso = self.destino in (
                self.Destino.ENTREGA_FONDO,
                self.Destino.DEVOLUCION_PAGO,
            )
            if requiere_ingreso and self.flujo_factoring_id:
                if self.flujo_factoring.direccion == FlujoFactoring.Direccion.EGRESO:
                    requiere_ingreso = False
                    requiere_egreso = True
            if (
                requiere_ingreso
                and self.movimiento.tipo != MovimientoBancario.Tipo.INGRESO
            ):
                errors["movimiento"] = (
                    "Este destino requiere un movimiento de ingreso."
                )
            if (
                requiere_egreso
                and self.movimiento.tipo != MovimientoBancario.Tipo.EGRESO
            ):
                errors["movimiento"] = (
                    "Este destino requiere un movimiento de egreso."
                )

        if errors:
            raise ValidationError(errors)

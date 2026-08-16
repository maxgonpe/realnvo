from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# =============================================================================
# UTILIDADES
# =============================================================================

def bytes_legibles(valor):
    """
    Convierte bytes a una representación legible.
    Solo para presentación; la BD siempre guarda bytes enteros.
    """
    if valor is None:
        return "-"

    valor = float(valor)

    unidades = ["B", "KB", "MB", "GB", "TB", "PB"]

    for unidad in unidades:
        if valor < 1024:
            return f"{valor:.2f} {unidad}"
        valor /= 1024

    return f"{valor:.2f} EB"


# =============================================================================
# CONFIGURACIÓN DE RUTAS
# =============================================================================

class RutaMonitoreada(models.Model):
    """
    Directorio que Espaciómetro debe observar.

    IMPORTANTE:
    Este modelo no se relaciona con ninguna otra aplicación Django.

    La ruta puede ser relativa a BASE_DIR o absoluta, permitiendo instalar
    Espaciómetro en otros proyectos sin cambiar sus modelos.
    """

    class Categoria(models.TextChoices):
        DATOS_NEGOCIO = "DATOS_NEGOCIO", "Datos de negocio"
        MEDIA = "MEDIA", "Media / archivos subidos"
        TEMPORAL = "TEMPORAL", "Archivos temporales"
        BACKUP = "BACKUP", "Respaldos"
        REGENERABLE = "REGENERABLE", "Archivos regenerables"
        APLICACION = "APLICACION", "Aplicación / sistema"
        DOCUMENTACION = "DOCUMENTACION", "Documentación"
        OTRO = "OTRO", "Otro"

    nombre = models.CharField(
        max_length=120,
        unique=True,
    )

    ruta = models.CharField(
        max_length=500,
        help_text=(
            "Ruta relativa a BASE_DIR o ruta absoluta, "
            "según relativa_a_base_dir."
        ),
    )

    relativa_a_base_dir = models.BooleanField(
        default=True,
        help_text=(
            "Si está activo, la ruta se resolverá respecto de BASE_DIR."
        ),
    )

    categoria = models.CharField(
        max_length=30,
        choices=Categoria.choices,
        default=Categoria.OTRO,
    )

    recursiva = models.BooleanField(
        default=True,
        help_text="Analizar también subdirectorios.",
    )

    seguir_enlaces_simbolicos = models.BooleanField(
        default=False,
        help_text=(
            "Normalmente debe permanecer desactivado para evitar "
            "recorridos fuera del proyecto o ciclos."
        ),
    )

    patrones_incluir = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Patrones opcionales. Ejemplo: ["*.pdf", "*.jpg"]. '
            "Vacío significa incluir todos."
        ),
    )

    patrones_excluir = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Patrones opcionales. Ejemplo: ["*.tmp", "__pycache__"].'
        ),
    )

    tipos_interes = models.JSONField(
    default=list,
    blank=True,
    help_text=(
        "Categorías de archivo que requieren "
        "monitorización especial."
        ),
    )

    extensiones_interes = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Extensiones específicas que requieren "
            "monitorización especial."
        ),
    )

    activa = models.BooleanField(default=True)

    visible_dashboard = models.BooleanField(
        default=True,
        help_text="Mostrar esta ruta en el dashboard principal.",
    )

    permite_mantenimiento = models.BooleanField(
        default=False,
        help_text=(
            "Indica si posteriormente podrán ofrecerse acciones "
            "de archivado/depuración sobre esta ruta."
        ),
    )

    observaciones = models.TextField(blank=True)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "esp_ruta_monitoreada"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# =============================================================================
# EJECUCIÓN DE MEDICIONES
# =============================================================================

class EjecucionMedicion(models.Model):
    """
    Agrupa una ejecución completa del Espaciómetro.

    Una ejecución podrá contener:
    - medición de disco,
    - medición de rutas,
    - medición de base de datos,
    - medición de tablas.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        PARCIAL = "PARCIAL", "Completada parcialmente"
        ERROR = "ERROR", "Error"

    iniciada_en = models.DateTimeField(default=timezone.now)

    finalizada_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    hostname = models.CharField(
        max_length=255,
        blank=True,
    )

    plataforma = models.CharField(
        max_length=255,
        blank=True,
        help_text="Linux, Windows, etc.",
    )

    version_python = models.CharField(
        max_length=50,
        blank=True,
    )

    errores = models.JSONField(
        default=list,
        blank=True,
    )

    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = "esp_ejecucion_medicion"
        ordering = ["-iniciada_en"]

    def __str__(self):
        return f"Medición {self.pk} — {self.iniciada_en:%Y-%m-%d %H:%M}"


# =============================================================================
# DISCO / FILESYSTEM
# =============================================================================

class MedicionDisco(models.Model):
    """
    Fotografía del espacio físico disponible en un filesystem.
    """

    ejecucion = models.ForeignKey(
        EjecucionMedicion,
        on_delete=models.CASCADE,
        related_name="discos",
    )

    punto_montaje = models.CharField(
        max_length=500,
        default="/",
    )

    dispositivo = models.CharField(
        max_length=255,
        blank=True,
    )

    sistema_archivos = models.CharField(
        max_length=100,
        blank=True,
    )

    total_bytes = models.PositiveBigIntegerField(default=0)

    usados_bytes = models.PositiveBigIntegerField(default=0)

    libres_bytes = models.PositiveBigIntegerField(default=0)

    porcentaje_usado = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
    )

    class Meta:
        db_table = "esp_medicion_disco"
        ordering = ["punto_montaje"]
        constraints = [
            models.UniqueConstraint(
                fields=["ejecucion", "punto_montaje"],
                name="uq_esp_med_disco",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.total_bytes:
            self.porcentaje_usado = round(
                Decimal(self.usados_bytes)
                * Decimal("100")
                / Decimal(self.total_bytes),
                2,
            )
        else:
            self.porcentaje_usado = Decimal("0.00")

        super().save(*args, **kwargs)

    @property
    def total_legible(self):
        return bytes_legibles(self.total_bytes)

    @property
    def usados_legible(self):
        return bytes_legibles(self.usados_bytes)

    @property
    def libres_legible(self):
        return bytes_legibles(self.libres_bytes)

    def __str__(self):
        return (
            f"{self.punto_montaje} — "
            f"{self.porcentaje_usado}% utilizado"
        )


# =============================================================================
# DIRECTORIOS
# =============================================================================

class MedicionRuta(models.Model):
    """
    Resultado agregado de analizar una RutaMonitoreada.

    NO guarda una fila por archivo.
    """

    ejecucion = models.ForeignKey(
        EjecucionMedicion,
        on_delete=models.CASCADE,
        related_name="rutas",
    )

    ruta_monitoreada = models.ForeignKey(
        RutaMonitoreada,
        on_delete=models.PROTECT,
        related_name="mediciones",
    )

    ruta_resuelta = models.CharField(
        max_length=1000,
        blank=True,
    )

    total_bytes = models.PositiveBigIntegerField(default=0)

    total_archivos = models.PositiveBigIntegerField(default=0)

    total_directorios = models.PositiveBigIntegerField(default=0)

    total_enlaces_simbolicos = models.PositiveBigIntegerField(default=0)

    total_imagenes = models.PositiveBigIntegerField(default=0)

    total_pdf = models.PositiveBigIntegerField(default=0)

    total_documentos = models.PositiveBigIntegerField(default=0)

    total_planillas = models.PositiveBigIntegerField(default=0)

    total_videos = models.PositiveBigIntegerField(default=0)

    total_comprimidos = models.PositiveBigIntegerField(default=0)

    total_temporales = models.PositiveBigIntegerField(default=0)

    total_otros = models.PositiveBigIntegerField(default=0)

    archivo_mas_antiguo_fecha = models.DateTimeField(
        null=True,
        blank=True,
    )

    archivo_mas_antiguo_ruta = models.CharField(
        max_length=1000,
        blank=True,
    )

    archivo_mas_reciente_fecha = models.DateTimeField(
        null=True,
        blank=True,
    )

    archivo_mas_reciente_ruta = models.CharField(
        max_length=1000,
        blank=True,
    )

    archivo_mas_grande_bytes = models.PositiveBigIntegerField(
        default=0,
    )

    archivo_mas_grande_ruta = models.CharField(
        max_length=1000,
        blank=True,
    )

    archivos_inaccesibles = models.PositiveBigIntegerField(default=0)

    duracion_ms = models.PositiveBigIntegerField(default=0)

    error = models.TextField(blank=True)

    class Meta:
        db_table = "esp_medicion_ruta"
        ordering = ["-ejecucion__iniciada_en", "ruta_monitoreada__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["ejecucion", "ruta_monitoreada"],
                name="uq_esp_med_ruta",
            ),
        ]
        indexes = [
            models.Index(fields=["total_bytes"]),
            models.Index(fields=["total_archivos"]),
        ]

    @property
    def total_legible(self):
        return bytes_legibles(self.total_bytes)

    def __str__(self):
        return (
            f"{self.ruta_monitoreada.nombre} — "
            f"{bytes_legibles(self.total_bytes)}"
        )


# =============================================================================
# RESUMEN POR TIPO / EXTENSIÓN
# =============================================================================

class ResumenTipoArchivo(models.Model):
    """
    Resumen agregado por extensión dentro de una medición.

    Ejemplo:
        .jpg  -> 15.200 archivos -> 8.4 GB
        .pdf  ->  1.240 archivos -> 2.1 GB
    """

    class Categoria(models.TextChoices):
        IMAGEN = "IMAGEN", "Imagen"
        PDF = "PDF", "PDF"
        DOCUMENTO = "DOCUMENTO", "Documento"
        PLANILLA = "PLANILLA", "Planilla"
        VIDEO = "VIDEO", "Video"
        COMPRIMIDO = "COMPRIMIDO", "Comprimido"
        TEMPORAL = "TEMPORAL", "Temporal"
        OTRO = "OTRO", "Otro"

    medicion_ruta = models.ForeignKey(
        MedicionRuta,
        on_delete=models.CASCADE,
        related_name="tipos_archivo",
    )

    categoria = models.CharField(
        max_length=20,
        choices=Categoria.choices,
        default=Categoria.OTRO,
    )

    extension = models.CharField(
        max_length=30,
        blank=True,
        help_text="Ejemplo: .jpg, .pdf, .xlsx",
    )

    cantidad = models.PositiveBigIntegerField(default=0)

    total_bytes = models.PositiveBigIntegerField(default=0)

    archivo_mas_antiguo_fecha = models.DateTimeField(
        null=True,
        blank=True,
    )

    archivo_mas_reciente_fecha = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "esp_resumen_tipo_archivo"
        ordering = ["-total_bytes"]
        constraints = [
            models.UniqueConstraint(
                fields=["medicion_ruta", "categoria", "extension"],
                name="uq_esp_tipo_archivo",
            ),
        ]

    @property
    def total_legible(self):
        return bytes_legibles(self.total_bytes)

    def __str__(self):
        extension = self.extension or "sin extensión"
        return f"{extension} — {self.cantidad} archivos"


# =============================================================================
# BASE DE DATOS
# =============================================================================

class MedicionBaseDatos(models.Model):
    """
    Información genérica de una conexión Django.

    Compatible conceptualmente con SQLite y PostgreSQL.

    No guarda contraseña ni credenciales.
    """

    ejecucion = models.ForeignKey(
        EjecucionMedicion,
        on_delete=models.CASCADE,
        related_name="bases_datos",
    )

    alias = models.CharField(
        max_length=100,
        default="default",
    )

    vendor = models.CharField(
        max_length=50,
        blank=True,
        help_text="sqlite, postgresql, mysql, etc.",
    )

    engine = models.CharField(
        max_length=255,
        blank=True,
    )

    nombre_base_datos = models.CharField(
        max_length=500,
        blank=True,
    )

    host = models.CharField(
        max_length=255,
        blank=True,
    )

    puerto = models.CharField(
        max_length=20,
        blank=True,
    )

    total_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    total_tablas = models.PositiveIntegerField(default=0)

    total_registros = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    error = models.TextField(blank=True)

    class Meta:
        db_table = "esp_medicion_bd"
        ordering = ["alias"]
        constraints = [
            models.UniqueConstraint(
                fields=["ejecucion", "alias"],
                name="uq_esp_med_bd",
            ),
        ]

    @property
    def total_legible(self):
        return bytes_legibles(self.total_bytes)

    def __str__(self):
        return f"{self.alias} — {self.vendor or 'BD'}"


class MedicionTabla(models.Model):
    """
    Estadística genérica de tablas.

    Los campos de tamaño pueden quedar NULL cuando el motor no pueda
    entregar esa información de manera fiable.
    """

    medicion_bd = models.ForeignKey(
        MedicionBaseDatos,
        on_delete=models.CASCADE,
        related_name="tablas",
    )

    esquema = models.CharField(
        max_length=120,
        blank=True,
    )

    nombre_tabla = models.CharField(
        max_length=255,
    )

    total_registros = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    datos_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    indices_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    total_bytes = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "esp_medicion_tabla"
        ordering = ["-total_bytes", "nombre_tabla"]
        constraints = [
            models.UniqueConstraint(
                fields=["medicion_bd", "esquema", "nombre_tabla"],
                name="uq_esp_med_tabla",
            ),
        ]
        indexes = [
            models.Index(fields=["nombre_tabla"]),
            models.Index(fields=["total_registros"]),
        ]

    def __str__(self):
        if self.esquema:
            return f"{self.esquema}.{self.nombre_tabla}"
        return self.nombre_tabla


# =============================================================================
# UMBRALES
# =============================================================================

class UmbralAlerta(models.Model):
    """
    Regla genérica de alerta.

    No depende de ningún modelo externo.

    Ejemplos:
        DISCO / "/" / PORCENTAJE_USADO / >= / 80
        RUTA / "intervenciones" / TAMANO_BYTES / >= / ...
    """

    class TipoObjetivo(models.TextChoices):
        DISCO = "DISCO", "Disco"
        RUTA = "RUTA", "Ruta"
        BASE_DATOS = "BASE_DATOS", "Base de datos"
        TABLA = "TABLA", "Tabla"

    class Nivel(models.TextChoices):
        INFORMATIVO = "INFORMATIVO", "Informativo"
        ADVERTENCIA = "ADVERTENCIA", "Advertencia"
        CRITICO = "CRITICO", "Crítico"

    class Operador(models.TextChoices):
        MAYOR_IGUAL = "GTE", "Mayor o igual"
        MENOR_IGUAL = "LTE", "Menor o igual"
        MAYOR = "GT", "Mayor"
        MENOR = "LT", "Menor"

    class Unidad(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje"
        BYTES = "BYTES", "Bytes"
        ARCHIVOS = "ARCHIVOS", "Cantidad de archivos"
        REGISTROS = "REGISTROS", "Cantidad de registros"

    nombre = models.CharField(max_length=150)

    tipo_objetivo = models.CharField(
        max_length=20,
        choices=TipoObjetivo.choices,
    )

    identificador = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Ejemplo: /, intervenciones, default, adm_factura_venta."
        ),
    )

    metrica = models.CharField(
        max_length=100,
        help_text=(
            "Ejemplo: porcentaje_usado, total_bytes, total_registros."
        ),
    )

    operador = models.CharField(
        max_length=5,
        choices=Operador.choices,
        default=Operador.MAYOR_IGUAL,
    )

    valor = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )

    unidad = models.CharField(
        max_length=20,
        choices=Unidad.choices,
    )

    nivel = models.CharField(
        max_length=20,
        choices=Nivel.choices,
        default=Nivel.ADVERTENCIA,
    )

    activa = models.BooleanField(default=True)

    observaciones = models.TextField(blank=True)

    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "esp_umbral_alerta"
        ordering = ["tipo_objetivo", "nivel", "nombre"]

    def __str__(self):
        return self.nombre


# =============================================================================
# FUTURAS OPERACIONES DE MANTENIMIENTO
# =============================================================================

class OperacionMantenimiento(models.Model):
    """
    Auditoría de las acciones que Espaciómetro realice en el futuro.

    No apunta a archivos ni modelos externos mediante ForeignKey.
    """

    class Tipo(models.TextChoices):
        EXPORTAR_ARCHIVOS = "EXPORTAR_ARCHIVOS", "Exportar archivos"
        ARCHIVAR_ARCHIVOS = "ARCHIVAR_ARCHIVOS", "Archivar archivos"
        ELIMINAR_TEMPORALES = (
            "ELIMINAR_TEMPORALES",
            "Eliminar archivos temporales",
        )
        HISTORIZAR_BD = "HISTORIZAR_BD", "Historizar registros"
        DEPURAR_BD = "DEPURAR_BD", "Depurar registros"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        PREPARADA = "PREPARADA", "Preparada"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"
        ERROR = "ERROR", "Error"

    tipo = models.CharField(
        max_length=30,
        choices=Tipo.choices,
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PREPARADA,
    )

    tipo_objetivo = models.CharField(
        max_length=50,
        blank=True,
        help_text="RUTA, TABLA, TEMPORALES, etc.",
    )

    identificador_objetivo = models.CharField(
        max_length=1000,
        blank=True,
        help_text=(
            "Ruta, nombre de tabla u otro identificador textual."
        ),
    )

    criterios = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Ejemplo: fecha_hasta, extensiones, antigüedad, filtros."
        ),
    )

    usuario = models.CharField(
        max_length=150,
        blank=True,
        help_text=(
            "Nombre/username informativo. No es FK para mantener "
            "la independencia de la app."
        ),
    )

    bytes_estimados = models.PositiveBigIntegerField(default=0)

    bytes_liberados = models.PositiveBigIntegerField(default=0)

    registros_afectados = models.PositiveBigIntegerField(default=0)

    creada_en = models.DateTimeField(auto_now_add=True)

    iniciada_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    finalizada_en = models.DateTimeField(
        null=True,
        blank=True,
    )

    resultado = models.JSONField(
        default=dict,
        blank=True,
    )

    error = models.TextField(blank=True)

    class Meta:
        db_table = "esp_operacion_mantenimiento"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.estado}"

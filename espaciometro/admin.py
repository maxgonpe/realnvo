from django.contrib import admin

from .models import (
    RutaMonitoreada,
    EjecucionMedicion,
    MedicionDisco,
    MedicionRuta,
    ResumenTipoArchivo,
    MedicionBaseDatos,
    MedicionTabla,
    UmbralAlerta,
    OperacionMantenimiento,
    LoteCandidatosMantenimiento,
    CandidatoMantenimiento,
    RespaldoMantenimiento,
    DetalleRespaldoMantenimiento,
    RegistroDescargaRespaldo,
    LiberacionMantenimiento,
    DetalleLiberacionMantenimiento,
)


# =============================================================================
# MODELOS EXISTENTES DE ESPACIÓMETRO
# =============================================================================
#
# Los mantenemos registrados de forma simple.
#
# No imponemos aquí nombres de campos específicos para conservar
# compatibilidad con la estructura real existente del proyecto.
# =============================================================================


admin.site.register(
    RutaMonitoreada
)

admin.site.register(
    EjecucionMedicion
)

admin.site.register(
    MedicionDisco
)

admin.site.register(
    MedicionRuta
)

admin.site.register(
    ResumenTipoArchivo
)

admin.site.register(
    MedicionBaseDatos
)

admin.site.register(
    MedicionTabla
)

admin.site.register(
    UmbralAlerta
)

admin.site.register(
    OperacionMantenimiento
)


# =============================================================================
# ESP012 — CANDIDATOS DENTRO DEL LOTE
# =============================================================================


class CandidatoMantenimientoInline(
    admin.TabularInline
):

    model = CandidatoMantenimiento

    extra = 0

    can_delete = False

    show_change_link = True

    fields = (
        "ruta_monitoreada",
        "ruta_relativa",
        "nombre",
        "categoria",
        "extension",
        "total_bytes_snapshot",
        "modificado_snapshot",
    )

    readonly_fields = (
        "ruta_monitoreada",
        "ruta_relativa",
        "nombre",
        "categoria",
        "extension",
        "total_bytes_snapshot",
        "modificado_snapshot",
    )


# =============================================================================
# ESP012 — LOTES
# =============================================================================


@admin.register(
    LoteCandidatosMantenimiento
)
class LoteCandidatosMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "nombre",
        "estado",
        "total_archivos",
        "espacio_legible",
        "creado_por",
        "creado_en",
    )

    list_filter = (
        "estado",
        "creado_en",
    )

    search_fields = (
        "nombre",
        "creado_por",
    )

    ordering = (
        "-creado_en",
        "-id",
    )

    readonly_fields = (
        "total_archivos",
        "total_bytes",
        "creado_en",
    )

    inlines = (
        CandidatoMantenimientoInline,
    )


    @admin.display(
        description="Espacio"
    )
    def espacio_legible(
        self,
        obj,
    ):

        return obj.total_legible


# =============================================================================
# ESP012 — CANDIDATOS INDIVIDUALES
# =============================================================================


@admin.register(
    CandidatoMantenimiento
)
class CandidatoMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "lote",
        "ruta_monitoreada",
        "nombre",
        "categoria",
        "extension",
        "espacio_legible",
        "modificado_snapshot",
        "creado_en",
    )

    list_filter = (
        "categoria",
        "extension",
        "ruta_monitoreada",
        "tipo_interes_snapshot",
        "extension_interes_snapshot",
    )

    search_fields = (
        "nombre",
        "ruta_relativa",
        "lote__nombre",
        "ruta_monitoreada__nombre",
    )

    ordering = (
        "-creado_en",
        "-id",
    )

    readonly_fields = (
        "lote",
        "ruta_monitoreada",
        "ruta_relativa",
        "nombre",
        "categoria",
        "extension",
        "total_bytes_snapshot",
        "mtime_ns_snapshot",
        "inode_snapshot",
        "dispositivo_snapshot",
        "modificado_snapshot",
        "tipo_interes_snapshot",
        "extension_interes_snapshot",
        "creado_en",
    )


    @admin.display(
        description="Espacio"
    )
    def espacio_legible(
        self,
        obj,
    ):

        return obj.total_legible


# =============================================================================
# ESP013
# =============================================================================


@admin.register(
    RespaldoMantenimiento
)
class RespaldoMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "lote",
        "estado",
        "incluidos",
        "omitidos",
        "contenido_legible",
        "paquete_legible",
        "creado_por",
        "creado_en",
    )

    list_filter = (
        "estado",
        "creado_en",
    )

    search_fields = (
        "lote__nombre",
        "nombre_archivo",
        "sha256",
    )

    readonly_fields = (
        "lote",
        "estado",
        "creado_por",
        "nombre_archivo",
        "ruta_relativa_archivo",
        "total_candidatos",
        "incluidos",
        "omitidos",
        "total_bytes_contenido",
        "total_bytes_paquete",
        "sha256",
        "manifest",
        "errores",
        "creado_en",
        "finalizado_en",
    )



@admin.register(
    DetalleRespaldoMantenimiento
)
class DetalleRespaldoMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "respaldo",
        "candidato",
        "estado",
        "estado_validacion",
        "total_legible",
    )

    list_filter = (
        "estado",
        "estado_validacion",
    )

    search_fields = (
        "candidato__nombre",
        "candidato__ruta_relativa",
        "sha256",
    )

    readonly_fields = (
        "respaldo",
        "candidato",
        "estado",
        "estado_validacion",
        "motivo",
        "ruta_zip",
        "total_bytes",
        "sha256",
        "creado_en",
    )

# =============================================================================
# ESP014
# =============================================================================


@admin.register(
    RegistroDescargaRespaldo
)
class RegistroDescargaRespaldoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "respaldo",
        "usuario",
        "estado",
        "total_legible",
        "iniciada_en",
        "confirmada_en",
    )

    list_filter = (
        "estado",
        "iniciada_en",
    )

    search_fields = (
        "usuario",
        "respaldo__nombre_archivo",
        "sha256_esperado",
        "sha256_cliente",
    )

    readonly_fields = (
        "respaldo",
        "usuario",
        "estado",
        "sha256_esperado",
        "sha256_servidor",
        "sha256_cliente",
        "total_bytes",
        "ip_cliente",
        "user_agent",
        "detalle",
        "iniciada_en",
        "confirmada_en",
    )

# =============================================================================
# ESP015
# =============================================================================


@admin.register(
    LiberacionMantenimiento
)
class LiberacionMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "lote",
        "respaldo",
        "estado",
        "usuario",
        "liberados",
        "omitidos",
        "liberado_legible",
        "iniciado_en",
        "finalizado_en",
    )

    list_filter = (
        "estado",
        "iniciado_en",
    )

    search_fields = (
        "lote__nombre",
        "usuario",
        "confirmacion",
    )

    readonly_fields = (
        "lote",
        "respaldo",
        "descarga_verificada",
        "estado",
        "usuario",
        "total_candidatos",
        "liberados",
        "omitidos",
        "total_bytes_objetivo",
        "total_bytes_liberados",
        "confirmacion",
        "errores",
        "iniciado_en",
        "finalizado_en",
    )



@admin.register(
    DetalleLiberacionMantenimiento
)
class DetalleLiberacionMantenimientoAdmin(
    admin.ModelAdmin
):

    list_display = (
        "id",
        "liberacion",
        "candidato",
        "estado",
        "total_legible",
        "liberado_en",
    )

    list_filter = (
        "estado",
        "creado_en",
    )

    search_fields = (
        "candidato__nombre",
        "ruta_relativa",
    )

    readonly_fields = (
        "liberacion",
        "candidato",
        "estado",
        "ruta_relativa",
        "total_bytes_snapshot",
        "motivo",
        "liberado_en",
        "creado_en",
    )
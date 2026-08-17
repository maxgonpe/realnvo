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
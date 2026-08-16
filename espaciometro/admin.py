from django.contrib import admin

from .models import (
    EjecucionMedicion,
    MedicionBaseDatos,
    MedicionDisco,
    MedicionRuta,
    MedicionTabla,
    OperacionMantenimiento,
    ResumenTipoArchivo,
    RutaMonitoreada,
    UmbralAlerta,
    bytes_legibles,
)


@admin.register(RutaMonitoreada)
class RutaMonitoreadaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "ruta",
        "categoria",
        "recursiva",
        "activa",
        "visible_dashboard",
        "permite_mantenimiento",
    )

    list_filter = (
        "categoria",
        "recursiva",
        "activa",
        "visible_dashboard",
        "permite_mantenimiento",
    )

    search_fields = (
        "nombre",
        "ruta",
        "observaciones",
    )


@admin.register(EjecucionMedicion)
class EjecucionMedicionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "iniciada_en",
        "finalizada_en",
        "estado",
        "hostname",
        "plataforma",
    )

    list_filter = (
        "estado",
        "iniciada_en",
    )

    search_fields = (
        "hostname",
        "plataforma",
        "observaciones",
    )

    readonly_fields = (
        "iniciada_en",
    )


@admin.register(MedicionDisco)
class MedicionDiscoAdmin(admin.ModelAdmin):
    list_display = (
        "ejecucion",
        "punto_montaje",
        "total_formateado",
        "usado_formateado",
        "libre_formateado",
        "porcentaje_usado",
    )

    search_fields = (
        "punto_montaje",
        "dispositivo",
        "sistema_archivos",
    )

    @admin.display(description="Total")
    def total_formateado(self, obj):
        return bytes_legibles(obj.total_bytes)

    @admin.display(description="Usado")
    def usado_formateado(self, obj):
        return bytes_legibles(obj.usados_bytes)

    @admin.display(description="Libre")
    def libre_formateado(self, obj):
        return bytes_legibles(obj.libres_bytes)


class ResumenTipoArchivoInline(admin.TabularInline):
    model = ResumenTipoArchivo
    extra = 0
    readonly_fields = (
        "categoria",
        "extension",
        "cantidad",
        "total_bytes",
        "archivo_mas_antiguo_fecha",
        "archivo_mas_reciente_fecha",
    )

    can_delete = False

    show_change_link = True


@admin.register(MedicionRuta)
class MedicionRutaAdmin(admin.ModelAdmin):
    list_display = (
        "ruta_monitoreada",
        "ejecucion",
        "tamano_formateado",
        "total_archivos",
        "total_imagenes",
        "total_pdf",
        "archivos_inaccesibles",
    )

    list_filter = (
        "ruta_monitoreada",
        "ejecucion__estado",
    )

    search_fields = (
        "ruta_monitoreada__nombre",
        "ruta_resuelta",
        "archivo_mas_grande_ruta",
    )

    inlines = [ResumenTipoArchivoInline]

    @admin.display(description="Tamaño")
    def tamano_formateado(self, obj):
        return bytes_legibles(obj.total_bytes)


@admin.register(ResumenTipoArchivo)
class ResumenTipoArchivoAdmin(admin.ModelAdmin):
    list_display = (
        "medicion_ruta",
        "categoria",
        "extension",
        "cantidad",
        "tamano_formateado",
    )

    list_filter = (
        "categoria",
        "extension",
    )

    search_fields = (
        "extension",
        "medicion_ruta__ruta_monitoreada__nombre",
    )

    @admin.display(description="Tamaño")
    def tamano_formateado(self, obj):
        return bytes_legibles(obj.total_bytes)


class MedicionTablaInline(admin.TabularInline):
    model = MedicionTabla
    extra = 0

    readonly_fields = (
        "esquema",
        "nombre_tabla",
        "total_registros",
        "datos_bytes",
        "indices_bytes",
        "total_bytes",
    )

    can_delete = False

    show_change_link = True


@admin.register(MedicionBaseDatos)
class MedicionBaseDatosAdmin(admin.ModelAdmin):
    list_display = (
        "ejecucion",
        "alias",
        "vendor",
        "nombre_base_datos",
        "total_tablas",
        "total_registros",
        "tamano_formateado",
    )

    list_filter = (
        "vendor",
        "alias",
    )

    search_fields = (
        "alias",
        "vendor",
        "nombre_base_datos",
        "host",
    )

    inlines = [MedicionTablaInline]

    @admin.display(description="Tamaño")
    def tamano_formateado(self, obj):
        return bytes_legibles(obj.total_bytes)


@admin.register(MedicionTabla)
class MedicionTablaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_tabla",
        "esquema",
        "medicion_bd",
        "total_registros",
        "tamano_formateado",
    )

    search_fields = (
        "nombre_tabla",
        "esquema",
    )

    @admin.display(description="Tamaño")
    def tamano_formateado(self, obj):
        return bytes_legibles(obj.total_bytes)


@admin.register(UmbralAlerta)
class UmbralAlertaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo_objetivo",
        "identificador",
        "metrica",
        "operador",
        "valor",
        "unidad",
        "nivel",
        "activa",
    )

    list_filter = (
        "tipo_objetivo",
        "nivel",
        "activa",
    )

    search_fields = (
        "nombre",
        "identificador",
        "metrica",
    )


@admin.register(OperacionMantenimiento)
class OperacionMantenimientoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "tipo",
        "estado",
        "identificador_objetivo",
        "usuario",
        "creada_en",
        "bytes_liberados_formateados",
        "registros_afectados",
    )

    list_filter = (
        "tipo",
        "estado",
        "creada_en",
    )

    search_fields = (
        "identificador_objetivo",
        "usuario",
        "error",
    )

    readonly_fields = (
        "creada_en",
    )

    @admin.display(description="Liberado")
    def bytes_liberados_formateados(self, obj):
        return bytes_legibles(obj.bytes_liberados)
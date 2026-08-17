from __future__ import annotations

import hashlib
import os
import stat as statmod

from pathlib import Path

from django.utils import timezone

from .backup import (
    obtener_directorio_respaldos,
)
from .models import (
    RegistroDescargaRespaldo,
    RespaldoMantenimiento,
)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================


TAMANO_BLOQUE = (
    1024
    * 1024
)


ESTADOS_DESCARGABLES = {
    RespaldoMantenimiento.Estado.LISTO,
    RespaldoMantenimiento.Estado.PARCIAL,
}


# =============================================================================
# SHA-256
# =============================================================================


def normalizar_sha256(
    valor: str,
) -> str:

    valor = str(
        valor or ""
    ).strip().lower()


    if not valor:
        return ""


    if len(
        valor
    ) != 64:

        raise ValueError(
            "Un SHA-256 debe contener "
            "exactamente 64 caracteres."
        )


    permitidos = set(
        "0123456789abcdef"
    )


    if any(
        caracter not in permitidos
        for caracter in valor
    ):

        raise ValueError(
            "El SHA-256 contiene "
            "caracteres no válidos."
        )


    return valor


# =============================================================================
# RESOLVER ARCHIVO PRIVADO
# =============================================================================


def _resolver_archivo_respaldo(
    respaldo: RespaldoMantenimiento,
) -> Path:

    relativa_texto = str(
        respaldo.ruta_relativa_archivo
        or ""
    ).strip()


    if not relativa_texto:

        raise ValueError(
            "El respaldo no tiene un archivo "
            "físico registrado."
        )


    relativa = Path(
        relativa_texto
    )


    if relativa.is_absolute():

        raise ValueError(
            "La ruta registrada del respaldo "
            "no es relativa."
        )


    for parte in relativa.parts:

        if parte in {
            "",
            ".",
            "..",
        }:

            raise ValueError(
                "La ruta registrada contiene "
                "componentes no permitidos."
            )


    base = (
        obtener_directorio_respaldos()
    )


    path_sin_resolver = (
        base
        / relativa
    )


    if path_sin_resolver.is_symlink():

        raise ValueError(
            "El paquete de respaldo "
            "es un enlace simbólico."
        )


    try:

        path = (
            path_sin_resolver.resolve(
                strict=True
            )
        )

    except (
        FileNotFoundError,
        OSError,
    ) as exc:

        raise ValueError(
            "El paquete físico "
            "ya no existe."
        ) from exc


    try:

        path.relative_to(
            base
        )

    except ValueError as exc:

        raise ValueError(
            "El paquete físico está fuera "
            "del área privada de Espaciómetro."
        ) from exc


    if not path.is_file():

        raise ValueError(
            "La ubicación registrada "
            "no es un archivo regular."
        )


    return path


# =============================================================================
# ABRIR Y VALIDAR
# =============================================================================


def _abrir_y_validar_respaldo(
    respaldo: RespaldoMantenimiento,
):
    """
    Abre el mismo descriptor que posteriormente será
    entregado mediante FileResponse.

    Así evitamos validar un archivo y después abrir
    silenciosamente otro distinto.
    """

    if respaldo.estado not in (
        ESTADOS_DESCARGABLES
    ):

        raise ValueError(
            "El respaldo no se encuentra "
            "en un estado descargable."
        )


    esperado = normalizar_sha256(
        respaldo.sha256
    )


    if not esperado:

        raise ValueError(
            "El respaldo no tiene SHA-256 "
            "registrado por ESP013."
        )


    path = (
        _resolver_archivo_respaldo(
            respaldo
        )
    )


    flags = os.O_RDONLY


    if hasattr(
        os,
        "O_NOFOLLOW",
    ):

        flags |= os.O_NOFOLLOW


    try:

        fd = os.open(
            str(
                path
            ),
            flags,
        )

    except OSError as exc:

        raise ValueError(
            "No fue posible abrir "
            "el paquete de respaldo."
        ) from exc


    archivo = os.fdopen(
        fd,
        "rb",
        closefd=True,
    )


    try:

        info = os.fstat(
            archivo.fileno()
        )


        if not statmod.S_ISREG(
            info.st_mode
        ):

            raise ValueError(
                "El paquete ya no corresponde "
                "a un archivo regular."
            )


        tamano = int(
            info.st_size
        )


        if (
            respaldo.total_bytes_paquete
            and tamano
            != respaldo.total_bytes_paquete
        ):

            raise ValueError(
                "El tamaño físico del paquete "
                "ya no coincide con ESP013."
            )


        digest = hashlib.sha256()


        while True:

            bloque = archivo.read(
                TAMANO_BLOQUE
            )


            if not bloque:
                break


            digest.update(
                bloque
            )


        observado = (
            digest.hexdigest()
        )


        if observado != esperado:

            raise ValueError(
                "El SHA-256 actual del paquete "
                "no coincide con el registrado "
                "por ESP013."
            )


        # Volvemos al inicio.
        # Este MISMO descriptor será entregado
        # al navegador.

        archivo.seek(
            0
        )


        return {
            "archivo": archivo,

            "path": path,

            "tamano": tamano,

            "sha256": observado,
        }


    except Exception:

        archivo.close()

        raise


# =============================================================================
# PREPARAR ENTREGA
# =============================================================================


def preparar_entrega_descarga(
    *,
    respaldo: RespaldoMantenimiento,
    usuario: str = "",
    ip_cliente: str = "",
    user_agent: str = "",
) -> dict:

    resultado = {
        "registro": None,

        "archivo": None,

        "nombre_archivo": "",

        "error": "",
    }


    try:

        validacion = (
            _abrir_y_validar_respaldo(
                respaldo
            )
        )


    except Exception as exc:

        registro = (
            RegistroDescargaRespaldo.objects.create(

                respaldo=respaldo,

                usuario=(
                    str(
                        usuario
                        or ""
                    )[
                        :150
                    ]
                ),

                estado=(
                    RegistroDescargaRespaldo
                    .Estado
                    .ERROR
                ),

                sha256_esperado=(
                    str(
                        respaldo.sha256
                        or ""
                    )[
                        :64
                    ]
                ),

                ip_cliente=(
                    str(
                        ip_cliente
                        or ""
                    )[
                        :64
                    ]
                ),

                user_agent=(
                    str(
                        user_agent
                        or ""
                    )
                ),

                detalle=str(
                    exc
                ),
            )
        )


        resultado[
            "registro"
        ] = registro


        resultado[
            "error"
        ] = str(
            exc
        )


        return resultado


    try:

        registro = (
            RegistroDescargaRespaldo.objects.create(

                respaldo=respaldo,

                usuario=(
                    str(
                        usuario
                        or ""
                    )[
                        :150
                    ]
                ),

                estado=(
                    RegistroDescargaRespaldo
                    .Estado
                    .INICIADA
                ),

                sha256_esperado=(
                    respaldo.sha256
                ),

                sha256_servidor=(
                    validacion[
                        "sha256"
                    ]
                ),

                total_bytes=(
                    validacion[
                        "tamano"
                    ]
                ),

                ip_cliente=(
                    str(
                        ip_cliente
                        or ""
                    )[
                        :64
                    ]
                ),

                user_agent=(
                    str(
                        user_agent
                        or ""
                    )
                ),

                detalle=(
                    "Integridad validada. "
                    "El servidor inició la "
                    "entrega del paquete."
                ),
            )
        )


    except Exception:

        validacion[
            "archivo"
        ].close()

        raise


    resultado[
        "registro"
    ] = registro


    resultado[
        "archivo"
    ] = validacion[
        "archivo"
    ]


    resultado[
        "nombre_archivo"
    ] = Path(
        respaldo.nombre_archivo
        or validacion[
            "path"
        ].name
    ).name


    return resultado


# =============================================================================
# CONFIRMAR RECEPCIÓN
# =============================================================================


def confirmar_descarga(
    *,
    registro: RegistroDescargaRespaldo,
    sha256_cliente: str = "",
) -> dict:

    resultado = {
        "estado": (
            registro.estado
        ),

        "mensaje": "",

        "error": "",
    }


    if (
        registro.estado
        == RegistroDescargaRespaldo
        .Estado
        .ERROR
    ):

        resultado[
            "error"
        ] = (
            "Una entrega que terminó en error "
            "no puede confirmarse."
        )

        return resultado


    try:

        hash_cliente = (
            normalizar_sha256(
                sha256_cliente
            )
        )


    except ValueError as exc:

        resultado[
            "error"
        ] = str(
            exc
        )

        return resultado


    ahora = timezone.now()


    # =========================================================================
    # CONFIRMACIÓN SIN HASH
    # =========================================================================

    if not hash_cliente:

        registro.estado = (
            RegistroDescargaRespaldo
            .Estado
            .CONFIRMADA
        )


        registro.confirmada_en = (
            ahora
        )


        registro.detalle = (
            "El usuario confirmó haber "
            "recibido el paquete. "
            "No proporcionó SHA-256 local."
        )


        registro.save(
            update_fields=[
                "estado",
                "confirmada_en",
                "detalle",
            ]
        )


        resultado[
            "estado"
        ] = registro.estado


        resultado[
            "mensaje"
        ] = (
            "Recepción confirmada. "
            "La integridad local todavía "
            "no ha sido verificada."
        )


        return resultado


    # =========================================================================
    # CONFIRMACIÓN CON HASH
    # =========================================================================

    registro.sha256_cliente = (
        hash_cliente
    )


    registro.confirmada_en = (
        ahora
    )


    esperado = normalizar_sha256(
        registro.sha256_esperado
    )


    if hash_cliente == esperado:

        registro.estado = (
            RegistroDescargaRespaldo
            .Estado
            .VERIFICADA
        )


        registro.detalle = (
            "El usuario confirmó la recepción "
            "y el SHA-256 calculado en el PC "
            "coincide con ESP013."
        )


        registro.save(
            update_fields=[
                "estado",
                "sha256_cliente",
                "confirmada_en",
                "detalle",
            ]
        )


        resultado[
            "estado"
        ] = registro.estado


        resultado[
            "mensaje"
        ] = (
            "Descarga verificada correctamente. "
            "El SHA-256 del PC coincide con ESP013."
        )


        return resultado


    registro.estado = (
        RegistroDescargaRespaldo
        .Estado
        .VERIFICACION_FALLIDA
    )


    registro.detalle = (
        "El usuario confirmó la recepción, "
        "pero el SHA-256 proporcionado no "
        "coincide con ESP013."
    )


    registro.save(
        update_fields=[
            "estado",
            "sha256_cliente",
            "confirmada_en",
            "detalle",
        ]
    )


    resultado[
        "estado"
    ] = registro.estado


    resultado[
        "error"
    ] = (
        "El archivo recibido NO coincide "
        "con el SHA-256 esperado. "
        "No debe utilizarse para una futura "
        "liberación de espacio."
    )


    return resultado
from __future__ import annotations

import os
import platform
import socket
import sys
from pathlib import Path
from typing import Any

import django
from django.conf import settings


# =============================================================================
# UTILIDADES
# =============================================================================


def _resolver_ruta(valor: Any) -> dict:
    """
    Convierte una configuración de ruta Django en información utilizable.

    No requiere que la ruta exista.
    """

    if valor in (None, ""):
        return {
            "configurada": False,
            "ruta": "",
            "existe": False,
            "es_directorio": False,
            "lectura": False,
            "escritura": False,
        }

    try:
        ruta = Path(valor).expanduser().resolve(strict=False)
    except (TypeError, ValueError, OSError):
        return {
            "configurada": True,
            "ruta": str(valor),
            "existe": False,
            "es_directorio": False,
            "lectura": False,
            "escritura": False,
        }

    existe = ruta.exists()

    return {
        "configurada": True,
        "ruta": str(ruta),
        "existe": existe,
        "es_directorio": ruta.is_dir() if existe else False,
        "lectura": os.access(ruta, os.R_OK) if existe else False,
        "escritura": os.access(ruta, os.W_OK) if existe else False,
    }


def _vendor_desde_engine(engine: str) -> str:
    """
    Obtiene un nombre sencillo del motor a partir del ENGINE de Django.
    """

    engine = (engine or "").lower()

    if "postgresql" in engine:
        return "PostgreSQL"

    if "sqlite" in engine:
        return "SQLite"

    if "mysql" in engine:
        return "MySQL"

    if "oracle" in engine:
        return "Oracle"

    if not engine:
        return "No definido"

    return engine.rsplit(".", 1)[-1]


def _nombre_proyecto() -> str:
    """
    Intenta identificar el paquete principal del proyecto Django.

    Ejemplo:
        ROOT_URLCONF = "myproject.urls"

    devuelve:
        myproject
    """

    root_urlconf = getattr(settings, "ROOT_URLCONF", "") or ""

    if root_urlconf:
        return root_urlconf.split(".")[0]

    settings_module = os.environ.get(
        "DJANGO_SETTINGS_MODULE",
        "",
    )

    if settings_module:
        return settings_module.split(".")[0]

    return "Proyecto Django"


def _staticfiles_dirs() -> list[dict]:
    """
    Normaliza STATICFILES_DIRS.

    Django admite tanto rutas simples como algunas configuraciones
    con prefijo.
    """

    resultado = []

    for entrada in getattr(settings, "STATICFILES_DIRS", []) or []:

        prefijo = ""

        if (
            isinstance(entrada, (tuple, list))
            and len(entrada) == 2
        ):
            prefijo = str(entrada[0])
            valor = entrada[1]
        else:
            valor = entrada

        info = _resolver_ruta(valor)

        info["prefijo"] = prefijo

        resultado.append(info)

    return resultado


# =============================================================================
# BASES DE DATOS
# =============================================================================


def detectar_bases_datos() -> list[dict]:
    """
    Obtiene configuración no sensible de DATABASES.

    IMPORTANTE:
    nunca devuelve PASSWORD.
    """

    resultado = []

    databases = getattr(settings, "DATABASES", {}) or {}

    for alias, configuracion in databases.items():

        engine = str(
            configuracion.get("ENGINE", "") or ""
        )

        nombre = configuracion.get("NAME", "")

        resultado.append(
            {
                "alias": alias,
                "vendor": _vendor_desde_engine(engine),
                "engine": engine,
                "nombre": str(nombre or ""),
                "host": str(
                    configuracion.get("HOST", "") or ""
                ),
                "puerto": str(
                    configuracion.get("PORT", "") or ""
                ),
                "usuario": str(
                    configuracion.get("USER", "") or ""
                ),

                # Solo informamos si existe una contraseña.
                # Nunca devolvemos su contenido.
                "usa_password": bool(
                    configuracion.get("PASSWORD")
                ),
            }
        )

    return resultado


# =============================================================================
# AUTODETECCIÓN DEL PROYECTO
# =============================================================================


def detectar_proyecto() -> dict:
    """
    Detecta el entorno del proyecto Django anfitrión.

    Esta función constituye el núcleo de ESP001.

    No importa ni consulta modelos de otras aplicaciones.
    """

    base_dir = _resolver_ruta(
        getattr(settings, "BASE_DIR", "")
    )

    media_root = _resolver_ruta(
        getattr(settings, "MEDIA_ROOT", "")
    )

    static_root = _resolver_ruta(
        getattr(settings, "STATIC_ROOT", "")
    )

    return {
        # -----------------------------------------------------------------
        # Proyecto Django
        # -----------------------------------------------------------------

        "proyecto": {
            "nombre": _nombre_proyecto(),

            "settings_module": os.environ.get(
                "DJANGO_SETTINGS_MODULE",
                "",
            ),

            "root_urlconf": str(
                getattr(settings, "ROOT_URLCONF", "") or ""
            ),

            "debug": bool(
                getattr(settings, "DEBUG", False)
            ),

            "language_code": str(
                getattr(settings, "LANGUAGE_CODE", "") or ""
            ),

            "time_zone": str(
                getattr(settings, "TIME_ZONE", "") or ""
            ),
        },

        # -----------------------------------------------------------------
        # Sistema
        # -----------------------------------------------------------------

        "sistema": {
            "hostname": socket.gethostname(),

            "sistema_operativo": platform.system(),

            "release": platform.release(),

            "plataforma": platform.platform(),

            "arquitectura": platform.machine(),

            "python": platform.python_version(),

            "django": django.get_version(),

            "ejecutable_python": sys.executable,
        },

        # -----------------------------------------------------------------
        # Directorios Django
        # -----------------------------------------------------------------

        "rutas": {
            "base_dir": base_dir,
            "media_root": media_root,
            "static_root": static_root,
            "staticfiles_dirs": _staticfiles_dirs(),
        },

        # -----------------------------------------------------------------
        # Base de datos
        # -----------------------------------------------------------------

        "bases_datos": detectar_bases_datos(),

        # -----------------------------------------------------------------
        # Información adicional
        # -----------------------------------------------------------------

        "apps_instaladas": len(
            getattr(settings, "INSTALLED_APPS", [])
        ),
    }
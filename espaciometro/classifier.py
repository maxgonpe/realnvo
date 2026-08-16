from __future__ import annotations

from pathlib import Path


# =============================================================================
# CATEGORÍAS
# =============================================================================

CATEGORIAS = {
    "imagen": "Imágenes",
    "pdf": "PDF",
    "documento": "Documentos",
    "planilla": "Planillas",
    "video": "Videos",
    "audio": "Audio",
    "comprimido": "Comprimidos",
    "temporal": "Temporales",
    "base_datos": "Bases de datos",
    "codigo": "Código fuente",
    "configuracion": "Configuración",
    "otro": "Otros",
}


# =============================================================================
# EXTENSIONES
# =============================================================================

EXTENSIONES_IMAGEN = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp",
    ".tif",
    ".tiff",
    ".svg",
    ".heic",
}

EXTENSIONES_DOCUMENTO = {
    ".doc",
    ".docx",
    ".odt",
    ".txt",
    ".rtf",
    ".md",
}

EXTENSIONES_PLANILLA = {
    ".xls",
    ".xlsx",
    ".ods",
    ".csv",
}

EXTENSIONES_VIDEO = {
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".webm",
    ".mpeg",
    ".mpg",
}

EXTENSIONES_AUDIO = {
    ".mp3",
    ".wav",
    ".ogg",
    ".flac",
    ".m4a",
    ".aac",
}

EXTENSIONES_COMPRIMIDO = {
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".bz2",
    ".xz",
    ".7z",
    ".rar",
}

EXTENSIONES_TEMPORAL = {
    ".tmp",
    ".temp",
    ".cache",
    ".part",
    ".swp",
}

EXTENSIONES_BASE_DATOS = {
    ".sqlite",
    ".sqlite3",
    ".db",
    ".mdb",
}

EXTENSIONES_CODIGO = {
    ".py",
    ".pyc",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
    ".bash",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rs",
    ".java",
    ".go",
}

EXTENSIONES_CONFIGURACION = {
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".xml",
    ".env",
}


# =============================================================================
# CLASIFICACIÓN
# =============================================================================

def clasificar_archivo(path: Path | str) -> str:
    """
    Clasifica un archivo exclusivamente a partir de su nombre/extensión.

    No depende de ningún modelo ni aplicación del proyecto anfitrión.
    """

    path = Path(path)

    nombre = path.name.lower()
    extension = path.suffix.lower()

    if extension in EXTENSIONES_IMAGEN:
        return "imagen"

    if extension == ".pdf":
        return "pdf"

    if extension in EXTENSIONES_DOCUMENTO:
        return "documento"

    if extension in EXTENSIONES_PLANILLA:
        return "planilla"

    if extension in EXTENSIONES_VIDEO:
        return "video"

    if extension in EXTENSIONES_AUDIO:
        return "audio"

    if extension in EXTENSIONES_COMPRIMIDO:
        return "comprimido"

    if extension in EXTENSIONES_TEMPORAL:
        return "temporal"

    if extension in EXTENSIONES_BASE_DATOS:
        return "base_datos"

    if extension in EXTENSIONES_CODIGO:
        return "codigo"

    if extension in EXTENSIONES_CONFIGURACION:
        return "configuracion"

    # Algunos archivos comunes no tienen extensión.
    if nombre in {
        "dockerfile",
        "makefile",
        "requirements.txt",
        "pyproject.toml",
    }:
        return "configuracion"

    return "otro"


def nombre_categoria(codigo: str) -> str:
    return CATEGORIAS.get(codigo, CATEGORIAS["otro"])


def extension_normalizada(path: Path | str) -> str:
    """
    Devuelve una extensión apta para estadísticas.
    """

    extension = Path(path).suffix.lower()

    if not extension:
        return "[sin extensión]"

    return extension
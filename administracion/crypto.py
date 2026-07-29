"""
Cifrado reversible para secretos de negocio (p. ej. claves PDF de cartolas).

No usar hashers de Django: necesitamos recuperar la clave para abrir el PDF.
La clave Fernet se deriva de SECRET_KEY (cambiar SECRET_KEY invalida secretos guardados).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _fernet() -> Fernet:
    secret = getattr(settings, "SECRET_KEY", None)
    if not secret:
        raise ImproperlyConfigured("SECRET_KEY es obligatorio para cifrar claves de cartola.")
    digest = hashlib.sha256(f"adm-cartola-clave:{secret}".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def cifrar_texto(valor: str) -> str:
    texto = (valor or "").strip()
    if not texto:
        return ""
    return _fernet().encrypt(texto.encode("utf-8")).decode("ascii")


def descifrar_texto(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise ValueError("No se pudo descifrar la clave almacenada.") from exc


def tiene_secreto(token: str) -> bool:
    return bool(token and token.strip())

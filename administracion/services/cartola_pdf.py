"""
Lectura de metadatos desde cartolas PDF (B002 / preparación B003).

Usa la clave cifrada del banco (B001). No crea movimientos: solo identifica
cuenta, titular, período y un extracto de texto para precargar formularios.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from django.core.exceptions import ValidationError
from pypdf import PdfReader

from .bancos import obtener_clave_cartola
from ..models import Banco, CuentaBancaria


def _texto_pdf(archivo, clave: str) -> str:
    reader = PdfReader(archivo)
    if reader.is_encrypted:
        if not reader.decrypt(clave):
            raise ValidationError(
                "La clave del banco no abre este PDF. Revísela en B001."
            )
    partes = []
    for page in reader.pages:
        try:
            partes.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            raise ValidationError(f"No se pudo leer el PDF: {exc}") from exc
    return "\n".join(partes)


def _norm(texto: str) -> str:
    return re.sub(r"[ \t\xa0]+", " ", (texto or "").replace("\t", " ")).strip()


def _parse_fecha(valor: str):
    valor = (valor or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, fmt).date()
        except ValueError:
            continue
    return None


def _lineas(texto: str) -> list[str]:
    return [_norm(l) for l in texto.replace("\xa0", " ").splitlines() if _norm(l)]


def _inferir_estado(lineas: list[str], datos: dict) -> None:
    """Cartola CuentaRUT / Banco Estado (texto con tabs)."""
    datos["tipo_cuenta"] = CuentaBancaria.TipoCuenta.VISTA
    datos["nombre"] = "CuentaRUT"
    omitir_frag = (
        "ESTADO",
        "FECHA",
        "EMISI",
        "CORREO",
        "CARTOLA",
        "NOMBRE",
        "DESDE",
        "HASTA",
        "MONEDA",
        "SUCURSAL",
        "SALDO",
        "CUENTARUT",
        "MOVIMIENTO",
        "DOCTO",
        "DESCRIP",
        "CARGOS",
        "ABONOS",
    )

    for lin in lineas:
        up = lin.upper()
        if any(f in up for f in omitir_frag):
            continue
        if "@" in lin:
            continue
        if re.fullmatch(r"[A-ZÁÉÍÓÚÑ]+(?: [A-ZÁÉÍÓÚÑ]+){2,6}", lin):
            datos["titular"] = lin.title()
            break

    for i, lin in enumerate(lineas):
        if re.fullmatch(r"\d{6,12}", lin):
            nxt = " ".join(lineas[i + 1 : i + 3]).upper()
            if "PESOS" in nxt or "LIGUA" in nxt:
                datos["numero_cuenta"] = lin
                for j in range(i + 1, min(i + 6, len(lineas))):
                    if re.fullmatch(r"[\d\.]+", lineas[j]) and "." in lineas[j]:
                        datos["saldo_inicial"] = lineas[j]
                        break
                break

    fechas = [x for x in lineas if re.fullmatch(r"\d{2}/\d{2}/\d{4}", x)]
    if len(fechas) >= 3:
        datos["periodo_desde"] = _parse_fecha(fechas[1])
        datos["periodo_hasta"] = _parse_fecha(fechas[2])
    elif len(fechas) >= 2:
        datos["periodo_desde"] = _parse_fecha(fechas[0])
        datos["periodo_hasta"] = _parse_fecha(fechas[1])


def _inferir_falabella(lineas: list[str], joined: str, datos: dict) -> None:
    datos["tipo_cuenta"] = CuentaBancaria.TipoCuenta.CORRIENTE
    datos["nombre"] = "Cuenta corriente Falabella"

    m = re.search(r"Numero\s+de\s+Cuenta\s*:\s*([0-9\-]+)", joined, re.I)
    if m:
        datos["numero_cuenta"] = m.group(1).strip()

    for i, lin in enumerate(lineas):
        if re.search(r"SR\s*\(A\)", lin, re.I) and i + 1 < len(lineas):
            cand = lineas[i + 1]
            if not cand.lower().startswith("numero"):
                datos["titular"] = cand.title()
                break
    if not datos["titular"]:
        m = re.search(
            r"SR\s*\(A\)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s]+?)(?=\s+Numero)",
            joined,
            re.I,
        )
        if m:
            datos["titular"] = _norm(m.group(1)).title()

    m = re.search(
        r"Fecha\s+desde\s*:\s*(\d{2}/\d{2}/\d{4})\s+Hasta\s*:\s*(\d{2}/\d{2}/\d{4})",
        joined,
        re.I,
    )
    if m:
        datos["periodo_desde"] = _parse_fecha(m.group(1))
        datos["periodo_hasta"] = _parse_fecha(m.group(2))


def _inferir_chile(lineas: list[str], datos: dict) -> None:
    """Estado de cuenta Banco de Chile: etiquetas y valores en líneas con ': '."""
    datos["tipo_cuenta"] = CuentaBancaria.TipoCuenta.VISTA
    datos["nombre"] = "Cuenta vista"

    for i, lin in enumerate(lineas):
        if lin.upper() == "CUENTA VISTA" and i + 1 < len(lineas):
            if "@" not in lineas[i + 1]:
                datos["titular"] = lineas[i + 1].title()
            break

    # Valores con patrón " :  XXXXXXXX1364"
    valores = []
    for lin in lineas:
        m = re.match(r"^:\s*(.+)$", lin)
        if m:
            valores.append(m.group(1).strip())

    # Preferir número enmascarado tipo XXXXXXXX1364 (no el teléfono 600…)
    for v in valores:
        if re.fullmatch(r"X+\d+", v, re.I):
            datos["numero_cuenta"] = v.upper()
            break
    if not datos["numero_cuenta"]:
        for v in valores:
            if re.fullmatch(r"\d{8,}", v) and not v.startswith("600"):
                datos["numero_cuenta"] = v
                break

    fechas = [v for v in valores if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v)]
    if len(fechas) >= 2:
        datos["periodo_desde"] = _parse_fecha(fechas[0])
        datos["periodo_hasta"] = _parse_fecha(fechas[1])
    elif len(fechas) == 1:
        datos["periodo_hasta"] = _parse_fecha(fechas[0])


def _inferir_desde_texto(banco: Banco, texto: str) -> dict[str, Any]:
    lineas = _lineas(texto)
    joined = " ".join(lineas)
    nombre_banco = (banco.nombre or "").casefold()

    datos: dict[str, Any] = {
        "banco_id": banco.pk,
        "banco_nombre": banco.nombre,
        "titular": "",
        "numero_cuenta": "",
        "tipo_cuenta": CuentaBancaria.TipoCuenta.CORRIENTE,
        "moneda": "CLP",
        "nombre": f"Cuenta {banco.nombre}",
        "periodo_desde": None,
        "periodo_hasta": None,
        "saldo_inicial": "",
        "texto_muestra": "\n".join(lineas[:40]),
        "fuente": "pdf",
    }

    if re.search(r"\bPESOS\b|\bCLP\b", joined, re.I):
        datos["moneda"] = "CLP"

    if "falabella" in nombre_banco or "Numero de Cuenta" in joined:
        _inferir_falabella(lineas, joined, datos)
    elif "chile" in nombre_banco or "Estado de Cuenta" in joined:
        _inferir_chile(lineas, datos)
    elif "estado" in nombre_banco or "CuentaRUT" in joined:
        _inferir_estado(lineas, datos)
    else:
        # genérico: buscar número largo y titular en mayúsculas
        for lin in lineas:
            if re.fullmatch(r"[A-ZÁÉÍÓÚÑ]+(?: [A-ZÁÉÍÓÚÑ]+){2,6}", lin):
                datos["titular"] = lin.title()
                break
            if re.fullmatch(r"[\dX]{6,}", lin, re.I) and not datos["numero_cuenta"]:
                datos["numero_cuenta"] = lin.upper()

    return datos


def leer_metadatos_cartola_pdf(*, banco: Banco, archivo) -> dict[str, Any]:
    """
    Abre un PDF de cartola con la clave del banco y extrae campos útiles para B002/B003.
    """
    if not archivo:
        raise ValidationError({"archivo": "Seleccione un archivo PDF."})
    nombre = getattr(archivo, "name", "") or ""
    if not nombre.lower().endswith(".pdf"):
        raise ValidationError({"archivo": "Solo se admiten archivos PDF en esta carga."})

    clave = obtener_clave_cartola(banco)
    if hasattr(archivo, "seek"):
        archivo.seek(0)
    texto = _texto_pdf(archivo, clave)
    if not texto.strip():
        raise ValidationError("El PDF no entregó texto legible.")
    return _inferir_desde_texto(banco, texto)

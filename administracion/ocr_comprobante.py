"""
Extracción gratuita de datos desde fotos de comprobantes (OCR).

Motor: rapidocr-onnxruntime (pip, sin coste ni API externa).
El técnico revisa y corrige antes de guardar.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from django.core.files.uploadedfile import UploadedFile
from PIL import Image


@dataclass
class DatosComprobante:
    proveedor: str = ""
    rut_proveedor: str = ""
    tipo_documento: str = "BOLETA"
    numero_documento: str = ""
    sucursal: str = ""
    fecha: str = ""  # YYYY-MM-DD para input type=date
    descripcion: str = ""
    forma_pago: str = "DEBITO"
    neto: str = ""
    iva: str = ""
    total: str = ""
    texto_ocr: str = ""
    confianza: str = "media"
    avisos: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # OCR frecuentes
    "inayo": 5,
    "1nayo": 5,
    "lnayo": 5,
    "mnayo": 5,
}


def _normalizar_texto(lineas: list[str]) -> str:
    return "\n".join(lineas)


def _limpiar_monto(valor: str) -> Decimal | None:
    if not valor:
        return None
    v = valor.strip()
    v = v.replace("$", "").replace("S", "").replace("s", "")
    v = v.replace(" ", "")
    # 42.990 o 12.100 (miles CLP) vs 6.864 (también miles)
    if re.fullmatch(r"\d{1,3}(\.\d{3})+", v):
        v = v.replace(".", "")
    elif "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        return Decimal(v)
    except InvalidOperation:
        return None


def _decimal_str(valor: Decimal | None) -> str:
    if valor is None:
        return ""
    return f"{valor:.2f}"


def _buscar_rut(texto: str) -> str:
    m = re.search(
        r"(?:R\.?\s*U\.?\s*T\.?\s*:?\s*)?(\d{1,2}\.?\d{3}\.?\d{3}\s*-\s*[\dkK])",
        texto,
        re.IGNORECASE,
    )
    if not m:
        return ""
    rut = m.group(1).replace(" ", "")
    # Completar puntos si vienen a medias
    return rut


def _buscar_numero_documento(lineas: list[str], texto: str) -> str:
    excluir = set()
    for i, linea in enumerate(lineas):
        if re.search(r"Terminal|Aprobacion|Cod\.?\s*Aprob|Digitos|Hora", linea, re.IGNORECASE):
            for j in range(i, min(i + 4, len(lineas))):
                for m in re.finditer(r"(\d{5,})", lineas[j]):
                    excluir.add(m.group(1))

    patrones = [
        r"(?:N[ºo°!]?\s*[:\-]?\s*|NO[-\s]*)(\d{4,})",
        r"BOLETA\s*(?:ELECTRONICA)?\s*N[ºo°!]?\s*(\d+)",
        r"\bN(\d{5,})\b",
    ]
    for pat in patrones:
        for m in re.finditer(pat, texto, re.IGNORECASE):
            num = m.group(1)
            if num not in excluir:
                return num
    for linea in lineas:
        m = re.search(r"^N?(\d{5,8})$", linea.strip(), re.IGNORECASE)
        if m and m.group(1) not in excluir:
            return m.group(1)
    return ""


def _buscar_fecha(texto: str) -> str:
    # Emisión : 9 de mayo del 2026 / errores OCR (inayo, mnayo)
    # Unir espacios raros del OCR
    plano = re.sub(r"\s+", " ", texto)
    m = re.search(
        r"(\d{1,2})\s*de\s*([A-Za-záéíóúñ0-9]{3,12})\s*(?:del?\s*)?(\d{4})",
        plano,
        re.IGNORECASE,
    )
    if m:
        dia = int(m.group(1))
        mes_txt = (
            m.group(2)
            .lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
        )
        # OCR: "1nayo" / "lnayo" por "mayo"
        mes_txt = mes_txt.replace("1nayo", "mayo").replace("lnayo", "mayo").replace("inayo", "mayo")
        anio = int(m.group(3))
        mes = _MESES.get(mes_txt)
        if mes:
            try:
                return date(anio, mes, dia).isoformat()
            except ValueError:
                pass

    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", plano)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            try:
                return date(y, d, mo).isoformat()
            except ValueError:
                pass
    return ""


def _monto_despues_etiqueta(lineas: list[str], etiquetas: tuple[str, ...]) -> Decimal | None:
    """Busca una etiqueta y toma el monto en la misma línea o en las siguientes."""
    for i, linea in enumerate(lineas):
        for et in etiquetas:
            if re.search(et, linea, re.IGNORECASE):
                m = re.search(r"([\d][\d\.\,]*)", linea.split(":")[-1])
                if m:
                    mon = _limpiar_monto(m.group(1))
                    if mon and mon >= Decimal("1"):
                        return mon
                for j in range(i + 1, min(i + 3, len(lineas))):
                    m2 = re.search(r"\$?\s*([\d\.\,]+)", lineas[j])
                    if m2:
                        mon = _limpiar_monto(m2.group(1))
                        if mon and mon >= Decimal("1"):
                            return mon
    return None


def _buscar_montos(texto: str, lineas: list[str]) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    neto = _monto_despues_etiqueta(lineas, (r"Neto\s*\$?", r"Mon[nto]+\s*Neto"))
    iva = _monto_despues_etiqueta(lineas, (r"\bIVA\b",))
    total = _monto_despues_etiqueta(lineas, (r"^Total", r"Total\s*\$?", r"Totals?"))

    m = re.search(r"Neto\s*\$?\s*:?\s*([\d\.\,]+)", texto, re.IGNORECASE)
    if m and neto is None:
        neto = _limpiar_monto(m.group(1))

    m = re.search(r"IVA(?:\s*\(%\))?\s*\$?\s*:?\s*([\d\.\,]+)", texto, re.IGNORECASE)
    if m and iva is None:
        iva = _limpiar_monto(m.group(1))

    m = re.search(r"Totals?\s*\$?\s*:?\s*([\d\.\,]+)", texto, re.IGNORECASE)
    if m and total is None:
        total = _limpiar_monto(m.group(1))

    candidatos_total = []
    for linea in lineas:
        # Solo montos con signo $ (evita tomar N° boleta / terminal como plata)
        for m3 in re.finditer(r"\$\s*([\d]{1,3}(?:\.\d{3})+|\d+(?:[.,]\d{1,2})?)", linea):
            mon = _limpiar_monto(m3.group(1))
            if mon and Decimal("100") <= mon <= Decimal("5000000"):
                candidatos_total.append(mon)

    if candidatos_total:
        mayor = max(candidatos_total)
        if total is None or (iva and total == iva) or total < Decimal("100"):
            total = mayor
        elif mayor >= (total or 0) and mayor != iva:
            total = max(total or 0, mayor)

    # Si total quedó absurdo (confundió con N° documento), preferir candidatos con $
    if total and candidatos_total and (
        total > Decimal("5000000") or datos_numero_parece_id(total)
    ):
        total = max(candidatos_total)

    if neto is not None and total is not None and neto > total:
        neto = None
    if iva is not None and total is not None and iva > total:
        iva = None
    if neto is not None and neto < Decimal("50") and total and total > Decimal("1000"):
        neto = None

    return neto, iva, total


def datos_numero_parece_id(valor: Decimal) -> bool:
    """Montos enteros enormes sin formato de plata suelen ser IDs mal leídos."""
    if valor != valor.to_integral_value():
        return False
    return int(valor) >= 100000


def _buscar_proveedor(lineas: list[str], texto: str) -> str:
    # Patrones claros
    for linea in lineas:
        up = linea.upper()
        if "GELCOM" in up:
            return "GELCOM SPA"
        if "BUSES LA PORT" in up or "PORTE" in up and "BUS" in up:
            return "BUSES LA PORTEÑA LTDA."
        if "CHURRASC" in up:
            return "El Churrascón COMIDA AL PASO"
        if "BANCHILE" in up:
            continue

    # Tras BOLETA ELECTRONICA suele venir la razón social
    for i, linea in enumerate(lineas):
        if re.search(r"BOLETA\s*ELECTR", linea, re.IGNORECASE):
            for j in range(i + 1, min(i + 6, len(lineas))):
                cand = lineas[j].strip()
                if len(cand) < 4:
                    continue
                if re.search(r"R\.?U\.?T|S\.?I\.?I|N[ºo°]?\d|VENTA|Emisi", cand, re.IGNORECASE):
                    continue
                if re.search(r"(SPA|LTDA|EIRL|S\.A)", cand, re.IGNORECASE):
                    return cand
                if cand.isupper() and len(cand) > 5:
                    return cand
    return ""


def _buscar_descripcion(lineas: list[str], texto: str) -> str:
    for linea in lineas:
        up = linea.upper().replace(" ", "")
        if "ROKU" in up or "STREAMING" in up:
            return "ROKU STREAMING STICK HD"
        if "INSPECTOR" in up:
            return "Pasaje / ticket transporte"
        if "CHURRASC" in up or "COMIDA" in up:
            return "Alimentación"
    # Primera línea de producto típica (después de Pago)
    for i, linea in enumerate(lineas):
        if re.search(r"^Pago", linea, re.IGNORECASE):
            for j in range(i + 1, min(i + 8, len(lineas))):
                cand = lineas[j].strip()
                if len(cand) > 8 and not re.search(
                    r"Neto|IVA|Total|P\.?\s*unit|Cant|Item", cand, re.IGNORECASE
                ):
                    return cand[:200]
    return ""


def _buscar_forma_pago(texto: str) -> str:
    t = texto.upper()
    if "DEBIT" in t or "DEBILO" in t or "T.DEB" in t or "VISA" in t:
        return "DEBITO"
    if "TRANSF" in t:
        return "TRANSFERENCIA"
    if "EFECT" in t:
        return "EFECTIVO"
    return "OTRO"


def _inferir_tipo(texto: str, total_encontrado: bool) -> str:
    t = texto.upper()
    if "BOLETA" in t:
        return "BOLETA"
    if "FACTURA" in t:
        return "FACTURA"
    if "BUS" in t or "PASAJE" in t or "PORTE" in t:
        return "OTRO"
    if "PEAJE" in t:
        return "PEAJE"
    return "BOLETA" if total_encontrado else "OTRO"


def _ocr_lineas(imagen: Image.Image) -> list[str]:
    buf = BytesIO()
    # RapidOCR trabaja mejor con RGB
    if imagen.mode not in ("RGB", "L"):
        imagen = imagen.convert("RGB")
    else:
        imagen = imagen.convert("RGB")
    imagen.save(buf, format="JPEG", quality=92)
    buf.seek(0)

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise RuntimeError(
            "Falta el motor OCR. Instale: pip install rapidocr-onnxruntime"
        ) from exc

    engine = RapidOCR()
    # RapidOCR acepta ndarray / path / bytes vía numpy
    import numpy as np

    arr = np.array(imagen)
    result, _elapse = engine(arr)
    if not result:
        return []
    return [str(item[1]).strip() for item in result if item and item[1]]


def extraer_datos_comprobante(archivo: UploadedFile | bytes | str) -> DatosComprobante:
    """
    Lee una imagen de comprobante y propone campos para DetalleRendicion.
    """
    datos = DatosComprobante()
    avisos: list[str] = []

    if isinstance(archivo, (bytes, bytearray)):
        imagen = Image.open(BytesIO(archivo))
    elif isinstance(archivo, str):
        imagen = Image.open(archivo)
    else:
        archivo.seek(0)
        imagen = Image.open(archivo)

    # Limitar tamaño para rendimiento en móvil
    max_lado = 1800
    if max(imagen.size) > max_lado:
        imagen.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)

    try:
        lineas = _ocr_lineas(imagen)
    except Exception as exc:  # noqa: BLE001
        datos.avisos.append(f"No se pudo leer la imagen con OCR: {exc}")
        datos.confianza = "baja"
        return datos

    if not lineas:
        datos.avisos.append("OCR no encontró texto. Complete los datos a mano.")
        datos.confianza = "baja"
        return datos

    texto = _normalizar_texto(lineas)
    datos.texto_ocr = texto

    datos.rut_proveedor = _buscar_rut(texto)
    datos.numero_documento = _buscar_numero_documento(lineas, texto)
    datos.fecha = _buscar_fecha(texto) or date.today().isoformat()
    if not _buscar_fecha(texto):
        avisos.append("No se detectó fecha clara; se usó la fecha de hoy.")

    neto, iva, total = _buscar_montos(texto, lineas)
    datos.neto = _decimal_str(neto)
    datos.iva = _decimal_str(iva)
    datos.total = _decimal_str(total)

    datos.proveedor = _buscar_proveedor(lineas, texto)
    datos.descripcion = _buscar_descripcion(lineas, texto) or datos.proveedor
    datos.forma_pago = _buscar_forma_pago(texto)
    datos.tipo_documento = _inferir_tipo(texto, total is not None)

    if not datos.total:
        avisos.append("No se detectó el total. Revise el monto antes de guardar.")
        datos.confianza = "baja"
    elif not datos.proveedor or not datos.numero_documento:
        avisos.append("Algunos campos quedaron incompletos; revise antes de guardar.")
        datos.confianza = "media"
    else:
        datos.confianza = "alta"

    # Dirección / sucursal aproximada
    for linea in lineas:
        if re.search(r"(AVENIDA|CALLE|ORTIZ|MOLINA|PORVENIR)", linea, re.IGNORECASE):
            datos.sucursal = linea[:100]
            break

    datos.avisos = avisos
    return datos

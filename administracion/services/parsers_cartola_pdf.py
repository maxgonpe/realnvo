"""
Parsers de cartolas PDF por banco + utilidades de montos enteros (sin decimales).

Convención de montos: puntos = separador de miles chileno; se ignoran decimales.
Ej.: "$15.000" → 15000, "10.990" → 10990, "3.759" → 3759.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date, datetime
from typing import Any

from django.core.exceptions import ValidationError
from pypdf import PdfReader

from .bancos import obtener_clave_cartola
from ..models import Banco, CuentaBancaria, PlantillaMapeoCartola


def parse_monto_entero(raw: Any) -> int:
    """Convierte monto impreso chileno a entero (sin decimales)."""
    if raw is None:
        return 0
    s = str(raw).strip().replace("\xa0", " ").replace("$", "").replace(" ", "")
    if not s or s in {".", "-", "—"}:
        return 0
    # 1.234,56 → enteros antes de la coma
    if "," in s and "." in s:
        s = s.replace(".", "").split(",")[0]
    elif "," in s:
        s = s.split(",")[0]
    else:
        # solo puntos → miles
        s = s.replace(".", "")
    s = re.sub(r"[^\d-]", "", s)
    if not s or s == "-":
        return 0
    try:
        return abs(int(s))
    except ValueError as exc:
        raise ValidationError(f"Monto inválido: {raw!r}") from exc


def fingerprint_movimiento(
    *,
    cuenta_id: int,
    fecha: date,
    descripcion: str,
    cargo: int,
    abono: int,
    saldo,
    documento: str,
) -> str:
    base = (
        f"{cuenta_id}|{fecha.isoformat()}|{descripcion.strip().upper()}|"
        f"{cargo}|{abono}|{saldo if saldo is not None else ''}|{documento}"
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def _texto_pdf(archivo, clave: str) -> str:
    reader = PdfReader(archivo)
    if reader.is_encrypted and not reader.decrypt(clave):
        raise ValidationError("La clave del banco no abre este PDF.")
    partes = []
    for page in reader.pages:
        partes.append(page.extract_text() or "")
    return "\n".join(partes)


def _lineas(texto: str) -> list[str]:
    out = []
    for raw in texto.replace("\xa0", " ").splitlines():
        lin = re.sub(r"[ \t]+", " ", raw.replace("\t", " ")).strip()
        if lin:
            out.append(lin)
    return out


def _parse_fecha(valor: str, fmt: str = "%d/%m/%Y"):
    valor = (valor or "").strip()
    for f in (fmt, "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(valor, f).date()
        except ValueError:
            continue
    return None


def _fecha_sin_anio(ddmm: str, desde: date | None, hasta: date | None) -> date | None:
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", (ddmm or "").strip())
    if not m:
        return None
    dia, mes = int(m.group(1)), int(m.group(2))
    anios = []
    if desde:
        anios.append(desde.year)
    if hasta and (not desde or hasta.year != desde.year):
        anios.append(hasta.year)
    if not anios:
        anios = [date.today().year]
    candidatos = []
    for y in anios:
        try:
            candidatos.append(date(y, mes, dia))
        except ValueError:
            continue
    if not candidatos:
        return None
    if desde and hasta:
        for c in candidatos:
            if desde <= c <= hasta:
                return c
        # cruce de año: diciembre/enero
        for c in candidatos:
            if c.month >= 11 or c.month <= 2:
                return c
    return candidatos[0]


def _enriquecer_descripcion(desc: str) -> dict:
    extra = {
        "tipo_movimiento": "",
        "canal_movimiento": "",
        "nombre_contraparte": "",
        "fecha_operacion_original": None,
        "hora_operacion_original": "",
        "descripcion_original": desc,
    }
    up = desc.upper()
    if "GIRO" in up or "CAJERO" in up:
        extra["tipo_movimiento"] = "GIRO_CAJERO"
    elif "TEF" in up or "TRANSF" in up or "TRASPASO" in up:
        extra["tipo_movimiento"] = "TRANSFERENCIA"
    elif "PAGO" in up:
        extra["tipo_movimiento"] = "PAGO"
    elif "COMISION" in up or "COMISIÓN" in up:
        extra["tipo_movimiento"] = "COMISION"
    elif "REMUNERACION" in up or "REMUNERACIÓN" in up:
        extra["tipo_movimiento"] = "ABONO"
    if "REDBANC" in up:
        extra["canal_movimiento"] = "REDBANC"
    elif "INTERNET" in up:
        extra["canal_movimiento"] = "INTERNET"
    elif "CENTRAL" in up:
        extra["canal_movimiento"] = "POS"
    m = re.search(r"(\d{1,2}:\d{2})", desc)
    if m:
        extra["hora_operacion_original"] = m.group(1)
    m = re.search(r"(20\d{2}-\d{2}-\d{2})", desc)
    if m:
        extra["fecha_operacion_original"] = _parse_fecha(m.group(1), "%Y-%m-%d")
    m = re.search(
        r"(?:PARA|DE|A:|DE:)\s*([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñ\s\.\*]{2,60})",
        desc,
        re.I,
    )
    if m:
        extra["nombre_contraparte"] = m.group(1).strip()[:200]
    return extra


def _mov(
    *,
    fecha,
    descripcion,
    cargo,
    abono,
    saldo=None,
    documento="",
    sucursal="",
    codigo_sucursal="",
    fila=None,
) -> dict:
    cargo_i = int(cargo or 0)
    abono_i = int(abono or 0)
    if cargo_i and abono_i:
        raise ValidationError(
            f"Cargo y abono simultáneos: {descripcion!r} ({cargo_i}/{abono_i})"
        )
    if not cargo_i and not abono_i:
        return {}  # fila vacía / solo saldo
    tipo = "EGRESO" if cargo_i else "INGRESO"
    monto = cargo_i or abono_i
    extra = _enriquecer_descripcion(descripcion)
    return {
        "fecha_operacion": fecha,
        "fecha_contable": fecha,
        "descripcion_movimiento": descripcion,
        "descripcion_original": descripcion,
        "monto_cargo": cargo_i,
        "monto_abono": abono_i,
        "monto": monto,
        "tipo": tipo,
        "saldo_bancario": saldo,
        "numero_documento": str(documento or ""),
        "sucursal_movimiento": sucursal,
        "codigo_sucursal_movimiento": codigo_sucursal,
        "numero_fila_origen": fila,
        **extra,
    }


# ---------------------------------------------------------------------------
# Parsers por banco
# ---------------------------------------------------------------------------


def parse_falabella(texto: str) -> dict:
    lineas = _lineas(texto)
    joined = " ".join(lineas)
    cab: dict[str, Any] = {
        "tipo_documento": "Cartola Cuenta Corriente",
        "parser": "BANCO_FALABELLA",
    }
    m = re.search(r"Cartola\s*N[°º]?\s*:\s*(\d+)", joined, re.I)
    if m:
        cab["numero_cartola"] = m.group(1)
    m = re.search(
        r"Fecha\s+desde\s*:\s*(\d{2}/\d{2}/\d{4})\s+Hasta\s*:\s*(\d{2}/\d{2}/\d{4})",
        joined,
        re.I,
    )
    if m:
        cab["fecha_inicio_periodo"] = _parse_fecha(m.group(1))
        cab["fecha_fin_periodo"] = _parse_fecha(m.group(2))
    m = re.search(r"Numero\s+de\s+Cuenta\s*:\s*([0-9\-]+)", joined, re.I)
    if m:
        cab["numero_cuenta_texto"] = m.group(1)
    m = re.search(r"Oficina\s*:\s*(.+?)(?:Cartola|Fecha)", joined, re.I)
    if m:
        cab["sucursal_cuenta"] = m.group(1).strip()[:120]
    for i, lin in enumerate(lineas):
        if re.search(r"SR\s*\(A\)", lin, re.I) and i + 1 < len(lineas):
            cab["tratamiento_titular"] = "SR(A)"
            cab["nombre_titular"] = lineas[i + 1].title()
            break
    m = re.search(
        r"Saldo\s+Inicial\s+Saldo\s+Final.*?\$?([\d\.]+)\s+\$?([\d\.]+)",
        joined,
        re.I,
    )
    # fallback: look for Resumen de Saldos numbers
    if "Saldo Inicial" in joined or "Saldo Inicial" in texto:
        nums = re.findall(r"\$([\d\.]+)", " ".join(lineas[8:20]))
        if len(nums) >= 2:
            cab["saldo_inicial"] = parse_monto_entero(nums[0])
            cab["saldo_final"] = parse_monto_entero(nums[1])
        if len(nums) >= 4:
            cab["saldo_disponible"] = parse_monto_entero(nums[3])

    movimientos = []
    en_mov = False
    for idx, lin in enumerate(lineas):
        if lin.upper().startswith("MOVIMIENTOS"):
            en_mov = True
            continue
        if not en_mov:
            continue
        if lin.lower().startswith("fecha oficina"):
            continue
        m = re.match(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(\d+)\s+(.+?)\s+"
            r"\$([\d\.]+)\s+\$([\d\.]+)\s+\$([\d\.]+)\s*$",
            lin,
        )
        if not m:
            continue
        fecha = _parse_fecha(m.group(1))
        cargo = parse_monto_entero(m.group(5))
        abono = parse_monto_entero(m.group(6))
        saldo = parse_monto_entero(m.group(7))
        mov = _mov(
            fecha=fecha,
            descripcion=m.group(4).strip(),
            cargo=cargo,
            abono=abono,
            saldo=saldo,
            documento=m.group(3),
            sucursal=m.group(2).strip(),
            fila=idx + 1,
        )
        if mov:
            movimientos.append(mov)

    if not cab.get("fecha_inicio_periodo") and movimientos:
        cab["fecha_inicio_periodo"] = min(x["fecha_operacion"] for x in movimientos)
        cab["fecha_fin_periodo"] = max(x["fecha_operacion"] for x in movimientos)
    return {"cabecera": cab, "movimientos": movimientos}


def parse_banco_estado(texto: str) -> dict:
    # Conservar líneas con tabs para agrupar columnas
    raw_lines = [l.rstrip() for l in texto.splitlines()]
    lineas = []
    for l in raw_lines:
        s = l.replace("\t", " ").strip()
        if s:
            lineas.append(s)

    cab: dict[str, Any] = {
        "tipo_documento": "Estado de Movimientos",
        "tipo_cuenta_texto": "CuentaRUT",
        "parser": "BANCO_ESTADO",
    }
    for lin in lineas:
        if re.fullmatch(r"[A-ZÁÉÍÓÚÑ]+(?: [A-ZÁÉÍÓÚÑ]+){2,6}", lin):
            if "FECHA" not in lin and "ESTADO" not in lin:
                cab["nombre_titular"] = lin.title()
                break
    fechas = [x for x in lineas if re.fullmatch(r"\d{2}/\d{2}/\d{4}", x)]
    if len(fechas) >= 3:
        cab["fecha_emision"] = _parse_fecha(fechas[0])
        cab["fecha_inicio_periodo"] = _parse_fecha(fechas[1])
        cab["fecha_fin_periodo"] = _parse_fecha(fechas[2])
    for i, lin in enumerate(lineas):
        if re.fullmatch(r"\d{6,12}", lin):
            nxt = " ".join(lineas[i + 1 : i + 3]).upper()
            if "PESOS" in nxt or "LIGUA" in nxt:
                cab["numero_cuenta_texto"] = lin
                for j in range(i + 1, min(i + 6, len(lineas))):
                    if re.fullmatch(r"[\d\.]+", lineas[j]) and "." in lineas[j]:
                        cab["saldo_inicial"] = parse_monto_entero(lineas[j])
                        break
                break
    for lin in lineas:
        if "@" in lin:
            cab["correo_electronico"] = lin.strip()
            break
    m = re.search(r"\b(\d{5})\b", " ".join(lineas[:40]))
    # Nº cartola near email
    for i, lin in enumerate(lineas):
        if "@" in lin and i + 1 < len(lineas) and re.fullmatch(r"\d+", lineas[i + 1]):
            cab["numero_cartola"] = lineas[i + 1]
            break

    # Movimientos: bloques de 7 líneas tras encabezado SALDO
    movimientos = []
    start = 0
    for i, lin in enumerate(lineas):
        if lin.upper() == "SALDO" and i + 1 < len(lineas) and re.fullmatch(r"\d+", lineas[i + 1]):
            start = i + 1
            break
    i = start
    fila = 0
    while i + 6 < len(lineas):
        doc, desc, suc = lineas[i], lineas[i + 1], lineas[i + 2]
        cargo_s, abono_s, fecha_s, saldo_s = (
            lineas[i + 3],
            lineas[i + 4],
            lineas[i + 5],
            lineas[i + 6],
        )
        if not re.fullmatch(r"\d+", doc):
            i += 1
            continue
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", fecha_s.replace("|", "").strip()):
            # a veces quedan pipes
            fecha_s = fecha_s.replace("|", "").strip()
        fecha_s = fecha_s.replace("|", "").strip()
        cargo_s = cargo_s.replace("|", "").strip()
        abono_s = abono_s.replace("|", "").strip()
        saldo_s = saldo_s.replace("|", "").strip()
        fecha = _parse_fecha(fecha_s)
        if not fecha:
            i += 1
            continue
        fila += 1
        mov = _mov(
            fecha=fecha,
            descripcion=desc.replace("|", " "),
            cargo=parse_monto_entero(cargo_s),
            abono=parse_monto_entero(abono_s),
            saldo=parse_monto_entero(saldo_s),
            documento=doc,
            codigo_sucursal=suc.replace("|", "").strip(),
            fila=fila,
        )
        if mov:
            movimientos.append(mov)
        i += 7

    if movimientos and not cab.get("saldo_final"):
        cab["saldo_final"] = movimientos[-1].get("saldo_bancario")
    return {"cabecera": cab, "movimientos": movimientos}


def parse_banco_chile(texto: str) -> dict:
    lineas = _lineas(texto)
    cab: dict[str, Any] = {
        "tipo_documento": "Estado de Cuenta",
        "tipo_cuenta_texto": "Cuenta Vista",
        "parser": "BANCO_CHILE",
        "fecha_sin_anio": True,
    }
    for i, lin in enumerate(lineas):
        if lin.upper() == "CUENTA VISTA" and i + 1 < len(lineas):
            cab["nombre_titular"] = lineas[i + 1].title()
            break
    valores = []
    for lin in lineas:
        m = re.match(r"^:\s*(.+)$", lin)
        if m:
            valores.append(m.group(1).strip())
    for v in valores:
        if re.fullmatch(r"X+\d+", v, re.I):
            cab["numero_cuenta_texto"] = v.upper()
            cab["numero_cuenta_enmascarado"] = v.upper()
            break
    for v in valores:
        if re.fullmatch(r"\d{2,4}", v) and not cab.get("numero_cartola"):
            cab["numero_cartola"] = v
    fechas = [v for v in valores if re.fullmatch(r"\d{2}/\d{2}/\d{4}", v)]
    if len(fechas) >= 2:
        cab["fecha_inicio_periodo"] = _parse_fecha(fechas[0])
        # en Chile a veces el segundo es emisión; el período hasta puede ser el mayor
        cab["fecha_fin_periodo"] = _parse_fecha(fechas[1])
        if cab["fecha_inicio_periodo"] and cab["fecha_fin_periodo"]:
            if cab["fecha_fin_periodo"] < cab["fecha_inicio_periodo"]:
                cab["fecha_inicio_periodo"], cab["fecha_fin_periodo"] = (
                    cab["fecha_fin_periodo"],
                    cab["fecha_inicio_periodo"],
                )
    # Ajuste típico Chile: DESDE 30/06, FECHA emisión 20/07 → período junio-julio
    # Usar fechas de movimientos para corregir si hace falta

    movimientos = []
    id_ini = "SALDO INICIAL"
    id_fin = "SALDO FINAL"
    for idx, lin in enumerate(lineas):
        if not re.match(r"^D\d{2}/\d{2}\b", lin):
            continue
        cuerpo = lin[1:]  # quita D
        m = re.match(r"^(\d{2}/\d{2})\s+(.*)$", cuerpo)
        if not m:
            continue
        ddmm, resto = m.group(1), m.group(2).strip()
        up = resto.upper()
        # montos al final
        montos = re.findall(r"([\d\.]+)", resto)
        # quitar números que son parte de texto tipo PAGO:1169 — tomar desde la derecha
        # Heurística: últimos 1–3 tokens numéricos con punto o enteros grandes
        tokens = resto.split()
        nums: list[int] = []
        for tok in reversed(tokens):
            limpio = tok.replace(",", "")
            if re.fullmatch(r"[\d\.]+", limpio):
                nums.append(parse_monto_entero(limpio))
                if len(nums) >= 3:
                    break
            else:
                if nums:
                    break
        n = len(nums)
        desc = " ".join(tokens[:-n]).strip() if n and n < len(tokens) else resto
        fecha = _fecha_sin_anio(
            ddmm, cab.get("fecha_inicio_periodo"), cab.get("fecha_fin_periodo")
        )
        if id_ini in up:
            if nums:
                cab["saldo_inicial"] = nums[0]
            continue
        if id_fin in up:
            if nums:
                cab["saldo_final"] = nums[0]
            continue

        cargo = abono = 0
        saldo = None
        if len(nums) == 2:
            # nums[0]=saldo (derecha), nums[1]=monto
            saldo, monto_op = nums[0], nums[1]
            if any(k in up for k in ("TRASPASO DE", "DEPOSITO", "DEPÓSITO", "ABONO")):
                abono = monto_op
            else:
                cargo = monto_op
        elif len(nums) >= 3:
            # derecha → izquierda: saldo, abono, cargo
            saldo, abono, cargo = nums[0], nums[1], nums[2]
        else:
            continue

        suc = ""
        for marca in ("CENTRAL", "INTERNET", "VIRTUAL"):
            if marca in desc.upper():
                suc = "CENTRAL" if marca == "CENTRAL" else marca.title()
                break
        mov = _mov(
            fecha=fecha,
            descripcion=desc,
            cargo=cargo,
            abono=abono,
            saldo=saldo,
            sucursal=suc,
            fila=idx + 1,
        )
        if mov and fecha:
            movimientos.append(mov)

    if movimientos:
        fechas_m = [m["fecha_operacion"] for m in movimientos if m.get("fecha_operacion")]
        if fechas_m:
            cab.setdefault("fecha_inicio_periodo", min(fechas_m))
            cab.setdefault("fecha_fin_periodo", max(fechas_m))
            # recalcular fechas sin año con período definitivo
            for mov in movimientos:
                # already set
                pass
    return {"cabecera": cab, "movimientos": movimientos}


def detectar_parser(banco: Banco, plantilla: PlantillaMapeoCartola | None = None) -> str:
    if plantilla and plantilla.parser_codigo != PlantillaMapeoCartola.ParserCodigo.GENERICO:
        return plantilla.parser_codigo
    nombre = (banco.nombre or "").casefold()
    if "falabella" in nombre:
        return PlantillaMapeoCartola.ParserCodigo.BANCO_FALABELLA
    if "estado" in nombre:
        return PlantillaMapeoCartola.ParserCodigo.BANCO_ESTADO
    if "chile" in nombre:
        return PlantillaMapeoCartola.ParserCodigo.BANCO_CHILE
    return PlantillaMapeoCartola.ParserCodigo.GENERICO


def parsear_cartola_pdf(
    *, banco: Banco, archivo, plantilla: PlantillaMapeoCartola | None = None
) -> dict:
    clave = obtener_clave_cartola(banco)
    if hasattr(archivo, "seek"):
        archivo.seek(0)
    texto = _texto_pdf(archivo, clave)
    if not texto.strip():
        raise ValidationError("El PDF no entregó texto legible.")
    parser = detectar_parser(banco, plantilla)
    if parser == PlantillaMapeoCartola.ParserCodigo.BANCO_FALABELLA:
        data = parse_falabella(texto)
    elif parser == PlantillaMapeoCartola.ParserCodigo.BANCO_ESTADO:
        data = parse_banco_estado(texto)
    elif parser == PlantillaMapeoCartola.ParserCodigo.BANCO_CHILE:
        data = parse_banco_chile(texto)
    else:
        raise ValidationError(
            "No hay parser PDF para este banco. Configure parser_codigo en la plantilla."
        )
    data["cabecera"]["parser"] = parser
    if not data["movimientos"]:
        raise ValidationError(
            "No se detectaron movimientos en el PDF. Revise la plantilla/parser."
        )
    cab = data["cabecera"]
    if not cab.get("fecha_inicio_periodo") or not cab.get("fecha_fin_periodo"):
        fechas = [m["fecha_operacion"] for m in data["movimientos"]]
        cab["fecha_inicio_periodo"] = min(fechas)
        cab["fecha_fin_periodo"] = max(fechas)
    return data

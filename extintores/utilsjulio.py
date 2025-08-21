from datetime import timedelta, date, datetime
from decimal import Decimal
import os

def obtener_factor(cliente, categoria):
    # Importación local para evitar circular import
    from .models import FactorAjusteCliente
    try:
        ajuste = FactorAjusteCliente.objects.get(cliente=cliente, categoria=categoria)
        return ajuste.factor
    except FactorAjusteCliente.DoesNotExist:
        return 1  # Si no hay ajuste, usa el factor estándar (sin cambio)

def calcular_ph_vencimiento(fecha, agente):
    if not fecha or not agente:
        return None, None

    hoy = date.today()
    agente_upper = agente.strip().upper()

    if agente_upper.startswith('PQS'):
        vencimiento = fecha + timedelta(days=365 * 12)
        estado = 'al_dia' if vencimiento >= hoy else 'vencido+12'
    else:
        vencimiento = fecha + timedelta(days=365 * 5)
        estado = 'al_dia' if vencimiento >= hoy else 'vencido+5'

    return vencimiento, estado


def calcular_ph_vencimiento_simple(ultima_fecha, agente):
    if not ultima_fecha or not agente:
        return None

    agente = agente.strip().upper()

    if agente.startswith('PQS'):
        return ultima_fecha + timedelta(days=365 * 12)
    else:
        return ultima_fecha + timedelta(days=365 * 5)


def upload_path(instance, filename):
    today = datetime.now()
    folder = today.strftime("%Y-%m")
    return os.path.join(f"intervenciones/{folder}/int_{instance.intervencion.id}", filename)

'''
def get_file_path1(instance, filename):
    # Obtener la fecha actual
    today = timezone.now()
    nombre_partida = instance.edt #[:70]
    # Combinar la fecha con el valor de edt y el nombre del archivo
    # Asegúrate de que `edt` esté disponible en la instancia
    return f'avance/{today.year}/{today.month}/{today.day}/{nombre_partida}_{filename}'
'''


def descontar_stock3(producto, cantidad):
    if producto.stock is None:
        producto.stock = Decimal('0.00')
    producto.stock -= Decimal(cantidad)
    producto.save()

def revertir_stock3(producto, cantidad):
    if producto.stock is None:
        producto.stock = Decimal('0.00')
    producto.stock += Decimal(cantidad)
    producto.save()

def descontar_stock(producto, cantidad):
    if producto.stock is not None:
        producto.stock = max(0, producto.stock - cantidad)
        producto.save()

def revertir_stock(producto, cantidad):
    if producto.stock is not None:
        producto.stock += cantidad
        producto.save()

def actualizar_stock_item_odt(item_nuevo, item_original=None):
    """
    Aplica los ajustes de stock correctos según el cambio entre el item_original (previo) y el item_nuevo (modificado).
    """
    if item_original is None:
        # Item nuevo
        descontar_stock(item_nuevo.producto, item_nuevo.cantidad)
    else:
        mismo_producto = item_original.producto.pk == item_nuevo.producto.pk
        diferencia = item_nuevo.cantidad - item_original.cantidad

        if mismo_producto:
            if diferencia != 0:
                # Ajuste por cambio de cantidad
                if diferencia > 0:
                    descontar_stock(item_nuevo.producto, diferencia)
                else:
                    revertir_stock(item_nuevo.producto, abs(diferencia))
        else:
            # Revertir stock al producto original
            revertir_stock(item_original.producto, item_original.cantidad)
            # Descontar stock del nuevo producto
            descontar_stock(item_nuevo.producto, item_nuevo.cantidad)



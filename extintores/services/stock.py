from decimal import Decimal
import unicodedata

from django.db import transaction

from ..models import Producto


class StockInsuficiente(Exception):
    """La operacion solicita mas unidades de las disponibles."""


def stock_es_ilimitado(producto):
    """Recarga and Mantencion never consume stock, regardless of stored value."""
    nombre = producto.categoria.nombre if producto.categoria else ''
    nombre = ''.join(c for c in unicodedata.normalize('NFD', nombre.lower())
                     if unicodedata.category(c) != 'Mn')
    return (
        nombre.startswith('recarga') or nombre.startswith('mantencion')
    )


def ajustar_stock(producto_id, delta):
    """Aplica un delta atomico; los productos finitos pueden quedar negativos."""
    delta = Decimal(str(delta))
    with transaction.atomic():
        producto = Producto.objects.select_for_update().get(pk=producto_id)
        if stock_es_ilimitado(producto):
            return None
        actual = producto.stock or Decimal('0')
        nuevo = actual + delta
        Producto.objects.filter(pk=producto.pk).update(stock=nuevo)
        return nuevo


def ajustar_cambio_item(producto_anterior_id, cantidad_anterior, producto_nuevo_id, cantidad_nueva):
    """Revierte el consumo anterior y aplica el nuevo sin dejar cambios parciales."""
    with transaction.atomic():
        ids = sorted({producto_anterior_id, producto_nuevo_id})
        productos = {
            p.pk: p for p in Producto.objects.select_for_update().filter(pk__in=ids)
        }
        if len(productos) != len(ids):
            raise Producto.DoesNotExist

        for producto_id, delta in (
            (producto_anterior_id, Decimal(str(cantidad_anterior))),
            (producto_nuevo_id, -Decimal(str(cantidad_nueva))),
        ):
            producto = productos[producto_id]
            if stock_es_ilimitado(producto):
                continue
            nuevo = (producto.stock or Decimal('0')) + delta
            producto.stock = nuevo
        Producto.objects.bulk_update(productos.values(), ['stock'])


def guardar_consumo_item(item):
    """Ajusta stock y persiste un consumo, todo dentro de una transaccion."""
    from ..models import ItemIntervencion

    with transaction.atomic():
        if item.pk:
            anterior = ItemIntervencion.objects.select_for_update().get(pk=item.pk)
            if anterior.producto_id == item.producto_id:
                ajustar_stock(item.producto_id, anterior.cantidad - item.cantidad)
            else:
                ajustar_cambio_item(
                    anterior.producto_id, anterior.cantidad,
                    item.producto_id, item.cantidad,
                )
        else:
            ajustar_stock(item.producto_id, -item.cantidad)
        item.save()


def eliminar_consumo_item(item):
    with transaction.atomic():
        ajustar_stock(item.producto_id, item.cantidad)
        item.delete()

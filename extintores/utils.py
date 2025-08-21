from datetime import timedelta, date, datetime
from decimal import Decimal
import os
from django.utils.timezone import now
from collections import Counter
from django.db.models import Sum
from datetime import datetime
from django.apps import apps
from django.utils.timezone import now
from django.db.models import Sum, Count
from django.utils.timezone import now
from django.apps import apps
from django.db.models import Count, Sum
from django.db import IntegrityError


from django.db.models import Count, Sum, F
from django.utils.timezone import now
from django.apps import apps
#from .models import DetalleIntervencion

from django.db.models import Sum, F, DecimalField, ExpressionWrapper
#from .models import ItemOdt, EstadisticaDetalleExtintor, EstadisticaProducto
from django.utils.timezone import now
from datetime import datetime

def generar_estadisticas_mensuales(mes=None):
    if mes is None:
        mes = now().strftime('%Y-%m')

    fecha_inicio = datetime.strptime(mes, "%Y-%m")
    fecha_fin = datetime(fecha_inicio.year + int(fecha_inicio.month == 12), 
                         fecha_inicio.month % 12 + 1, 1)

    # Agrupar extintores
    detalle_queryset = DetalleIntervencion.objects.filter(
        intervencion__fecha__gte=fecha_inicio,
        intervencion__fecha__lt=fecha_fin
    ).values(
        'intervencion__cliente',
        'tipo_intervencion',
        'agente',
        'peso'
    ).annotate(
        total_extintores=Sum('cantidad')
    )

    for entry in detalle_queryset:
        EstadisticaDetalleExtintor.objects.update_or_create(
            mes=mes,
            cliente_id=entry['intervencion__cliente'],
            tipo_intervencion=entry['tipo_intervencion'],
            agente=entry['agente'],
            peso=entry['peso'],
            defaults={
                'total_extintores': entry['total_extintores']
            }
        )

    # Agrupar productos (sumar cantidad y total valorizado)
    item_queryset = ItemOdt.objects.filter(
        detalle_odt__odt__fecha__gte=fecha_inicio,
        detalle_odt__odt__fecha__lt=fecha_fin
    ).values(
        'detalle_odt__odt__cliente',
        'producto',
        'producto__nombre'
    ).annotate(
        total_cantidad=Sum('cantidad'),
        total_valor=Sum(
            ExpressionWrapper(
                F('cantidad') * F('producto__precio_unitario'),
                output_field=DecimalField()
            )
        )
    )

    for entry in item_queryset:
        EstadisticaProducto.objects.update_or_create(
            mes=mes,
            cliente_id=entry['detalle_odt__odt__cliente'],
            producto_id=entry['producto'],
            defaults={
                'nombre_producto': entry['producto__nombre'],
                'cantidad_total': entry['total_cantidad'],
                'total_valorizado': entry['total_valor']
            }
        )


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



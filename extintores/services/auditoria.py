import logging

from ..models import Bitacora

logger = logging.getLogger(__name__)


def obtener_ip(request):
    """Uses forwarded IP only when the deployment explicitly provides it."""
    if not request:
        return None
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def registrar_evento(*, request=None, accion, modelo='', objeto=None,
                     objeto_id=None, descripcion='', resultado='exito',
                     datos_anteriores=None, datos_nuevos=None, metadatos=None,
                     usuario=None):
    """Stores an audit event without interrupting the business operation."""
    try:
        if objeto is not None:
            modelo = objeto.__class__.__name__
            objeto_id = getattr(objeto, 'pk', objeto_id)
        if usuario is None and request is not None:
            usuario = request.user if request.user.is_authenticated else None
        return Bitacora.objects.create(
            usuario=usuario, accion=accion, modelo=modelo, objeto_id=objeto_id,
            descripcion=descripcion, resultado=resultado,
            url=request.path if request else '',
            metodo=request.method if request else '', ip=obtener_ip(request),
            datos_anteriores=datos_anteriores, datos_nuevos=datos_nuevos,
            metadatos=metadatos,
        )
    except Exception:
        logger.exception('No fue posible registrar evento de auditoria')
        return None

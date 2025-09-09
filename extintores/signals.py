# signals.py (activar creacion automatica de ODT)
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Intervencion, Odt, DetalleOdt,\
                    HistorialServicio, Cliente

@receiver(post_save, sender=Intervencion)
def crear_odt_si_corresponde(sender, instance, created, **kwargs):
    if instance.con_odt and not hasattr(instance, 'odt'):
        odt = Odt.objects.create(intervencion=instance)
        for d in instance.detalles.all():
            DetalleOdt.objects.create(
                odt=odt,
                ubicacion=d.ubicacion,
                agente=d.agente,
                presion=d.presion,
                ph_ultima=d.ph_ultima,
                ph_estado=d.ph_estado,
                ph_vencimiento=d.ph_vencimiento,
            )

@receiver(post_save, sender=Intervencion)
def actualizar_cliente_despues_intervencion(sender, instance, created, **kwargs):
    cliente = instance.cliente

    if created:
        # Crear historial solo al crear una intervención nueva
        HistorialServicio.objects.create(
            cliente=cliente,
            intervencion=instance,
            fecha=instance.fecha,
            alias=instance.alias
        )

    # Siempre actualizamos los campos rápidos del cliente
    cliente.fecha_ultima_intervencion = instance.fecha
    cliente.ultima_intervencion = instance
    cliente.ultimo_alias = instance.alias
    cliente.save()

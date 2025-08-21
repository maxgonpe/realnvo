# signals.py (activar creacion automatica de ODT)
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Intervencion, Odt, DetalleOdt

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

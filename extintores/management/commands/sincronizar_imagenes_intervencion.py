from django.core.management.base import BaseCommand, CommandError

from extintores.models import ImagenIntervencion, ImagenServicio, Intervencion


class Command(BaseCommand):
    help = 'Reemplaza ImagenServicio por las fotos vigentes de ImagenIntervencion.'

    def add_arguments(self, parser):
        parser.add_argument('intervencion_ids', nargs='+', type=int)

    def handle(self, *args, **options):
        for intervencion_id in options['intervencion_ids']:
            intervencion = Intervencion.objects.filter(pk=intervencion_id).first()
            if not intervencion:
                raise CommandError(f'No existe la intervencion #{intervencion_id}.')

            legacy = ImagenIntervencion.objects.filter(
                intervencion=intervencion
            ).first()
            if not legacy:
                raise CommandError(
                    f'La intervencion #{intervencion_id} no tiene ImagenIntervencion.'
                )

            actuales = {
                getattr(legacy, f'imagen{orden}').name
                for orden in range(1, 10)
                if getattr(legacy, f'imagen{orden}')
            }
            for imagen in list(intervencion.imagenes_nuevas.all()):
                if imagen.archivo.name not in actuales:
                    imagen.archivo.delete(save=False)
                imagen.delete()

            for orden in range(1, 10):
                archivo = getattr(legacy, f'imagen{orden}')
                if archivo:
                    ImagenServicio.objects.create(
                        intervencion=intervencion,
                        archivo=archivo.name,
                        orden=orden,
                    )

            self.stdout.write(self.style.SUCCESS(
                f'Intervencion #{intervencion_id}: sincronizada.'
            ))

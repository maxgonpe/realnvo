from .utils import calcular_ph_vencimiento
from django.db import models
from django.utils import timezone 
from .utils import upload_path
from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import Group
import os
from datetime import datetime
from decimal import Decimal



AGENTE_CHOICES = [
    ('PQS_40%','PQS_40%'),
    ('PQS_50%','PQS_50%'),
    ('PQS_55%','PQS_55%'),
    ('PQS_70%','PQS_70%'),
    ('PQS_75%','PQS_75%'),
    ('PQS_90%','PQS_90%'),
    ('CO2','CO2'),
    ('AGUA','AGUA'),
    ('Tipo K','Tipo K'),
    ('AFFF 3%','AFFF 3%'),
    ('CF302 6%', 'CF302 6%'),
    ('CF302 10%', 'CF302 10%'),
    ('otro','otro'),
    ]

TIPO_INTERVENCION_CHOICES = [
    ('revision', 'Revisión'),
    ('mantencion', 'Mantención'),
    ('recarga', 'Recarga'),
    ('venta', 'Venta'),
    ]

ESTADO_CHOICES = [
    ('operativo', 'Operativo'),
    ('f/servicio', 'Fuera/Servicio'),
    ('ph/venci.', 'PH/Vencida'),
    ('f/de/norma', 'Fuera/de/Norma'),
    ('baja/oxido', 'Baja/Oxido'),
    ('extin./abo.', 'Extintor/Abollado'),
    ('habili.+1', 'habilitado +1 año'),
    ('nuevo','Nuevo'),
    ('pendiente', 'Pendiente'),
    ('otro','Otro'),
]

PH_CHOICES = [
    ('al_dia', 'Al día'),
    ('vencido+5', 'Vencido +5 años CO2'),
    ('vencido+12', 'Vencido +12 años PQS'),

]

PRESION_CHOICES = [
    ('120', '120 PSI'),
    ('195', '195 PSI'),
    ('150', '150 PSI'),
    ('650', '650 PSI'),
    ('850', '850 PSI'),
    ('250', '250 BAR'),
]

CATEGORIA_CHOICES = [
        ('producto', 'Producto'),
        ('recarga 40%', 'Recarga 40%'),
        ('recarga 75%', 'Recarga 75%'),
        ('mantencion', 'Mantencion'),
        ('accesorio', 'Accesorio'),
        ('otro', 'Otro'),
    ]

PESO_CHOICES = (
    ('1 kg','1 kg',),
    ('2 kg','2 kg'),
    ('3 kg','3 kg'),
    ('4 Kg','4 Kg'),
    ('5 Kg','5 Kg'),
    ('6 Kg','6 Kg'),
    ('8 Kg','8 Kg'),
    ('10 Kg','10 Kg'),
    ('25 Kg','25 Kg'),
    ('50 Kg','50 Kg'),
    ('100 Kg','100 Kg'),
    ('6 Lt','6 Lt'),
    ('10 Lt','10 Lt'),
    ('25 Lt','25 Lt'),
    ('50 Lt','50 Lt'),


    )


@receiver(post_save, sender=User)
def assign_technician_profile(sender, instance, created, **kwargs):
    grupo_tecnicos, _ = Group.objects.get_or_create(name='Técnicos')
    
    if created and instance.groups.filter(name='Técnicos').exists():
        TechnicianProfile.objects.get_or_create(user=instance)
    
    # Si se añade al grupo después
    if not created and instance.groups.filter(name='Técnicos').exists():
        if not hasattr(instance, 'technician_profile'):
            TechnicianProfile.objects.create(user=instance)

class TechnicianProfile(models.Model):
    user = models.OneToOneField(
        get_user_model(), 
        on_delete=models.CASCADE,
        related_name='technician_profile'
    )
    professional_id = models.CharField(
        "N° Identificación Profesional", 
        max_length=50, 
        blank=True
    )
    rut = models.CharField(
        "Rut", 
        max_length=50, 
        blank=True
    )
    
    specialization = models.CharField(
        "Especialidad", 
        max_length=100, 
        blank=True
    )
    hire_date = models.DateField(
        "Fecha de Contratación", 
        auto_now_add=True
    )
    signature = models.ImageField(
        "Firma Electrónica",
        upload_to='tecnicos/firmas/',  # Ruta de almacenamiento
        blank=True,
        null=True
    )

    def get_full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"

# Signal para crear automáticamente el perfil al crear un User
@receiver(post_save, sender=User)
def create_technician_profile(sender, instance, created, **kwargs):
    if created and instance.groups.filter(name='Técnicos').exists():
        TechnicianProfile.objects.create(user=instance)



class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    rut = models.CharField(max_length=100,blank=True)
    correo = models.CharField(max_length=100,blank=True)
    direccion = models.CharField(max_length=150, blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    contacto = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Intervencion(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_INTERVENCION_CHOICES)
    fecha = models.DateField(default=timezone.now)
    tecnico = models.ForeignKey(
        User,  # ✅ Debe ser User, no TechnicianProfile
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Técnico",
        related_name='intervenciones'
    )
    odt = models.IntegerField(blank=True, null=True)
    con_odt = models.BooleanField(default=False)
    alias = models.CharField(max_length=50, unique=True, blank=True, null=True)
    notas = models.TextField(blank=True, null=True)
    

    def __str__(self):
        return f"{self.get_tipo_display()} {self.pk} - {self.cliente}"


class DetalleIntervencion(models.Model):
    intervencion = models.ForeignKey(Intervencion, related_name='detalles', on_delete=models.CASCADE)
    agente = models.CharField(max_length=100,choices=AGENTE_CHOICES, blank=True)
    nro_precinto = models.IntegerField(blank=True,null=True)
    ubicacion = models.CharField(max_length=150, blank=True)
    sello_incen = models.CharField(max_length=150, blank=True, default='S/I')
    sello_incen_ste = models.CharField(max_length=50, blank=True, default='S/I')
    certificado = models.CharField(max_length=50, blank=True, default='S/I')
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES,blank=True)
    exterior = models.BooleanField(default=True)
    ph_ultima = models.DateField(null=True, blank=True)
    ph_estado = models.CharField(max_length=50, blank=True, null=True)
    ph_vencimiento = models.DateField(null=True, blank=True)
    valvula = models.BooleanField(default=True)
    manometro = models.BooleanField(default=True)
    manguera = models.BooleanField(default=True)
    cintillo = models.BooleanField(default=True)
    agente_extintor = models.BooleanField(default=True)
    tubo_sifon = models.BooleanField(default=True)
    sellos_seguro = models.BooleanField(default=True)
    seguridad = models.BooleanField(default=True)
    rotulacion = models.BooleanField(default=True)
    ultima_fecha = models.DateField(null=True, blank=True)
    recarga = models.BooleanField(default=True)
    mantencion = models.BooleanField(default=True)
    presion = models.CharField(max_length=50, choices=PRESION_CHOICES, blank=True)
    peso = models.CharField(max_length=50, choices=PESO_CHOICES, blank=True)
    correcta = models.BooleanField(default=True)
    acceso = models.BooleanField(default=True)
    instrucciones = models.BooleanField(default=True)
    habilitado_un_ano = models.BooleanField(default=False)
    baja_por_oxido = models.BooleanField(default=False)
    baja_por_ph = models.BooleanField(default=False)
    baja_por_fuera_norma = models.BooleanField(default=False)
    extintor_abollado = models.BooleanField(default=False)
    baja_otro = models.BooleanField(default=False)
    extintor_nuevo = models.BooleanField(default=False)
    
    
    def save(self, *args, **kwargs):
        if self.ph_ultima and self.agente:
            self.ph_vencimiento, self.ph_estado = calcular_ph_vencimiento(self.ph_ultima, self.agente)
        
        super().save(*args, **kwargs)


    def __str__(self):
        return f"Extintor #{self.pk} - {self.agente} - {self.estado}"


class Odt(models.Model):
    intervencion = models.OneToOneField(Intervencion, on_delete=models.CASCADE, related_name='odt_rel')
    fecha = models.DateField(auto_now_add=True)
    estatus = models.BooleanField(default=False)  # Cerrada o no
    alias = models.CharField(max_length=50, unique=True, blank=True, null=True)
    tecnico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='odts')
    observaciones = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)  # Guardar primero si es nuevo

        if is_new and not self.alias:
            self.alias = f"ODT-{self.pk}"
            super().save(update_fields=['alias'])

    def __str__(self):
        return f"{self.alias or f'ODT #{self.pk}'} - {self.intervencion}"

    #def __str__(self):
    #    return f"ODT #{self.pk} - {self.intervencion}"


class DetalleOdt(models.Model):
    odt = models.ForeignKey(Odt, on_delete=models.CASCADE, related_name='detalles')
    #observaciones = models.TextField(blank=True, null=True)
    #costo_materiales = models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    ######
    agente = models.CharField(max_length=100,choices=AGENTE_CHOICES)
    nro_precinto = models.IntegerField(blank=True,null=True)
    ubicacion = models.CharField(max_length=150, blank=True)
    sello_incen = models.CharField(max_length=150, blank=True, default='S/I')
    sello_incen_ste = models.CharField(max_length=50, blank=True, default='S/I')
    certificado = models.CharField(max_length=50, blank=True, default='S/I')
    estado = models.CharField(max_length=50, choices=ESTADO_CHOICES)
    exterior = models.BooleanField(default=True)
    ph_ultima = models.DateField(null=True, blank=True)
    ph_estado = models.CharField(max_length=50, blank=True, null=True)
    ph_vencimiento = models.DateField(null=True, blank=True)
    valvula = models.BooleanField(default=True)
    manometro = models.BooleanField(default=True)
    manguera = models.BooleanField(default=True)
    cintillo = models.BooleanField(default=True)
    agente_extintor = models.BooleanField(default=True)
    tubo_sifon = models.BooleanField(default=True)
    sellos_seguro = models.BooleanField(default=True)
    seguridad = models.BooleanField(default=True)
    rotulacion = models.BooleanField(default=True)
    ultima_fecha = models.DateField(null=True, blank=True)
    recarga = models.BooleanField(default=True)
    mantencion = models.BooleanField(default=True)
    presion = models.CharField(max_length=50, choices=PRESION_CHOICES)
    peso = models.CharField(max_length=50, choices=PESO_CHOICES)
    correcta = models.BooleanField(default=True)
    acceso = models.BooleanField(default=True)
    instrucciones = models.BooleanField(default=True)
    ######

    def save(self, *args, **kwargs):
        if self.ph_ultima and self.agente:
            self.ph_vencimiento, self.ph_estado = calcular_ph_vencimiento(self.ph_ultima, self.agente)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Detalle #{self.pk} de ODT #{self.odt.pk}"

class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    componentes_relacionados = models.ManyToManyField('self', blank=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.SET_NULL, null=True)
    #categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    compatibilidad = models.ManyToManyField(DetalleOdt, through='CompatibilidadProducto')
    stock = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        # Acceder al nombre de la categoría, no a la instancia completa
        return f"{self.categoria.nombre if self.categoria else 'Sin categoría'} - {self.nombre}"


class CompatibilidadProducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    detalle_odt = models.ForeignKey(DetalleOdt, on_delete=models.CASCADE)
    motivo = models.TextField(blank=True,null=True)
    fecha_registro = models.DateField(auto_now_add=True)





class ItemOdt(models.Model):
    odt = models.ForeignKey(Odt, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # snapshot
    precio_con_factor = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # precio ajustado si aplica
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # snapshot

    def save(self, *args, **kwargs):
        from .utils import obtener_factor
        #factor = obtener_factor(self.odt.intervencion.cliente, self.producto.categoria)
        if self.producto and self.odt and self.odt.intervencion and self.odt.intervencion.cliente:
            factor = obtener_factor(self.odt.intervencion.cliente, self.producto.categoria)
        else:
            factor = Decimal('1.0')  # fallback

        self.precio_unitario = self.producto.precio_unitario
        if factor != 1:
            self.precio_con_factor = self.producto.precio_unitario * factor
            self.subtotal = self.cantidad * self.precio_con_factor
        else:
            self.precio_con_factor = None
            self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)


class ImagenIntervencion(models.Model):
    intervencion = models.ForeignKey('Intervencion', related_name='imagenes', on_delete=models.CASCADE)
    imagen1 = models.ImageField(upload_to=upload_path, verbose_name='Imagen1',blank=True, null=True)
    imagen2 = models.ImageField(upload_to=upload_path, verbose_name='Imagen2',blank=True, null=True)
    imagen3 = models.ImageField(upload_to=upload_path, verbose_name='Imagen3',blank=True, null=True)
    imagen4 = models.ImageField(upload_to=upload_path, verbose_name='Imagen4',blank=True, null=True)
    imagen5 = models.ImageField(upload_to=upload_path, verbose_name='Imagen5',blank=True, null=True)
    imagen6 = models.ImageField(upload_to=upload_path, verbose_name='Imagen6',blank=True, null=True)
    imagen7 = models.ImageField(upload_to=upload_path, verbose_name='Imagen7',blank=True, null=True)
    imagen8 = models.ImageField(upload_to=upload_path, verbose_name='Imagen8',blank=True, null=True)
    imagen9 = models.ImageField(upload_to=upload_path, verbose_name='Imagen9',blank=True, null=True)
    #default='/iconos/reloj-rojo.png', verbose_name='Imagen',blank=True)

    def __str__(self):
        return f"Imagen de Intervencion #{self.intervencion.pk}"

    def ruta_imagen_intervencion(instance, filename):
        mes = instance.fecha.strftime('%Y-%m')
        return f'intervenciones/{mes}/intervencion_{instance.pk}/{filename}'

    def intervencion_image_upload_path(instance, filename):
        fecha = datetime.now()
        return f"intervenciones/{fecha.strftime('%Y-%m')}/intervencion_{instance.intervencion.pk}/{filename}"


class Bitacora(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    accion = models.CharField(max_length=255)
    modelo = models.CharField(max_length=100, blank=True)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.TextField(blank=True)
    fecha = models.DateTimeField(auto_now_add=True)


class FactorAjusteCliente(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE)
    factor = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)

    def __str__(self):
        return f"{self.cliente} - {self.categoria} - {self.factor}"
   

class IngresoStock(models.Model):
    fecha = models.DateField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Ingreso #{self.pk} - {self.fecha}"


class DetalleIngreso(models.Model):
    ingreso = models.ForeignKey(IngresoStock, related_name='detalles', on_delete=models.CASCADE)
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Al guardar, suma al stock del producto
        if self.producto.stock is None:
            self.producto.stock = 0
        self.producto.stock += self.cantidad
        self.producto.save()

    def __str__(self):
        return f"{self.producto.nombre} +{self.cantidad} (Ingreso #{self.ingreso.pk})"



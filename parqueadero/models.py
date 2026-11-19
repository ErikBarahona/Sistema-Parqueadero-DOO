"""Modelo del SAGP: 13 clases persistentes con su comportamiento (programación orientada a objetos).

Cada clase tiene sus atributos (columnas), relaciones y los métodos de negocio del diagrama de clases.
Las operaciones críticas se ejecutan dentro de transacciones con bloqueo de filas (select_for_update).
"""
import datetime
import re

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, F, Q
from django.utils import timezone

from .excepciones import Denegado, ErrorNegocio

TIPOS_VEHICULO = [('CARRO', 'Carro'), ('MOTO', 'Moto'), ('BICICLETA', 'Bicicleta')]
TIPOS_ESPACIO = [('CARRO', 'Carro'), ('MOTO', 'Moto'), ('BICICLETA', 'Bicicleta'),
                 ('DISCAPACITADOS', 'Discapacitados'), ('VISITANTE', 'Visitante')]
ESTADOS_ESPACIO = [('LIBRE', 'Libre'), ('OCUPADO', 'Ocupado'),
                   ('BLOQUEADO', 'Bloqueado'), ('MANTENIMIENTO', 'En mantenimiento')]
ESTADOS_ACCESO = [('ACTIVO', 'Activo'), ('FINALIZADO', 'Finalizado')]
PLACA_RE = re.compile(r'^[A-Z0-9]{5,10}$')


# =====================================================================================
class Parqueadero(models.Model):
    id_parqueadero = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    capacidad = models.PositiveIntegerField(default=1)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'parqueadero'

    def __str__(self):
        return self.nombre

    def consultar_ocupacion(self):
        """RF-33: ocupación y disponibilidad por tipo de espacio."""
        return Espacio.ocupacion_por_tipo(self)


# =====================================================================================
class Apartamento(models.Model):
    id_apartamento = models.AutoField(primary_key=True)
    parqueadero = models.ForeignKey(Parqueadero, on_delete=models.PROTECT,
                                    db_column='id_parqueadero', related_name='apartamentos')
    numero = models.CharField(max_length=10)
    propietario = models.CharField(max_length=100)
    max_vehiculos = models.PositiveIntegerField(default=1)
    estado = models.BooleanField(default=True)

    class Meta:
        db_table = 'apartamento'
        constraints = [models.UniqueConstraint(fields=['parqueadero', 'numero'], name='uq_apartamento_numero')]

    def __str__(self):
        return f'Apto {self.numero} - {self.propietario}'

    def vehiculos_activos(self):
        return self.vehiculos.filter(estado=True)

    def cupo_disponible(self, excluir_pk=None):
        """RF-10: cuántos vehículos más puede registrar el apartamento."""
        return self.max_vehiculos - self.vehiculos_activos().exclude(pk=excluir_pk).count()

    def residentes_activos(self):
        return self.usuarios.filter(rol='RESIDENTE', estado=True)

    def visitas_activas(self):
        return self.visitas.filter(estado='ACTIVO')

    def definir_max_vehiculos(self, maximo):
        self.max_vehiculos = maximo
        self.save(update_fields=['max_vehiculos'])

    def dar_de_baja(self):
        """RF-09: baja lógica, se conserva el historial."""
        self.estado = False
        self.save(update_fields=['estado'])


# =====================================================================================
class UsuarioManager(BaseUserManager):
    def _crear(self, usuario, password, **extra):
        if not usuario:
            raise ValueError('El nombre de usuario es obligatorio')
        user = self.model(usuario=usuario, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, usuario, password=None, **extra):
        extra.setdefault('rol', 'RESIDENTE')
        return self._crear(usuario, password, **extra)

    def create_superuser(self, usuario, password=None, **extra):
        extra['rol'] = 'ADMINISTRADOR'
        return self._crear(usuario, password, **extra)


class Usuario(AbstractBaseUser):
    ROLES = [('ADMINISTRADOR', 'Administrador'), ('RESIDENTE', 'Residente autorizado'), ('AUDITOR', 'Auditor')]

    id_usuario = models.AutoField(primary_key=True)
    apartamento = models.ForeignKey(Apartamento, null=True, blank=True, on_delete=models.PROTECT,
                                    db_column='id_apartamento', related_name='usuarios')
    nombre = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(max_length=100, unique=True)
    usuario = models.CharField(max_length=50, unique=True)
    password = models.CharField('clave_hash', max_length=255, db_column='clave_hash')
    rol = models.CharField(max_length=20, choices=ROLES, default='RESIDENTE')
    estado = models.BooleanField(default=True)
    intentos_fallidos = models.PositiveIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'usuario'
    REQUIRED_FIELDS = ['nombre', 'cedula', 'correo']
    objects = UsuarioManager()

    class Meta:
        db_table = 'usuario'
        constraints = [
            models.CheckConstraint(condition=~Q(rol='RESIDENTE') | Q(apartamento__isnull=False),
                                   name='ck_residente_apartamento'),
        ]

    @property
    def is_active(self):
        return self.estado

    def __str__(self):
        return self.nombre

    # --- autenticación (RF-01, RF-05) ---
    @classmethod
    def autenticar(cls, request, nombre, clave):
        """Devuelve el usuario autenticado o lanza ErrorNegocio. Bloquea la cuenta tras varios fallos."""
        candidato = cls.objects.filter(usuario=nombre).first()
        if candidato and candidato.esta_bloqueado():
            raise ErrorNegocio('La cuenta está bloqueada temporalmente por intentos fallidos. Intente más tarde.')
        user = authenticate(request, username=nombre, password=clave)
        if user is not None:
            user.registrar_ingreso_exitoso()
            return user
        if candidato:
            candidato.registrar_intento_fallido()
        raise ErrorNegocio('Usuario o contraseña incorrectos, o usuario inactivo.')

    def esta_bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    def registrar_intento_fallido(self):
        self.intentos_fallidos += 1
        if self.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
            self.bloqueado_hasta = timezone.now() + datetime.timedelta(minutes=settings.LOGIN_BLOQUEO_MIN)
            self.intentos_fallidos = 0
        self.save(update_fields=['intentos_fallidos', 'bloqueado_hasta'])

    def registrar_ingreso_exitoso(self):
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        type(self).objects.filter(pk=self.pk).update(intentos_fallidos=0, bloqueado_hasta=None)

    def cambiar_clave(self, nueva):
        self.set_password(nueva)
        self.save(update_fields=['password'])

    def activar(self):
        self.estado = True
        self.save(update_fields=['estado'])

    def desactivar(self):
        self.estado = False
        self.save(update_fields=['estado'])

    # --- autorización (RF-06, RF-18, RF-37, RF-38, RF-40) ---
    def puede_operar(self):
        """Activo y con permiso vigente (el administrador siempre puede)."""
        if not self.estado:
            return False
        if self.rol == 'ADMINISTRADOR':
            return True
        if self.rol != 'RESIDENTE':
            return False
        hoy = timezone.localdate()
        return self.permisos.filter(estado=True, fecha_inicio__lte=hoy).filter(
            Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=hoy)).exists()

    def esta_autorizado_para(self, vehiculo):
        """RF-18: puede operar y está autorizado para ese vehículo."""
        if not self.puede_operar():
            return False
        if self.rol == 'ADMINISTRADOR':
            return True
        return vehiculo.autorizados.filter(pk=self.pk).exists()


# =====================================================================================
class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    apartamento = models.ForeignKey(Apartamento, on_delete=models.PROTECT,
                                    db_column='id_apartamento', related_name='vehiculos')
    placa = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    tipo = models.CharField(max_length=20, choices=TIPOS_VEHICULO)
    estado = models.BooleanField(default=True)
    autorizados = models.ManyToManyField(Usuario, through='UsuarioVehiculo', related_name='vehiculos_autorizados')

    class Meta:
        db_table = 'vehiculo'

    def __str__(self):
        return self.placa

    @staticmethod
    def normalizar_placa(placa):
        return (placa or '').upper().replace(' ', '').replace('-', '').strip()

    @classmethod
    def validar_placa(cls, placa, obligatoria=True):
        """RF-12: placa en mayúsculas, de 5 a 10 caracteres alfanuméricos."""
        placa = cls.normalizar_placa(placa)
        if not placa and not obligatoria:
            return ''
        if not PLACA_RE.match(placa):
            raise ValidationError('La placa debe tener entre 5 y 10 caracteres, solo letras y números.')
        return placa

    @classmethod
    def visibles_para(cls, usuario):
        qs = cls.objects.select_related('apartamento')
        if usuario.rol == 'RESIDENTE':
            qs = qs.filter(apartamento_id=usuario.apartamento_id)
        return qs

    def acceso_activo(self):
        return self.accesos.filter(estado='ACTIVO').first()

    def esta_dentro(self):
        return self.accesos.filter(estado='ACTIVO').exists()

    def desactivar(self):
        self.estado = False
        self.save(update_fields=['estado'])

    def autorizar_usuarios(self, usuarios):
        """RF-14: define quiénes pueden retirar el vehículo (por defecto, los residentes del apartamento)."""
        usuarios = list(usuarios) or list(self.apartamento.residentes_activos())
        UsuarioVehiculo.objects.filter(vehiculo=self).exclude(usuario__in=usuarios).delete()
        for u in usuarios:
            UsuarioVehiculo.objects.get_or_create(vehiculo=self, usuario=u)

    def propietarios_a_notificar(self):
        return self.autorizados.filter(estado=True)


class UsuarioVehiculo(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.CASCADE, db_column='id_vehiculo')

    class Meta:
        db_table = 'usuario_vehiculo'
        constraints = [models.UniqueConstraint(fields=['usuario', 'vehiculo'], name='uq_usuario_vehiculo')]


# =====================================================================================
class Espacio(models.Model):
    id_espacio = models.AutoField(primary_key=True)
    parqueadero = models.ForeignKey(Parqueadero, on_delete=models.PROTECT,
                                    db_column='id_parqueadero', related_name='espacios')
    apartamento = models.ForeignKey(Apartamento, null=True, blank=True, on_delete=models.SET_NULL,
                                    db_column='id_apartamento', related_name='espacios')
    identificador = models.CharField(max_length=10)
    zona = models.CharField(max_length=30, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS_ESPACIO)
    estado = models.CharField(max_length=20, choices=ESTADOS_ESPACIO, default='LIBRE')

    class Meta:
        db_table = 'espacio'
        constraints = [models.UniqueConstraint(fields=['parqueadero', 'identificador'],
                                               name='uq_espacio_identificador')]

    def __str__(self):
        return f'{self.identificador} ({self.get_tipo_display()})'

    @classmethod
    def ocupacion_por_tipo(cls, parqueadero=None):
        qs = cls.objects.all()
        if parqueadero is not None:
            qs = qs.filter(parqueadero=parqueadero)
        return (qs.values('tipo')
                .annotate(total=Count('pk'), ocupados=Count('pk', filter=Q(estado='OCUPADO')),
                          libres=Count('pk', filter=Q(estado='LIBRE')),
                          no_disp=Count('pk', filter=Q(estado__in=['BLOQUEADO', 'MANTENIMIENTO'])))
                .order_by('tipo'))

    @classmethod
    def buscar_libre(cls, tipo, apartamento):
        """Primero un espacio asignado al apartamento y, si no hay, uno común. Requiere transacción."""
        qs = cls.objects.select_for_update().filter(estado='LIBRE', tipo=tipo).order_by('identificador')
        return qs.filter(apartamento=apartamento).first() or qs.filter(apartamento__isnull=True).first()

    @classmethod
    def buscar_libre_visitante(cls):
        return (cls.objects.select_for_update().filter(estado='LIBRE', tipo='VISITANTE')
                .order_by('identificador').first())

    def esta_en_uso(self):
        return (self.accesos.filter(estado='ACTIVO').exists() or self.visitas.filter(estado='ACTIVO').exists())

    def ocupar(self):
        self.estado = 'OCUPADO'
        self.save(update_fields=['estado'])

    def liberar(self):
        if self.estado == 'OCUPADO':
            self.estado = 'LIBRE'
            self.save(update_fields=['estado'])

    def bloquear(self):
        """RF-36."""
        self.estado = 'BLOQUEADO'
        self.save(update_fields=['estado'])

    def asignar_apartamento(self, apartamento):
        """RF-32: espacio fijo (apartamento) o común (None)."""
        self.apartamento = apartamento
        self.save(update_fields=['apartamento'])


# =====================================================================================
class RegistroAcceso(models.Model):
    id_registro = models.AutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, on_delete=models.PROTECT, db_column='id_vehiculo',
                                 related_name='accesos')
    espacio = models.ForeignKey(Espacio, on_delete=models.PROTECT, db_column='id_espacio',
                                related_name='accesos')
    usuario_entrada = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column='id_usuario_entrada',
                                        related_name='accesos_entrada')
    usuario_salida = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.PROTECT,
                                       db_column='id_usuario_salida', related_name='accesos_salida')
    fecha_hora_entrada = models.DateTimeField(default=timezone.now)
    fecha_hora_salida = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=15, choices=ESTADOS_ACCESO, default='ACTIVO')

    class Meta:
        db_table = 'registro_acceso'
        constraints = [
            # RF-21: un vehículo no puede tener dos entradas activas
            models.UniqueConstraint(fields=['vehiculo'], condition=Q(estado='ACTIVO'),
                                    name='uq_acceso_vehiculo_activo'),
            # un espacio no puede estar ocupado por dos vehículos a la vez
            models.UniqueConstraint(fields=['espacio'], condition=Q(estado='ACTIVO'),
                                    name='uq_acceso_espacio_activo'),
            models.CheckConstraint(
                condition=Q(fecha_hora_salida__isnull=True) | Q(fecha_hora_salida__gte=F('fecha_hora_entrada')),
                name='ck_acceso_fechas'),
        ]

    @classmethod
    def activos(cls):
        return cls.objects.filter(estado='ACTIVO')

    @classmethod
    def registrar_entrada(cls, usuario, placa):
        """RF-15, RF-17, RF-20, RF-21, RF-22, RF-35."""
        placa = Vehiculo.normalizar_placa(placa)
        vehiculo = None
        try:
            with transaction.atomic():
                vehiculo = Vehiculo.objects.select_for_update().filter(placa=placa).first()
                if vehiculo is None or not vehiculo.estado:
                    raise Denegado('ENTRADA_NO_AUTORIZADA',
                                   'Entrada denegada: el vehículo no está registrado o está inactivo.')
                if not usuario.esta_autorizado_para(vehiculo):
                    raise Denegado('ENTRADA_NO_AUTORIZADA',
                                   'Entrada denegada: el usuario no está autorizado para este vehículo.')
                if vehiculo.esta_dentro():
                    raise ErrorNegocio('El vehículo ya se encuentra dentro del parqueadero.')
                espacio = Espacio.buscar_libre(vehiculo.tipo, vehiculo.apartamento)
                if espacio is None:
                    raise ErrorNegocio('No hay espacios disponibles para este tipo de vehículo.')
                acceso = cls.objects.create(vehiculo=vehiculo, espacio=espacio, usuario_entrada=usuario)
                espacio.ocupar()
                Notificacion.enviar(vehiculo.propietarios_a_notificar(), 'ENTRADA_VEHICULO',
                                    f'El vehículo {vehiculo.placa} ingresó al parqueadero (espacio {espacio.identificador}).')
                return acceso
        except Denegado as e:
            IntentoNoAutorizado.registrar(e.tipo, placa, vehiculo, usuario, str(e))
            raise ErrorNegocio(str(e))

    @classmethod
    def registrar_salida(cls, usuario, placa):
        """RF-16, RF-18, RF-19, RF-21, RF-22."""
        placa = Vehiculo.normalizar_placa(placa)
        vehiculo = None
        try:
            with transaction.atomic():
                vehiculo = Vehiculo.objects.select_for_update().filter(placa=placa).first()
                if vehiculo is None:
                    raise ErrorNegocio('El vehículo no está registrado.')
                cls.validar_salida(usuario, vehiculo)
                acceso = (cls.objects.select_for_update().select_related('espacio')
                          .filter(vehiculo=vehiculo, estado='ACTIVO').first())
                if acceso is None:
                    raise ErrorNegocio('El vehículo no tiene una entrada activa.')
                acceso.finalizar(usuario)
                Notificacion.enviar(vehiculo.propietarios_a_notificar(), 'SALIDA_VEHICULO',
                                    f'El vehículo {vehiculo.placa} salió del parqueadero.')
                return acceso
        except Denegado as e:
            IntentoNoAutorizado.registrar(e.tipo, placa, vehiculo, usuario, str(e))
            raise ErrorNegocio(str(e))

    @staticmethod
    def validar_salida(usuario, vehiculo):
        """RF-18 y RF-19: solo un usuario autorizado puede retirar el vehículo."""
        if not usuario.esta_autorizado_para(vehiculo):
            raise Denegado('SALIDA_NO_AUTORIZADA',
                           f'Salida denegada: {usuario.nombre} no está autorizado para retirar el vehículo.')

    def finalizar(self, usuario):
        self.fecha_hora_salida = timezone.now()
        self.usuario_salida = usuario
        self.estado = 'FINALIZADO'
        self.save()
        self.espacio.liberar()


# =====================================================================================
class Visitante(models.Model):
    id_visitante = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    documento = models.CharField(max_length=20, unique=True)
    placa = models.CharField(max_length=10, blank=True)
    tipo_vehiculo = models.CharField(max_length=20, blank=True, choices=TIPOS_VEHICULO)

    class Meta:
        db_table = 'visitante'

    def __str__(self):
        return self.nombre

    @classmethod
    def registrar(cls, nombre, documento, placa, tipo_vehiculo):
        """RF-25: crea el visitante o actualiza sus datos si ya existe."""
        visitante, creado = cls.objects.get_or_create(
            documento=documento, defaults={'nombre': nombre, 'placa': placa, 'tipo_vehiculo': tipo_vehiculo})
        if not creado:
            visitante.nombre, visitante.placa, visitante.tipo_vehiculo = nombre, placa, tipo_vehiculo
            visitante.save()
        return visitante

    def tiene_visita_activa(self):
        return self.visitas.filter(estado='ACTIVO').exists()


class RegistroVisita(models.Model):
    id_visita = models.AutoField(primary_key=True)
    visitante = models.ForeignKey(Visitante, on_delete=models.PROTECT, db_column='id_visitante',
                                  related_name='visitas')
    apartamento = models.ForeignKey(Apartamento, on_delete=models.PROTECT, db_column='id_apartamento',
                                    related_name='visitas')
    usuario_autoriza = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column='id_usuario_autoriza',
                                         related_name='visitas_autorizadas')
    espacio = models.ForeignKey(Espacio, null=True, blank=True, on_delete=models.PROTECT,
                                db_column='id_espacio', related_name='visitas')
    fecha_hora_entrada = models.DateTimeField(default=timezone.now)
    fecha_hora_salida = models.DateTimeField(null=True, blank=True)
    tiempo_max_min = models.PositiveIntegerField(default=240)
    estado = models.CharField(max_length=15, choices=ESTADOS_ACCESO, default='ACTIVO')

    class Meta:
        db_table = 'registro_visita'
        constraints = [
            models.UniqueConstraint(fields=['visitante'], condition=Q(estado='ACTIVO'),
                                    name='uq_visita_visitante_activa'),
            models.UniqueConstraint(fields=['espacio'], condition=Q(estado='ACTIVO') & Q(espacio__isnull=False),
                                    name='uq_visita_espacio_activo'),
            models.CheckConstraint(
                condition=Q(fecha_hora_salida__isnull=True) | Q(fecha_hora_salida__gte=F('fecha_hora_entrada')),
                name='ck_visita_fechas'),
        ]

    @property
    def excedida(self):
        """RF-27: la visita superó su tiempo máximo de permanencia."""
        if self.estado != 'ACTIVO':
            return False
        return timezone.now() - self.fecha_hora_entrada > datetime.timedelta(minutes=self.tiempo_max_min)

    @classmethod
    def activas(cls):
        return cls.objects.filter(estado='ACTIVO').select_related('visitante', 'apartamento', 'espacio')

    @classmethod
    def registrar_entrada(cls, usuario, apartamento, nombre, documento, placa, tipo_vehiculo, tiempo_max_min):
        """RF-24 a RF-29."""
        placa = Vehiculo.normalizar_placa(placa)
        with transaction.atomic():
            if not usuario.puede_operar():
                raise ErrorNegocio('Su usuario no tiene un permiso vigente para registrar visitantes.')
            if apartamento.visitas_activas().count() >= settings.VISITANTES_MAX_POR_APTO:   # RF-28
                raise ErrorNegocio(
                    f'El apartamento ya tiene el máximo de {settings.VISITANTES_MAX_POR_APTO} visitante(s) simultáneos.')
            visitante = Visitante.registrar(nombre, documento, placa, tipo_vehiculo)
            if visitante.tiene_visita_activa():
                raise ErrorNegocio('Este visitante ya se encuentra dentro del parqueadero.')
            espacio = None
            if placa and tipo_vehiculo:
                espacio = Espacio.buscar_libre_visitante()
                if espacio is None:
                    raise ErrorNegocio('No hay espacios de visitantes disponibles.')   # RF-29
                espacio.ocupar()
            return cls.objects.create(visitante=visitante, apartamento=apartamento, usuario_autoriza=usuario,
                                      espacio=espacio, tiempo_max_min=tiempo_max_min)

    @classmethod
    def registrar_salida_por_id(cls, usuario, visita_id):
        """RF-26."""
        if not str(visita_id).isdigit():
            raise ErrorNegocio('La visita no existe o ya finalizó.')
        with transaction.atomic():
            visita = (cls.objects.select_for_update().select_related('espacio')
                      .filter(pk=visita_id, estado='ACTIVO').first())
            if visita is None:
                raise ErrorNegocio('La visita no existe o ya finalizó.')
            return visita.registrar_salida(usuario)

    def registrar_salida(self, usuario):
        if usuario.rol != 'ADMINISTRADOR' and self.apartamento_id != usuario.apartamento_id:
            raise ErrorNegocio('No puede registrar la salida de visitantes de otro apartamento.')
        self.fecha_hora_salida = timezone.now()
        self.estado = 'FINALIZADO'
        self.save()
        if self.espacio:
            self.espacio.liberar()
        return self


# =====================================================================================
class Permiso(models.Model):
    id_permiso = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario',
                                related_name='permisos')
    estado = models.BooleanField(default=True)
    fecha_inicio = models.DateField(default=datetime.date.today)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    motivo = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'permiso'
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_vencimiento__isnull=True) | Q(fecha_vencimiento__gte=F('fecha_inicio')),
                name='ck_permiso_fechas'),
        ]

    @property
    def vigente(self):
        hoy = timezone.localdate()
        return self.estado and self.fecha_inicio <= hoy and (
            self.fecha_vencimiento is None or self.fecha_vencimiento >= hoy)

    @classmethod
    def otorgar(cls, usuario, administrador, motivo='Permiso inicial', motivo_historial='Alta del residente'):
        """Crea un permiso indefinido y lo registra en el historial (RF-39)."""
        permiso = cls.objects.create(usuario=usuario, motivo=motivo)
        permiso.registrar_creacion(administrador, motivo_historial)
        return permiso

    def registrar_creacion(self, administrador, motivo):
        HistorialPermiso.registrar_cambio(self, administrador, 'CREADO', motivo)

    def activar(self, administrador, motivo='Cambio manual'):
        """RF-37 y RF-38: se aplica de inmediato."""
        self.estado = True
        self.save(update_fields=['estado'])
        HistorialPermiso.registrar_cambio(self, administrador, 'ACTIVADO', motivo)

    def desactivar(self, administrador, motivo='Cambio manual'):
        self.estado = False
        self.save(update_fields=['estado'])
        HistorialPermiso.registrar_cambio(self, administrador, 'DESACTIVADO', motivo)

    def alternar(self, administrador):
        if self.estado:
            self.desactivar(administrador)
        else:
            self.activar(administrador)


class HistorialPermiso(models.Model):
    id_historial = models.AutoField(primary_key=True)
    permiso = models.ForeignKey(Permiso, on_delete=models.CASCADE, db_column='id_permiso',
                                related_name='historial')
    usuario_modifica = models.ForeignKey(Usuario, on_delete=models.PROTECT, db_column='id_usuario_modifica',
                                         related_name='cambios_permiso')
    accion = models.CharField(max_length=30)
    motivo = models.CharField(max_length=200, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'historial_permiso'

    @classmethod
    def registrar_cambio(cls, permiso, usuario, accion, motivo=''):
        return cls.objects.create(permiso=permiso, usuario_modifica=usuario, accion=accion, motivo=motivo)


# =====================================================================================
class IntentoNoAutorizado(models.Model):
    TIPOS = [('ENTRADA_NO_AUTORIZADA', 'Entrada no autorizada'), ('SALIDA_NO_AUTORIZADA', 'Salida no autorizada')]

    id_intento = models.AutoField(primary_key=True)
    vehiculo = models.ForeignKey(Vehiculo, null=True, blank=True, on_delete=models.SET_NULL,
                                 db_column='id_vehiculo', related_name='intentos')
    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL,
                                db_column='id_usuario', related_name='intentos')
    tipo = models.CharField(max_length=30, choices=TIPOS)
    placa_detectada = models.CharField(max_length=10, blank=True)
    motivo = models.CharField(max_length=200, blank=True)
    fecha_hora = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'intento_no_autorizado'

    @classmethod
    def registrar(cls, tipo, placa, vehiculo, usuario, motivo):
        """RF-19 y RF-23: registra el intento y alerta a los administradores."""
        intento = cls.objects.create(tipo=tipo, placa_detectada=placa[:10], vehiculo=vehiculo,
                                     usuario=usuario, motivo=motivo[:200])
        intento.generar_alerta()
        return intento

    def generar_alerta(self):
        quien = self.usuario.nombre if self.usuario else 'desconocido'
        Notificacion.enviar(Usuario.objects.filter(rol='ADMINISTRADOR', estado=True), self.tipo,
                            f'{self.motivo} (placa {self.placa_detectada}, usuario {quien})')


class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario',
                                related_name='notificaciones')
    tipo = models.CharField(max_length=30)
    mensaje = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField(default=timezone.now)
    leida = models.BooleanField(default=False)

    class Meta:
        db_table = 'notificacion'

    @classmethod
    def enviar(cls, usuarios, tipo, mensaje):
        destinatarios = {u.pk: u for u in usuarios}.values()
        cls.objects.bulk_create([cls(usuario=u, tipo=tipo, mensaje=mensaje[:255]) for u in destinatarios])

    @classmethod
    def contar_no_leidas(cls, usuario):
        return cls.objects.filter(usuario=usuario, leida=False).count()

    @classmethod
    def marcar_todas_leidas(cls, usuario):
        cls.objects.filter(usuario=usuario, leida=False).update(leida=True)

    def marcar_leida(self):
        self.leida = True
        self.save(update_fields=['leida'])

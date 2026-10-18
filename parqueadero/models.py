# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Apartamento(models.Model):
    id_apartamento = models.AutoField(primary_key=True)
    id_parqueadero = models.ForeignKey('Parqueadero', models.DO_NOTHING, db_column='id_parqueadero')
    numero = models.CharField(max_length=10)
    propietario = models.CharField(max_length=100)
    max_vehiculos = models.IntegerField()
    estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'apartamento'
        unique_together = (('id_parqueadero', 'numero'),)


class Espacio(models.Model):
    id_espacio = models.AutoField(primary_key=True)
    id_parqueadero = models.ForeignKey('Parqueadero', models.DO_NOTHING, db_column='id_parqueadero')
    id_apartamento = models.ForeignKey(Apartamento, models.DO_NOTHING, db_column='id_apartamento', blank=True, null=True)
    identificador = models.CharField(max_length=10)
    zona = models.CharField(max_length=30, blank=True, null=True)
    tipo = models.CharField(max_length=20)
    estado = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'espacio'
        unique_together = (('id_parqueadero', 'identificador'),)


class HistorialPermiso(models.Model):
    id_historial = models.AutoField(primary_key=True)
    id_permiso = models.ForeignKey('Permiso', models.DB_CASCADE, db_column='id_permiso')
    id_usuario_modifica = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario_modifica')
    accion = models.CharField(max_length=30)
    motivo = models.CharField(max_length=200, blank=True, null=True)
    fecha_hora = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'historial_permiso'


class IntentoNoAutorizado(models.Model):
    id_intento = models.AutoField(primary_key=True)
    id_vehiculo = models.ForeignKey('Vehiculo', models.DO_NOTHING, db_column='id_vehiculo', blank=True, null=True)
    id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    tipo = models.CharField(max_length=30)
    placa_detectada = models.CharField(max_length=10, blank=True, null=True)
    motivo = models.CharField(max_length=200, blank=True, null=True)
    fecha_hora = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'intento_no_autorizado'


class Notificacion(models.Model):
    id_notificacion = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey('Usuario', models.DB_CASCADE, db_column='id_usuario')
    tipo = models.CharField(max_length=30)
    mensaje = models.CharField(max_length=255)
    fecha_hora = models.DateTimeField()
    leida = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'notificacion'


class Parqueadero(models.Model):
    id_parqueadero = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    capacidad = models.IntegerField()
    estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'parqueadero'


class Permiso(models.Model):
    id_permiso = models.AutoField(primary_key=True)
    id_usuario = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario')
    estado = models.BooleanField()
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField(blank=True, null=True)
    motivo = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'permiso'


class RegistroAcceso(models.Model):
    id_registro = models.AutoField(primary_key=True)
    id_vehiculo = models.OneToOneField('Vehiculo', models.DO_NOTHING, db_column='id_vehiculo')
    id_espacio = models.OneToOneField(Espacio, models.DO_NOTHING, db_column='id_espacio')
    id_usuario_entrada = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario_entrada')
    id_usuario_salida = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario_salida', related_name='registroacceso_id_usuario_salida_set', blank=True, null=True)
    fecha_hora_entrada = models.DateTimeField()
    fecha_hora_salida = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=15)

    class Meta:
        managed = False
        db_table = 'registro_acceso'


class RegistroVisita(models.Model):
    id_visita = models.AutoField(primary_key=True)
    id_visitante = models.OneToOneField('Visitante', models.DO_NOTHING, db_column='id_visitante')
    id_apartamento = models.ForeignKey(Apartamento, models.DO_NOTHING, db_column='id_apartamento')
    id_usuario_autoriza = models.ForeignKey('Usuario', models.DO_NOTHING, db_column='id_usuario_autoriza')
    id_espacio = models.OneToOneField(Espacio, models.DO_NOTHING, db_column='id_espacio', blank=True, null=True)
    fecha_hora_entrada = models.DateTimeField()
    fecha_hora_salida = models.DateTimeField(blank=True, null=True)
    tiempo_max_min = models.IntegerField()
    estado = models.CharField(max_length=15)

    class Meta:
        managed = False
        db_table = 'registro_visita'


class Usuario(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    id_apartamento = models.ForeignKey(Apartamento, models.DO_NOTHING, db_column='id_apartamento', blank=True, null=True)
    nombre = models.CharField(max_length=100)
    cedula = models.CharField(unique=True, max_length=20)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo = models.CharField(unique=True, max_length=100)
    usuario = models.CharField(unique=True, max_length=50)
    clave_hash = models.CharField(max_length=255)
    rol = models.CharField(max_length=20)
    estado = models.BooleanField()
    intentos_fallidos = models.IntegerField()
    bloqueado_hasta = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuario'


class UsuarioVehiculo(models.Model):
    pk = models.CompositePrimaryKey('id_usuario', 'id_vehiculo')
    id_usuario = models.ForeignKey(Usuario, models.DB_CASCADE, db_column='id_usuario')
    id_vehiculo = models.ForeignKey('Vehiculo', models.DB_CASCADE, db_column='id_vehiculo')

    class Meta:
        managed = False
        db_table = 'usuario_vehiculo'


class Vehiculo(models.Model):
    id_vehiculo = models.AutoField(primary_key=True)
    id_apartamento = models.ForeignKey(Apartamento, models.DO_NOTHING, db_column='id_apartamento')
    placa = models.CharField(unique=True, max_length=10)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    tipo = models.CharField(max_length=20)
    estado = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'vehiculo'


class Visitante(models.Model):
    id_visitante = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    documento = models.CharField(unique=True, max_length=20)
    placa = models.CharField(max_length=10, blank=True, null=True)
    tipo_vehiculo = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'visitante'

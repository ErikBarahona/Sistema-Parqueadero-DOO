"""Carga datos de demostración: python manage.py cargar_demo"""
import os

from django.core.management.base import BaseCommand

from parqueadero.models import Apartamento, Espacio, Parqueadero, Permiso, Usuario, Vehiculo

CLAVE_ADMIN = os.environ.get('DEMO_CLAVE_ADMIN', 'Admin2026*')
CLAVE_RESIDENTE = os.environ.get('DEMO_CLAVE_RESIDENTE', 'Residente2026*')


class Command(BaseCommand):
    help = 'Carga un parqueadero, apartamentos, usuarios, vehículos y espacios de demostración.'

    def add_arguments(self, parser):
        parser.add_argument('--solo-si-env', action='store_true',
                            help='Solo carga los datos si la variable de entorno CARGAR_DEMO es "true".')

    def handle(self, *args, **options):
        if options['solo_si_env'] and os.environ.get('CARGAR_DEMO', '').lower() != 'true':
            self.stdout.write('CARGAR_DEMO no está activo: no se cargan datos de demostración.')
            return
        parq, _ = Parqueadero.objects.get_or_create(
            nombre='Edificio Los Almendros',
            defaults={'direccion': 'Calle 45 # 12-30, Bogotá', 'telefono': '6011234567', 'capacidad': 8})

        aptos = {}
        for numero, prop, maximo in [('101', 'Carlos Pérez', 2), ('102', 'María Gómez', 1), ('201', 'Andrés Rojas', 1)]:
            aptos[numero], _ = Apartamento.objects.get_or_create(
                parqueadero=parq, numero=numero, defaults={'propietario': prop, 'max_vehiculos': maximo})

        def usuario(nombre, cedula, correo, user, clave, rol, apto=None):
            u = Usuario.objects.filter(usuario=user).first()
            if u:
                return u
            u = Usuario(nombre=nombre, cedula=cedula, correo=correo, usuario=user, rol=rol, apartamento=apto)
            u.set_password(clave)
            u.save()
            if rol == 'RESIDENTE':
                Permiso.otorgar(u, admin, motivo_historial='Carga demo')
            return u

        admin = usuario('Administrador SAGP', '1000000001', 'admin@sagp.test', 'admin', CLAVE_ADMIN, 'ADMINISTRADOR')
        usuario('Auditor SAGP', '1000000005', 'auditor@sagp.test', 'auditor', CLAVE_ADMIN, 'AUDITOR')
        carlos = usuario('Carlos Pérez', '1000000002', 'carlos@sagp.test', 'cperez', CLAVE_RESIDENTE, 'RESIDENTE', aptos['101'])
        maria = usuario('María Gómez', '1000000003', 'maria@sagp.test', 'mgomez', CLAVE_RESIDENTE, 'RESIDENTE', aptos['102'])
        andres = usuario('Andrés Rojas', '1000000004', 'andres@sagp.test', 'arojas', CLAVE_RESIDENTE, 'RESIDENTE', aptos['201'])

        for ident, zona, tipo, apto in [
                ('C-01', 'Sótano 1', 'CARRO', '101'), ('C-02', 'Sótano 1', 'CARRO', '102'),
                ('C-03', 'Sótano 1', 'CARRO', '201'), ('C-04', 'Sótano 1', 'CARRO', None),
                ('M-01', 'Sótano 1', 'MOTO', '101'), ('M-02', 'Sótano 1', 'MOTO', None),
                ('V-01', 'Visitantes', 'VISITANTE', None), ('V-02', 'Visitantes', 'VISITANTE', None)]:
            Espacio.objects.get_or_create(parqueadero=parq, identificador=ident,
                                          defaults={'zona': zona, 'tipo': tipo, 'apartamento': aptos.get(apto)})

        for apto, placa, marca, modelo, color, tipo, dueno in [
                ('101', 'ABC123', 'Mazda', '2020', 'Rojo', 'CARRO', carlos),
                ('101', 'XYZ12D', 'Yamaha', '2022', 'Negro', 'MOTO', carlos),
                ('102', 'DEF456', 'Renault', '2019', 'Gris', 'CARRO', maria),
                ('201', 'GHI789', 'Chevrolet', '2021', 'Blanco', 'CARRO', andres)]:
            v, _ = Vehiculo.objects.get_or_create(placa=placa, defaults={
                'apartamento': aptos[apto], 'marca': marca, 'modelo': modelo, 'color': color, 'tipo': tipo})
            v.autorizar_usuarios([dueno])

        self.stdout.write(self.style.SUCCESS('Datos de demostración cargados.'))
        self.stdout.write(f'  Administrador: admin / {CLAVE_ADMIN}')
        self.stdout.write(f'  Auditor:       auditor / {CLAVE_ADMIN}')
        self.stdout.write(f'  Residentes:    cperez, mgomez, arojas / {CLAVE_RESIDENTE}')

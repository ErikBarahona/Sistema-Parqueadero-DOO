"""Vistas del SAGP orientadas a objetos.

Jerarquía de clases:
    RolRequeridoMixin ──► ListaTablaView ──► (listados) ──► ReporteView ──► (reportes)
                      └─► FormularioView ──► (formularios de alta y edición)
                      └─► View de Django ──► Portería, Visitas, Inicio, etc.
"""
import csv
from collections import namedtuple

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .excepciones import ErrorNegocio
from .forms import (ApartamentoForm, EspacioForm, FiltroForm, PermisoForm, UsuarioForm, VehiculoForm,
                    VisitaForm)
from .models import (Apartamento, Espacio, HistorialPermiso, IntentoNoAutorizado, Notificacion, Permiso,
                     RegistroAcceso, RegistroVisita, Usuario, Vehiculo)

Fila = namedtuple('Fila', 'celdas acciones')
TODOS = ('ADMINISTRADOR', 'RESIDENTE', 'AUDITOR')
ADMIN = ('ADMINISTRADOR',)
ADMIN_Y_RESIDENTE = ('ADMINISTRADOR', 'RESIDENTE')
ADMIN_Y_AUDITOR = ('ADMINISTRADOR', 'AUDITOR')


# ======================================================================= utilidades
def fmt(fecha):
    return timezone.localtime(fecha).strftime('%d/%m/%Y %H:%M') if fecha else ''


def fmt_fecha(fecha):
    return fecha.strftime('%d/%m/%Y') if fecha else ''


def si_no(valor):
    return 'Sí' if valor else 'No'


def exportar_csv(nombre, columnas, filas):
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{nombre}.csv"'
    resp.write('\ufeff')   # para que Excel reconozca los acentos
    escritor = csv.writer(resp)
    escritor.writerow(columnas)
    for f in filas:
        escritor.writerow(f.celdas)
    return resp


# ======================================================================= clases base
class RolRequeridoMixin(LoginRequiredMixin):
    """RF-06: restringe la vista a los roles indicados en `roles_permitidos`."""
    roles_permitidos = TODOS

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.rol not in self.roles_permitidos:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class ListaTablaView(RolRequeridoMixin, View):
    """Listado genérico en tabla. Las subclases definen título, columnas y `obtener_filas()`."""
    titulo = ''
    columnas = []

    def obtener_filas(self):
        raise NotImplementedError

    def contexto_extra(self):
        return {}

    def get(self, request, *args, **kwargs):
        return self.responder(self.obtener_filas())

    def responder(self, filas, **extra):
        consulta = self.request.GET.copy()
        consulta.pop('export', None)
        ctx = {'titulo': self.titulo, 'columnas': self.columnas, 'filas': filas,
               'con_acciones': any(f.acciones for f in filas), 'query': consulta.urlencode()}
        ctx.update(self.contexto_extra())
        ctx.update(extra)
        return render(self.request, 'parqueadero/lista.html', ctx)


class ReporteView(ListaTablaView):
    """Reporte filtrable por fechas y texto, con exportación a CSV (RF-41, RF-46)."""
    nombre_csv = 'reporte'

    def filtros(self):
        f = FiltroForm(self.request.GET or None)
        return f, (f.cleaned_data if f.is_valid() else {})

    @staticmethod
    def filtrar_rango(qs, campo, datos):
        if datos.get('desde'):
            qs = qs.filter(**{f'{campo}__date__gte': datos['desde']})
        if datos.get('hasta'):
            qs = qs.filter(**{f'{campo}__date__lte': datos['hasta']})
        return qs

    def construir_filas(self, datos):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        f, datos = self.filtros()
        filas = self.construir_filas(datos)
        if request.GET.get('export') == 'csv':
            return exportar_csv(self.nombre_csv, self.columnas, filas)
        return self.responder(filas, filtro=f, exportable=True)


class FormularioView(RolRequeridoMixin, View):
    """Alta o edición con un formulario. Las subclases definen `form_class`, `titulo` y `volver`."""
    form_class = None
    titulo = ''
    volver = 'inicio'
    mensaje_exito = 'Guardado correctamente.'

    def get_instancia(self):
        return None

    def get_form_kwargs(self):
        return {}

    def construir_form(self, data=None):
        return self.form_class(data, instance=self.get_instancia(), **self.get_form_kwargs())

    def guardar(self, form):
        return form.save()

    def mostrar(self, form):
        return render(self.request, 'parqueadero/form.html',
                      {'form': form, 'titulo': self.titulo, 'volver': reverse(self.volver)})

    def get(self, request, *args, **kwargs):
        return self.mostrar(self.construir_form())

    def post(self, request, *args, **kwargs):
        form = self.construir_form(request.POST)
        if form.is_valid():
            self.guardar(form)
            messages.success(request, self.mensaje_exito)
            return redirect(self.volver)
        return self.mostrar(form)


# ======================================================================= acceso (RF-01, RF-04, RF-05)
class LoginView(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('inicio')
        return render(request, 'parqueadero/login.html')

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('inicio')
        try:
            user = Usuario.autenticar(request, request.POST.get('usuario', '').strip(), request.POST.get('clave', ''))
        except ErrorNegocio as e:
            messages.error(request, str(e))
            return render(request, 'parqueadero/login.html')
        login(request, user)
        destino = request.GET.get('next', '')
        if destino and url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
            return redirect(destino)
        return redirect('inicio')


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('login')


# ======================================================================= inicio (RF-33)
class InicioView(LoginRequiredMixin, View):
    def get(self, request):
        u = request.user
        ctx = {'ocupacion': Espacio.ocupacion_por_tipo()}
        if u.rol in ADMIN_Y_AUDITOR:
            activas = list(RegistroVisita.activas())
            ctx.update({
                'vehiculos_dentro': RegistroAcceso.activos().count(),
                'visitas_activas': len(activas),
                'visitas_excedidas': [v for v in activas if v.excedida],
                'intentos': IntentoNoAutorizado.objects.select_related('usuario').order_by('-fecha_hora')[:5],
            })
        else:
            dentro = set(RegistroAcceso.activos().filter(vehiculo__apartamento_id=u.apartamento_id)
                         .values_list('vehiculo_id', flat=True))
            ctx['mis_vehiculos'] = [(v, v.pk in dentro) for v in Vehiculo.objects.filter(apartamento_id=u.apartamento_id)]
        return render(request, 'parqueadero/inicio.html', ctx)


# ======================================================================= usuarios (RF-03)
class UsuarioListView(ListaTablaView):
    roles_permitidos = ADMIN
    titulo = 'Usuarios'
    columnas = ['Nombre', 'Usuario', 'Rol', 'Apto', 'Activo', 'Cuenta']

    def contexto_extra(self):
        return {'nuevo_url': reverse('usuario_nuevo'), 'nuevo_texto': 'Nuevo usuario'}

    def obtener_filas(self):
        return [Fila([u.nombre, u.usuario, u.get_rol_display(), u.apartamento.numero if u.apartamento else '—',
                      si_no(u.estado), 'Bloqueada' if u.esta_bloqueado() else ''],
                     [('Editar', reverse('usuario_editar', args=[u.pk]), 'get', 'btn-outline-primary')])
                for u in Usuario.objects.select_related('apartamento').order_by('rol', 'nombre')]


class UsuarioCrearView(FormularioView):
    roles_permitidos = ADMIN
    form_class = UsuarioForm
    titulo = 'Nuevo usuario'
    volver = 'usuarios'
    mensaje_exito = 'Usuario creado correctamente.'

    def guardar(self, form):
        u = form.save()
        if u.rol == 'RESIDENTE':      # permiso inicial indefinido
            Permiso.otorgar(u, self.request.user)
        return u


class UsuarioEditarView(FormularioView):
    roles_permitidos = ADMIN
    form_class = UsuarioForm
    titulo = 'Editar usuario'
    volver = 'usuarios'

    def get_instancia(self):
        return get_object_or_404(Usuario, pk=self.kwargs['pk'])


# ======================================================================= apartamentos (RF-07 a RF-10)
class ApartamentoListView(ListaTablaView):
    roles_permitidos = ADMIN
    titulo = 'Apartamentos'
    columnas = ['Número', 'Propietario', 'Máx. vehículos', 'Residentes', 'Activo']

    def contexto_extra(self):
        return {'nuevo_url': reverse('apartamento_nuevo'), 'nuevo_texto': 'Nuevo apartamento'}

    def obtener_filas(self):
        return [Fila([a.numero, a.propietario, a.max_vehiculos, a.usuarios.count(), si_no(a.estado)],
                     [('Editar', reverse('apartamento_editar', args=[a.pk]), 'get', 'btn-outline-primary')])
                for a in Apartamento.objects.order_by('numero')]


class ApartamentoCrearView(FormularioView):
    roles_permitidos = ADMIN
    form_class = ApartamentoForm
    titulo = 'Nuevo apartamento'
    volver = 'apartamentos'


class ApartamentoEditarView(FormularioView):
    roles_permitidos = ADMIN
    form_class = ApartamentoForm
    titulo = 'Editar apartamento'
    volver = 'apartamentos'

    def get_instancia(self):
        return get_object_or_404(Apartamento, pk=self.kwargs['pk'])


# ======================================================================= espacios (RF-30 a RF-36)
class EspacioListView(ListaTablaView):
    roles_permitidos = ADMIN_Y_AUDITOR
    titulo = 'Espacios del parqueadero'
    columnas = ['Identificador', 'Zona', 'Tipo', 'Estado', 'Asignación']

    def contexto_extra(self):
        if self.request.user.rol == 'ADMINISTRADOR':
            return {'nuevo_url': reverse('espacio_nuevo'), 'nuevo_texto': 'Nuevo espacio'}
        return {}

    def obtener_filas(self):
        filas = []
        for e in Espacio.objects.select_related('apartamento').order_by('identificador'):
            acciones = []
            if self.request.user.rol == 'ADMINISTRADOR':
                acciones = [('Editar', reverse('espacio_editar', args=[e.pk]), 'get', 'btn-outline-primary')]
            filas.append(Fila([e.identificador, e.zona, e.get_tipo_display(), e.get_estado_display(),
                               f'Apto {e.apartamento.numero}' if e.apartamento else 'Común'], acciones))
        return filas


class EspacioCrearView(FormularioView):
    roles_permitidos = ADMIN
    form_class = EspacioForm
    titulo = 'Nuevo espacio'
    volver = 'espacios'


class EspacioEditarView(FormularioView):
    roles_permitidos = ADMIN
    form_class = EspacioForm
    titulo = 'Editar espacio'
    volver = 'espacios'

    def get_instancia(self):
        return get_object_or_404(Espacio, pk=self.kwargs['pk'])


# ======================================================================= vehículos (RF-11 a RF-14)
class VehiculoListView(ListaTablaView):
    titulo = 'Vehículos'
    columnas = ['Placa', 'Marca', 'Modelo', 'Color', 'Tipo', 'Apto', 'Activo']

    def contexto_extra(self):
        if self.request.user.rol != 'AUDITOR':
            return {'nuevo_url': reverse('vehiculo_nuevo'), 'nuevo_texto': 'Registrar vehículo'}
        return {}

    def obtener_filas(self):
        filas = []
        for v in Vehiculo.visibles_para(self.request.user).order_by('placa'):
            acciones = []
            if self.request.user.rol != 'AUDITOR':
                acciones = [('Editar', reverse('vehiculo_editar', args=[v.pk]), 'get', 'btn-outline-primary')]
            filas.append(Fila([v.placa, v.marca, v.modelo, v.color, v.get_tipo_display(), v.apartamento.numero,
                               si_no(v.estado)], acciones))
        return filas


class VehiculoCrearView(FormularioView):
    roles_permitidos = ADMIN_Y_RESIDENTE
    form_class = VehiculoForm
    titulo = 'Registrar vehículo'
    volver = 'vehiculos'

    def get_form_kwargs(self):
        return {'usuario': self.request.user}


class VehiculoEditarView(VehiculoCrearView):
    titulo = 'Editar vehículo'

    def get_instancia(self):
        return get_object_or_404(Vehiculo.visibles_para(self.request.user), pk=self.kwargs['pk'])


# ======================================================================= portería (RF-15 a RF-23)
class PorteriaView(RolRequeridoMixin, View):
    roles_permitidos = ADMIN_Y_RESIDENTE

    def get(self, request):
        dentro = RegistroAcceso.activos().select_related('vehiculo', 'vehiculo__apartamento', 'espacio')
        mios = []
        if request.user.rol == 'RESIDENTE':
            dentro = dentro.filter(vehiculo__apartamento_id=request.user.apartamento_id)
            ids = set(dentro.values_list('vehiculo_id', flat=True))
            mios = [(v, v.pk in ids)
                    for v in Vehiculo.objects.filter(apartamento_id=request.user.apartamento_id, estado=True)]
        return render(request, 'parqueadero/porteria.html',
                      {'dentro': dentro.order_by('-fecha_hora_entrada'), 'mios': mios})

    def post(self, request):
        accion = request.POST.get('accion')
        placa = request.POST.get('placa', '')
        try:
            if accion == 'entrada':
                acceso = RegistroAcceso.registrar_entrada(request.user, placa)
                messages.success(request, f'Entrada registrada: {acceso.vehiculo.placa} en el espacio {acceso.espacio.identificador}.')
            elif accion == 'salida':
                acceso = RegistroAcceso.registrar_salida(request.user, placa)
                messages.success(request, f'Salida registrada: {acceso.vehiculo.placa}.')
        except ErrorNegocio as e:
            messages.error(request, str(e))
        return redirect('porteria')


# ======================================================================= visitantes (RF-24 a RF-29)
class VisitasView(RolRequeridoMixin, View):
    roles_permitidos = ADMIN_Y_RESIDENTE

    def mostrar(self, form):
        activas = RegistroVisita.activas()
        if self.request.user.rol == 'RESIDENTE':
            activas = activas.filter(apartamento_id=self.request.user.apartamento_id)
        return render(self.request, 'parqueadero/visitas.html',
                      {'form': form, 'activas': activas.order_by('fecha_hora_entrada')})

    def get(self, request):
        return self.mostrar(VisitaForm(usuario=request.user))

    def post(self, request):
        user = request.user
        if request.POST.get('accion') == 'salida':
            try:
                v = RegistroVisita.registrar_salida_por_id(user, request.POST.get('visita_id'))
                messages.success(request, f'Salida registrada: {v.visitante.nombre}.')
            except ErrorNegocio as e:
                messages.error(request, str(e))
            return redirect('visitas')
        form = VisitaForm(request.POST, usuario=user)
        if form.is_valid():
            d = form.cleaned_data
            apto = d.get('apartamento') or user.apartamento
            try:
                RegistroVisita.registrar_entrada(user, apto, d['nombre'], d['documento'], d['placa'],
                                                 d['tipo_vehiculo'], d['tiempo_max_min'])
                messages.success(request, 'Entrada del visitante registrada.')
                return redirect('visitas')
            except ErrorNegocio as e:
                messages.error(request, str(e))
        return self.mostrar(form)


# ======================================================================= permisos (RF-37 a RF-40)
class PermisoListView(ListaTablaView):
    roles_permitidos = ADMIN
    titulo = 'Permisos de usuarios'
    columnas = ['Usuario', 'Inicio', 'Vencimiento', 'Estado', 'Vigencia', 'Motivo']

    def contexto_extra(self):
        return {'nuevo_url': reverse('permiso_nuevo'), 'nuevo_texto': 'Nuevo permiso'}

    def obtener_filas(self):
        filas = []
        for p in Permiso.objects.select_related('usuario').order_by('usuario__nombre', '-fecha_inicio'):
            etiqueta = 'Desactivar' if p.estado else 'Activar'
            clase = 'btn-outline-danger' if p.estado else 'btn-outline-success'
            filas.append(Fila([p.usuario.nombre, fmt_fecha(p.fecha_inicio),
                               fmt_fecha(p.fecha_vencimiento) or 'Sin vencimiento',
                               'Activo' if p.estado else 'Inactivo', 'Vigente' if p.vigente else 'No vigente',
                               p.motivo],
                              [(etiqueta, reverse('permiso_toggle', args=[p.pk]), 'post', clase)]))
        return filas


class PermisoCrearView(FormularioView):
    roles_permitidos = ADMIN
    form_class = PermisoForm
    titulo = 'Nuevo permiso'
    volver = 'permisos'
    mensaje_exito = 'Permiso creado. Se aplica de inmediato.'

    def guardar(self, form):
        p = form.save()
        p.registrar_creacion(self.request.user, p.motivo or 'Permiso creado')
        return p


class PermisoCambiarView(RolRequeridoMixin, View):
    roles_permitidos = ADMIN
    http_method_names = ['post']

    def post(self, request, pk):
        get_object_or_404(Permiso, pk=pk).alternar(request.user)
        messages.success(request, 'Permiso actualizado. El cambio se aplica de inmediato.')
        return redirect('permisos')


# ======================================================================= notificaciones (RF-48, RF-49)
class NotificacionListView(ListaTablaView):
    titulo = 'Notificaciones'
    columnas = ['Fecha', 'Tipo', 'Mensaje', 'Estado']

    def obtener_filas(self):
        qs = list(Notificacion.objects.filter(usuario=self.request.user).order_by('-fecha_hora')[:100])
        filas = [Fila([fmt(n.fecha_hora), n.tipo, n.mensaje, 'Leída' if n.leida else 'Nueva'], []) for n in qs]
        Notificacion.marcar_todas_leidas(self.request.user)
        return filas


# ======================================================================= reportes (RF-41 a RF-47)
class ReporteAccesosView(ReporteView):
    titulo = 'Reporte de entradas y salidas (historial de vehículos)'
    nombre_csv = 'reporte_accesos'
    columnas = ['Placa', 'Apto', 'Espacio', 'Entrada', 'Salida', 'Registró entrada', 'Registró salida', 'Estado']

    def construir_filas(self, datos):
        qs = RegistroAcceso.objects.select_related('vehiculo', 'vehiculo__apartamento', 'espacio',
                                                   'usuario_entrada', 'usuario_salida').order_by('-fecha_hora_entrada')
        if self.request.user.rol == 'RESIDENTE':
            qs = qs.filter(vehiculo__apartamento_id=self.request.user.apartamento_id)
        qs = self.filtrar_rango(qs, 'fecha_hora_entrada', datos)
        if datos.get('texto'):
            qs = qs.filter(vehiculo__placa__icontains=datos['texto'].strip().upper())
        return [Fila([a.vehiculo.placa, a.vehiculo.apartamento.numero, a.espacio.identificador,
                      fmt(a.fecha_hora_entrada), fmt(a.fecha_hora_salida), a.usuario_entrada.nombre,
                      a.usuario_salida.nombre if a.usuario_salida else '', a.get_estado_display()], [])
                for a in qs[:1000]]


class ReporteVisitasView(ReporteView):
    titulo = 'Reporte de visitantes'
    nombre_csv = 'reporte_visitas'
    columnas = ['Visitante', 'Documento', 'Placa', 'Apto', 'Autorizó', 'Entrada', 'Salida', 'Estado']

    def construir_filas(self, datos):
        qs = RegistroVisita.objects.select_related('visitante', 'apartamento', 'usuario_autoriza').order_by('-fecha_hora_entrada')
        if self.request.user.rol == 'RESIDENTE':
            qs = qs.filter(apartamento_id=self.request.user.apartamento_id)
        qs = self.filtrar_rango(qs, 'fecha_hora_entrada', datos)
        if datos.get('texto'):
            t = datos['texto'].strip()
            qs = qs.filter(Q(visitante__documento__icontains=t) | Q(visitante__placa__icontains=t.upper()))
        return [Fila([v.visitante.nombre, v.visitante.documento, v.visitante.placa, v.apartamento.numero,
                      v.usuario_autoriza.nombre, fmt(v.fecha_hora_entrada), fmt(v.fecha_hora_salida),
                      'Tiempo excedido' if v.excedida else v.get_estado_display()], [])
                for v in qs[:1000]]


class ReporteIntentosView(ReporteView):
    roles_permitidos = ADMIN_Y_AUDITOR
    titulo = 'Intentos de acceso no autorizados'
    nombre_csv = 'reporte_intentos'
    columnas = ['Fecha', 'Tipo', 'Placa', 'Usuario', 'Motivo']

    def construir_filas(self, datos):
        qs = IntentoNoAutorizado.objects.select_related('usuario').order_by('-fecha_hora')
        qs = self.filtrar_rango(qs, 'fecha_hora', datos)
        if datos.get('texto'):
            qs = qs.filter(placa_detectada__icontains=datos['texto'].strip().upper())
        return [Fila([fmt(i.fecha_hora), i.get_tipo_display(), i.placa_detectada,
                      i.usuario.nombre if i.usuario else '', i.motivo], []) for i in qs[:1000]]


class ReportePermisosView(ReporteView):
    roles_permitidos = ADMIN_Y_AUDITOR
    titulo = 'Cambios de permisos (auditoría)'
    nombre_csv = 'reporte_permisos'
    columnas = ['Fecha', 'Usuario', 'Acción', 'Motivo', 'Modificado por']

    def construir_filas(self, datos):
        qs = HistorialPermiso.objects.select_related('permiso__usuario', 'usuario_modifica').order_by('-fecha_hora')
        qs = self.filtrar_rango(qs, 'fecha_hora', datos)
        return [Fila([fmt(h.fecha_hora), h.permiso.usuario.nombre, h.accion, h.motivo, h.usuario_modifica.nombre], [])
                for h in qs[:1000]]

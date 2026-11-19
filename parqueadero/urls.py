from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

urlpatterns = [
    path('', views.InicioView.as_view(), name='inicio'),
    path('ingresar/', views.LoginView.as_view(), name='login'),
    path('salir/', views.LogoutView.as_view(), name='logout'),
    path('clave/', auth_views.PasswordChangeView.as_view(
        template_name='parqueadero/form.html', success_url=reverse_lazy('inicio'),
        extra_context={'titulo': 'Cambiar contraseña', 'volver': reverse_lazy('inicio')}), name='cambiar_clave'),

    path('usuarios/', views.UsuarioListView.as_view(), name='usuarios'),
    path('usuarios/nuevo/', views.UsuarioCrearView.as_view(), name='usuario_nuevo'),
    path('usuarios/<int:pk>/', views.UsuarioEditarView.as_view(), name='usuario_editar'),

    path('apartamentos/', views.ApartamentoListView.as_view(), name='apartamentos'),
    path('apartamentos/nuevo/', views.ApartamentoCrearView.as_view(), name='apartamento_nuevo'),
    path('apartamentos/<int:pk>/', views.ApartamentoEditarView.as_view(), name='apartamento_editar'),

    path('espacios/', views.EspacioListView.as_view(), name='espacios'),
    path('espacios/nuevo/', views.EspacioCrearView.as_view(), name='espacio_nuevo'),
    path('espacios/<int:pk>/', views.EspacioEditarView.as_view(), name='espacio_editar'),

    path('vehiculos/', views.VehiculoListView.as_view(), name='vehiculos'),
    path('vehiculos/nuevo/', views.VehiculoCrearView.as_view(), name='vehiculo_nuevo'),
    path('vehiculos/<int:pk>/', views.VehiculoEditarView.as_view(), name='vehiculo_editar'),

    path('porteria/', views.PorteriaView.as_view(), name='porteria'),
    path('visitas/', views.VisitasView.as_view(), name='visitas'),

    path('permisos/', views.PermisoListView.as_view(), name='permisos'),
    path('permisos/nuevo/', views.PermisoCrearView.as_view(), name='permiso_nuevo'),
    path('permisos/<int:pk>/cambiar/', views.PermisoCambiarView.as_view(), name='permiso_toggle'),

    path('notificaciones/', views.NotificacionListView.as_view(), name='notificaciones'),

    path('reportes/accesos/', views.ReporteAccesosView.as_view(), name='reporte_accesos'),
    path('reportes/visitas/', views.ReporteVisitasView.as_view(), name='reporte_visitas'),
    path('reportes/intentos/', views.ReporteIntentosView.as_view(), name='reporte_intentos'),
    path('reportes/permisos/', views.ReportePermisosView.as_view(), name='reporte_permisos'),
]

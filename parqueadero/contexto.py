from .models import Notificacion


def global_ctx(request):
    """Disponible en todas las plantillas: número de notificaciones sin leer."""
    if request.user.is_authenticated:
        return {'n_notif': Notificacion.contar_no_leidas(request.user)}
    return {}

from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect


def solo_gestor_usuarios(view_func):
    """
    Solo superusuario o usuario 'andres' pueden acceder.
    Permite a andres gestionar usuarios/contraseñas sin ser superusuario.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superuser or request.user.username == 'andres'):
            messages.error(request, "No tienes permiso para gestionar usuarios.")
            return redirect('intervencion_lista')
        return view_func(request, *args, **kwargs)
    return wrapper

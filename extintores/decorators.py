from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

from .permissions import PERM_GESTIONAR_USUARIOS, usuario_tiene_permiso


def solo_gestor_usuarios(view_func):
    """
    Solo superusuario o usuario 'andres' pueden acceder.
    Permite a andres gestionar usuarios/contraseñas sin ser superusuario.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not usuario_tiene_permiso(request.user, PERM_GESTIONAR_USUARIOS):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

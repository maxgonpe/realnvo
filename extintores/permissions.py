"""Roles y permisos funcionales de la app extintores.

Los grupos son roles combinables. Los permisos individuales permiten ajustar
excepciones sin duplicar la definicion de cada rol.
"""

from functools import wraps

from django.shortcuts import redirect, render

ROLE_ADMINISTRADOR = 'Administrador'
ROLE_SUPERVISOR = 'Supervisor'
ROLE_TECNICO = 'Tecnico'
ROLE_INVENTARIO = 'Inventario'
ROLE_SOLO_LECTURA = 'Solo lectura'

PERM_GESTIONAR_USUARIOS = 'extintores.manage_users'
PERM_GESTIONAR_PERMISOS = 'extintores.manage_permissions'
PERM_FIRMAR_DOCUMENTOS = 'extintores.sign_documents'
PERM_VER_FINANZAS = 'extintores.view_financial_data'
PERM_VER_OPERACIONES = 'extintores.view_operations'
PERM_GESTIONAR_OPERACIONES = 'extintores.manage_operations'
PERM_GESTIONAR_CATALOGO = 'extintores.manage_catalog'
PERM_GESTIONAR_INVENTARIO = 'extintores.manage_inventory'
PERM_VER_REPORTES = 'extintores.view_reports'

ROLE_DEFAULT_PERMISSIONS = {
    ROLE_ADMINISTRADOR: {
        PERM_GESTIONAR_USUARIOS, PERM_GESTIONAR_PERMISOS,
        PERM_FIRMAR_DOCUMENTOS, PERM_VER_FINANZAS, PERM_VER_OPERACIONES,
        PERM_GESTIONAR_OPERACIONES, PERM_GESTIONAR_CATALOGO,
        PERM_GESTIONAR_INVENTARIO, PERM_VER_REPORTES,
    },
    ROLE_SUPERVISOR: {
        PERM_FIRMAR_DOCUMENTOS, PERM_VER_OPERACIONES,
        PERM_GESTIONAR_OPERACIONES, PERM_GESTIONAR_CATALOGO,
        PERM_GESTIONAR_INVENTARIO, PERM_VER_REPORTES,
    },
    ROLE_TECNICO: {PERM_FIRMAR_DOCUMENTOS, PERM_VER_OPERACIONES, PERM_GESTIONAR_OPERACIONES},
    ROLE_INVENTARIO: {PERM_VER_OPERACIONES, PERM_GESTIONAR_INVENTARIO, PERM_VER_REPORTES},
    ROLE_SOLO_LECTURA: {PERM_VER_OPERACIONES, PERM_VER_REPORTES},
}


def usuario_es_tecnico(user):
    """La capacidad de firma depende del perfil tecnico, no del rol."""
    return bool(
        user and user.is_authenticated
        and hasattr(user, 'technician_profile')
    )


def usuario_tiene_permiso(user, permiso):
    """Evalua permisos Django, manteniendo superusuarios como administradores."""
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.has_perm(permiso)


def puede_firmar_documentos(user):
    return usuario_es_tecnico(user)


def requiere_permiso(permiso):
    """Protege una vista y muestra una respuesta util cuando falta permiso."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not usuario_tiene_permiso(request.user, permiso):
                return render(request, '403.html', {
                    'permiso_requerido': permiso,
                }, status=403)
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

from pathlib import Path

from django.contrib.auth.models import Group, Permission, User
from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import resolve, reverse

from .models import Cliente, CategoriaProducto, Intervencion, Odt, Producto, ItemIntervencion
from .services.stock import StockInsuficiente, ajustar_stock, guardar_consumo_item, eliminar_consumo_item
from .models import TechnicianProfile
from .permissions import (
    PERM_GESTIONAR_USUARIOS,
    PERM_FIRMAR_DOCUMENTOS,
    ROLE_TECNICO,
    puede_firmar_documentos,
    usuario_tiene_permiso,
)


class ExtintoresUrlIntegrityTests(SimpleTestCase):
    """Contratos de rutas que no requieren una base de datos."""

    def test_statistics_fixed_route_is_not_captured_as_a_month(self):
        match = resolve('/estadisticas/ver/')

        self.assertEqual(match.url_name, 'ver_estadisticas_redirect')
        self.assertEqual(match.kwargs, {})

    def test_statistics_month_route_requires_a_month(self):
        self.assertEqual(
            reverse('ver_estadisticas', kwargs={'mes': '2026-08'}),
            '/estadisticas/2026-08/',
        )

    def test_ajax_routes_have_stable_names(self):
        self.assertEqual(reverse('buscar_clientes_ajax'), '/ajax/buscar-clientes/')
        self.assertEqual(reverse('buscar_productos_ajax'), '/ajax/buscar-productos/')


class ExtintoresTemplateIntegrityTests(SimpleTestCase):
    def test_statistics_template_has_no_empty_download_links(self):
        template_path = (
            Path(__file__).parent / 'templates' / 'estadisticas' / 'generar.html'
        )
        template = template_path.read_text(encoding='utf-8')

        self.assertNotIn('href=""', template)
        self.assertNotIn('Descargar Excel', template)
        self.assertNotIn('Descargar PDF', template)

    def test_ajax_templates_do_not_hardcode_root_urls(self):
        templates = (
            Path(__file__).parent / 'templates' / 'intervenciones' / 'crear.html',
            Path(__file__).parent / 'templates' / 'intervenciones' / 'editar_consumos.html',
        )

        for template_path in templates:
            template = template_path.read_text(encoding='utf-8')
            self.assertNotIn('fetch(`/ajax/', template)


class IntervencionOdtTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre='Cliente de prueba')

    def test_odt_can_exist_without_intervencion(self):
        odt = Odt.objects.create()

        self.assertIsNone(odt.intervencion)

    def test_intervencion_without_odt_does_not_create_one(self):
        intervencion = Intervencion.objects.create(
            cliente=self.cliente,
            tipo='revision',
            con_odt=False,
        )

        self.assertFalse(Odt.objects.filter(intervencion=intervencion).exists())

    def test_intervencion_can_have_one_explicit_odt(self):
        intervencion = Intervencion.objects.create(
            cliente=self.cliente,
            tipo='revision',
            con_odt=True,
        )
        odt = Odt.objects.create(intervencion=intervencion)

        self.assertEqual(intervencion.odt_rel, odt)
        self.assertEqual(Odt.objects.filter(intervencion=intervencion).count(), 1)


class StockServiceTests(TestCase):
    def setUp(self):
        categoria = CategoriaProducto.objects.create(nombre='Prueba')
        self.producto = Producto.objects.create(
            nombre='Producto de prueba', categoria=categoria, stock=10
        )
        self.cliente = Cliente.objects.create(nombre='Cliente de stock')
        self.intervencion = Intervencion.objects.create(
            cliente=self.cliente, tipo='revision', alias='INT-STOCK'
        )

    def test_consumption_rejects_insufficient_stock_without_changes(self):
        with self.assertRaises(StockInsuficiente):
            ajustar_stock(self.producto.pk, -11)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_consumption_and_deletion_restore_stock(self):
        item = ItemIntervencion(
            intervencion=self.intervencion, producto=self.producto, cantidad=3
        )
        guardar_consumo_item(item)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)

        eliminar_consumo_item(item)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)

    def test_item_model_save_does_not_change_stock_directly(self):
        item = ItemIntervencion.objects.create(
            intervencion=self.intervencion, producto=self.producto, cantidad=3
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        item.delete()


class PermissionTests(TestCase):
    def test_permission_can_be_granted_through_a_group(self):
        user = User.objects.create_user(username='supervisor')
        group = Group.objects.create(name='Supervisor')
        permission = Permission.objects.get(
            content_type__app_label='extintores', codename='manage_users'
        )
        group.permissions.add(permission)
        user.groups.add(group)

        self.assertTrue(usuario_tiene_permiso(user, PERM_GESTIONAR_USUARIOS))

    def test_technician_profile_grants_document_signature_without_admin_role(self):
        user = User.objects.create_user(username='tecnico')
        TechnicianProfile.objects.create(user=user)

        self.assertTrue(puede_firmar_documentos(user))

    def test_user_manager_can_assign_role_permission_and_technician_profile(self):
        manager = User.objects.create_superuser(
            username='manager', password='password123', email='manager@example.com'
        )
        target = User.objects.create_user(username='andres')
        self.client.force_login(manager)

        response = self.client.post(reverse('usuarios_simple'), {
            'action': 'editar',
            'user_id': target.pk,
            'first_name': '',
            'last_name': '',
            'email': '',
            'is_active': 'on',
            'roles': [ROLE_TECNICO],
            'permissions': [PERM_FIRMAR_DOCUMENTOS],
            'is_technician': 'on',
        })

        self.assertEqual(response.status_code, 302)
        target.refresh_from_db()
        self.assertTrue(target.groups.filter(name=ROLE_TECNICO).exists())
        self.assertTrue(target.has_perm(PERM_FIRMAR_DOCUMENTOS))
        self.assertTrue(hasattr(target, 'technician_profile'))

    def test_extintores_routes_require_authentication(self):
        response = self.client.get(reverse('lista_productos'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_authenticated_user_without_area_permission_is_rejected(self):
        user = User.objects.create_user(username='sin-permisos')
        self.client.force_login(user)

        response = self.client.get(reverse('agregar_producto'))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'No tienes autorización para esta sección', status_code=403)
        self.assertContains(response, 'extintores.manage_catalog', status_code=403)

    def test_user_management_button_uses_permission_not_username(self):
        template = (Path(__file__).parent / 'templates' / 'intervenciones' / 'lista.html').read_text(
            encoding='utf-8'
        )

        self.assertIn('perms.extintores.manage_users', template)
        self.assertNotIn("user.username == 'andres'", template)

    def test_technician_can_operate_but_not_manage_catalog(self):
        user = User.objects.create_user(username='tecnico-ruta')
        role = Group.objects.create(name='Tecnico')
        role.permissions.set(Permission.objects.filter(
            content_type__app_label='extintores',
            codename__in=['view_operations', 'manage_operations'],
        ))
        user.groups.add(role)
        self.client.force_login(user)

        self.assertNotEqual(
            self.client.get(reverse('intervencion_lista')).status_code, 403
        )
        self.assertEqual(self.client.get(reverse('agregar_producto')).status_code, 403)

    def test_inventory_role_can_manage_stock_but_not_interventions(self):
        user = User.objects.create_user(username='inventario-ruta')
        role = Group.objects.create(name='Inventario')
        role.permissions.set(Permission.objects.filter(
            content_type__app_label='extintores',
            codename__in=['view_operations', 'manage_inventory', 'view_reports'],
        ))
        user.groups.add(role)
        self.client.force_login(user)

        self.assertNotEqual(
            self.client.get(reverse('ingreso_stock_nuevo')).status_code, 403
        )
        self.assertEqual(self.client.get(reverse('intervencion_crear')).status_code, 403)

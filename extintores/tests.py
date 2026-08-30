from pathlib import Path

from django.test import SimpleTestCase
from django.test import TestCase
from django.urls import resolve, reverse

from .models import Cliente, CategoriaProducto, Intervencion, Odt, Producto, ItemIntervencion
from .services.stock import StockInsuficiente, ajustar_stock, guardar_consumo_item, eliminar_consumo_item


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

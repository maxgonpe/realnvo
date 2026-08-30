from pathlib import Path

from django.test import SimpleTestCase
from django.urls import resolve, reverse


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

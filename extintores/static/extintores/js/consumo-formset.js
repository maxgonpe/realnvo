(function () {
    function init() {
        var root = document.querySelector('[data-consumo-formset]');
        if (!root) return;
        var form = root.closest('form');
        if (!form) return;

        root.addEventListener('click', function (event) {
            var item = event.target.closest('.producto-result-item');
            if (item && parseFloat(item.dataset.productoStock || 0) < 100) {
                var modal = document.getElementById('modal-stock-bajo');
                var name = document.getElementById('modal-stock-bajo-nombre');
                if (modal && name && window.bootstrap) {
                    name.textContent = item.dataset.productoNombre || '';
                    new bootstrap.Modal(modal).show();
                }
            }
        });

        form.addEventListener('submit', function (event) {
            var errors = [];
            root.querySelectorAll('.producto-search').forEach(function (input, index) {
                var box = input.closest('.producto-search-container');
                var selected = box && box.querySelector('.producto-selected');
                var field = box && box.querySelector('[name="' + input.dataset.formPrefix + '-producto"]');
                if (selected && selected.style.display !== 'none' && (!field || !field.value)) {
                    errors.push('Línea ' + (index + 1) + ': Producto seleccionado pero no sincronizado');
                }
            });
            if (errors.length) {
                event.preventDefault();
                window.alert('Errores de sincronización:\n' + errors.join('\n'));
            }
        });
    }
    document.addEventListener('DOMContentLoaded', init);
}());

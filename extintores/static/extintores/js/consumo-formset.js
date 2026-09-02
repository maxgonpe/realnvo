(function () {
    function init() {
        var root = document.querySelector('[data-consumo-formset]');
        if (!root) return;
        var form = root.closest('form');
        if (!form) return;

        form.addEventListener('submit', function (event) {
            root.querySelectorAll('.producto-search').forEach(function (input) {
                var box = input.closest('.producto-search-container');
                var selected = box && box.querySelector('.producto-selected');
                var prefix = input.dataset.formPrefix;
                var field = box && (
                    box.querySelector('select[name="' + prefix + '-producto"]') ||
                    box.querySelector('input[name="' + prefix + '-producto"]')
                );
                if (!field && box && box.closest('.card')) {
                    field = box.closest('.card').querySelector('select[name*="producto"], input[name*="producto"]');
                }
                if (!field) field = form.querySelector('[name="' + prefix + '-producto"]');
                if (selected && field && !String(field.value || '').trim() && selected.dataset.productoId) {
                    field.value = selected.dataset.productoId;
                }
            });
        });
    }
    document.addEventListener('DOMContentLoaded', init);
}());

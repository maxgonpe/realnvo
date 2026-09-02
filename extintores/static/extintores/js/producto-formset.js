(function () {
    function escapeAttr(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;').replace(/"/g, '&quot;')
            .replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function fieldFor(prefix) {
        return document.querySelector('[name="' + prefix + '-producto"]') ||
            document.querySelector('#id_' + prefix + '-producto');
    }

    function fieldInBox(box, prefix) {
        return box.querySelector('select[name="' + prefix + '-producto"]') ||
            box.querySelector('input[name="' + prefix + '-producto"]') ||
            (box.closest('.card') && box.closest('.card').querySelector('select[name*="producto"], input[name*="producto"]')) ||
            fieldFor(prefix);
    }

    function init() {
        var root = document.querySelector('[data-producto-formset]');
        if (!root) return;
        window.productoFormsetInitialized = true;
        var searchUrl = root.dataset.searchUrl;
        var timers = {};

        function search(input) {
            var query = input.value;
            var results = input.parentElement.querySelector('.producto-results');
            if (query.length < 2) { if (results) results.style.display = 'none'; return; }
            fetch(searchUrl + '?q=' + encodeURIComponent(query))
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (!results) return;
                    results.innerHTML = (data.productos || []).map(function (product) {
                        var stock = product.stock === null ? 'Ilimitado' : (product.stock || 0);
                        return '<div class="producto-result-item p-2 border-bottom" data-stock-ilimitado="' +
                            (product.stock_ilimitado ? 'true' : 'false') + '" data-producto-id="' +
                            escapeAttr(product.id) + '" data-producto-nombre="' + escapeAttr(product.nombre) +
                            '" data-producto-categoria="' + escapeAttr(product.categoria) +
                            '" data-producto-precio="' + (product.precio || 0) + '" data-producto-stock="' +
                            (product.stock === null ? '' : product.stock) + '"><div class="producto-result-name fw-bold">' +
                            escapeAttr(product.nombre) + '</div><small class="text-muted">' +
                            escapeAttr(product.categoria) + ' | $' + (product.precio || 0) +
                            ' | Stock: ' + stock + '</small></div>';
                    }).join('') || '<div class="p-2 text-muted">No se encontraron productos</div>';
                    results.style.display = 'block';
                }).catch(function () { if (results) results.style.display = 'none'; });
        }

        document.addEventListener('input', function (event) {
            var input = event.target;
            if (!input.classList.contains('producto-search')) return;
            var key = input.dataset.formPrefix;
            clearTimeout(timers[key]);
            timers[key] = setTimeout(function () { search(input); }, 300);
        });
        document.addEventListener('click', function (event) {
            var item = event.target.closest('.producto-result-item');
            if (item) {
                var box = item.closest('.producto-search-container');
                var input = box.querySelector('.producto-search');
                var prefix = input.dataset.formPrefix;
                var field = fieldInBox(box, prefix);
                if (field) field.value = item.dataset.productoId;
                var selected = box.querySelector('.producto-selected');
                selected.dataset.productoId = item.dataset.productoId;
                box.querySelector('.producto-nombre').textContent = item.dataset.productoNombre;
                box.querySelector('.producto-details').textContent = item.dataset.productoCategoria +
                    ' | $' + item.dataset.productoPrecio + ' | Stock: ' +
                    (item.dataset.stockIlimitado === 'true' ? 'Ilimitado' : item.dataset.productoStock);
                input.style.display = 'none';
                box.querySelector('.producto-results').style.display = 'none';
                box.querySelector('.producto-selected').style.display = 'block';
                return;
            }
            var clear = event.target.closest('.producto-clear');
            if (clear) {
                var boxToClear = clear.closest('.producto-search-container');
                var clearInput = boxToClear.querySelector('.producto-search');
                var clearField = fieldFor(clearInput.dataset.formPrefix);
                if (clearField) clearField.value = '';
                clearInput.value = '';
                delete boxToClear.querySelector('.producto-selected').dataset.productoId;
                clearInput.style.display = 'block';
                boxToClear.querySelector('.producto-selected').style.display = 'none';
                boxToClear.querySelector('.producto-results').style.display = 'none';
            } else if (!event.target.closest('.producto-search-container')) {
                document.querySelectorAll('.producto-results').forEach(function (el) { el.style.display = 'none'; });
            }
        });

        document.querySelectorAll('.producto-search').forEach(function (input) {
            var field = fieldFor(input.dataset.formPrefix);
            var selected = input.parentElement.querySelector('.producto-selected');
            if (field && field.value && selected) {
                var option = field.querySelector('option[value="' + field.value + '"]');
                if (option) {
                    selected.querySelector('.producto-nombre').textContent = option.textContent;
                    selected.querySelector('.producto-details').textContent = 'Producto seleccionado';
                    selected.dataset.productoId = field.value;
                    input.style.display = 'none';
                    selected.style.display = 'block';
                }
            }
        });

        var button = document.getElementById(root.dataset.addButtonId || 'add-form');
        var total = document.getElementById(root.dataset.totalFormsId);
        var template = document.getElementById('empty-form');
        var container = root;
        if (button && total && template && container) button.addEventListener('click', function () {
            var index = parseInt(total.value, 10);
            var html = template.innerHTML.replace(/__prefix__/g, index);
            var wrapper = document.createElement('div'); wrapper.innerHTML = html;
            container.appendChild(wrapper.firstElementChild); total.value = index + 1;
        });
    }
    document.addEventListener('DOMContentLoaded', init);
}());

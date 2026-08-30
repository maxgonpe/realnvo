(function (window, document) {
    'use strict';

    function initialize() {
        var input = document.getElementById('busqueda');
        var results = document.getElementById('resultados-odt');
        if (!input || !results) return;

        var request;
        input.addEventListener('input', function () {
            if (request) request.abort();
            request = new AbortController();
            results.setAttribute('aria-busy', 'true');
            fetch(window.location.pathname + '?q=' + encodeURIComponent(input.value), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                signal: request.signal
            }).then(function (response) {
                if (!response.ok) throw new Error('Search failed');
                return response.json();
            }).then(function (data) {
                results.innerHTML = data.html || '<p class="text-muted">No se encontraron ODT.</p>';
            }).catch(function (error) {
                if (error.name !== 'AbortError') {
                    results.innerHTML = '<p class="text-danger">No se pudieron cargar los resultados.</p>';
                }
            }).finally(function () {
                results.removeAttribute('aria-busy');
            });
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(window, document));

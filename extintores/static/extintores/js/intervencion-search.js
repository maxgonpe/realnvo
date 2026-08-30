(function (window, document) {
    'use strict';

    function initialize() {
        var input = document.getElementById('searchInput');
        var container = document.getElementById('intervenciones-container');
        if (!input || !container) return;
        var ajaxUrl = input.dataset.ajaxUrl;
        var timer;
        var request;

        function load(query) {
            if (request) request.abort();
            request = new AbortController();
            container.setAttribute('aria-busy', 'true');
            fetch(ajaxUrl + '?q=' + encodeURIComponent(query), {
                signal: request.signal,
                headers: { 'X-Requested-With': 'XMLHttpRequest' }
            }).then(function (response) {
                if (!response.ok) throw new Error('Search failed');
                return response.json();
            }).then(function (data) {
                container.innerHTML = data.html || '';
            }).catch(function (error) {
                if (error.name !== 'AbortError') {
                    container.setAttribute('data-search-error', 'true');
                }
            }).finally(function () {
                container.removeAttribute('aria-busy');
            });
        }

        input.addEventListener('input', function () {
            clearTimeout(timer);
            timer = setTimeout(function () { load(input.value); }, 200);
        });
        if (input.value.trim()) load(input.value);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(window, document));

(function (document) {
    'use strict';

    function initialize() {
        var filterInput = document.getElementById('filterInput');
        if (!filterInput) return;
        var cards = document.querySelectorAll('.card');

        filterInput.addEventListener('input', function () {
            var filterValue = filterInput.value.toLowerCase();
            cards.forEach(function (card) {
                card.style.display = card.textContent.toLowerCase().includes(filterValue)
                    ? 'block'
                    : 'none';
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }
}(document));

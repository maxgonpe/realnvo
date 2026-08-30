(function (document) {
    'use strict';

    function initialize() {
        document.querySelectorAll('[data-add-formset]').forEach(function (button) {
            var total = document.getElementById(button.dataset.totalId);
            var container = document.getElementById(button.dataset.containerId);
            var template = document.getElementById(button.dataset.templateId);
            if (!total || !container || !template) return;
            button.addEventListener('click', function () {
                var index = parseInt(total.value, 10);
                container.insertAdjacentHTML('beforeend', template.innerHTML.replace(/__prefix__/g, index));
                total.value = index + 1;
            });
        });
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(document));

(function (document, window) {
    'use strict';

    function addForm(buttonId, containerId, totalId, templateId) {
        var button = document.getElementById(buttonId);
        if (!button) return;
        button.addEventListener('click', function () {
            var container = document.getElementById(containerId);
            var totalForms = document.getElementById(totalId);
            var template = document.getElementById(templateId);
            var index = parseInt(totalForms.value, 10);
            var wrapper = document.createElement('div');
            wrapper.innerHTML = template.innerHTML.replace(/__prefix__/g, index);
            container.appendChild(wrapper.firstElementChild || wrapper);
            totalForms.value = index + 1;
        });
    }

    function initialize() {
        addForm('add-formset', 'formset-container', 'id_detalleodt-TOTAL_FORMS', 'empty-formset');
        addForm('add-itemset', 'itemset-container', 'id_itemodt_set-TOTAL_FORMS', 'empty-itemset');
    }

    window.scrollToTop = function () { window.scrollTo({ top: 0, behavior: 'smooth' }); };
    window.scrollToBottom = function () { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); };
    window.scrollDown = function () { window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' }); };
    window.scrollUp = function () { window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' }); };

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(document, window));

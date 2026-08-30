(function (document, window) {
    'use strict';

    function initialize() {
        var button = document.getElementById('add-form');
        if (!button) return;
        button.addEventListener('click', function () {
            var container = document.getElementById(button.dataset.containerId);
            var total = document.getElementById(button.dataset.totalId);
            var template = document.getElementById(button.dataset.templateId);
            var index = parseInt(total.value, 10);
            container.insertAdjacentHTML('beforeend', template.innerHTML.replace(/__prefix__/g, index));
            total.value = index + 1;
            var card = container.lastElementChild;
            var counter = card && card.querySelector('.form-counter');
            var watermark = card && card.querySelector('.watermark-card');
            if (counter) counter.textContent = index + 1;
            if (watermark) watermark.textContent = '#' + (index + 1);
        });
    }

    window.scrollToTop = function () { window.scrollTo({ top: 0, behavior: 'smooth' }); };
    window.scrollToBottom = function () { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); };
    window.scrollDown = function () { window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' }); };
    window.scrollUp = function () { window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' }); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(document, window));

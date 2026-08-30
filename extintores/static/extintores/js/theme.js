(function (window, document) {
    'use strict';

    function applyTheme(theme) {
        var body = document.body;
        var validThemes = ['red', 'yellow', 'blue', 'gray'];
        if (validThemes.indexOf(theme) === -1) {
            theme = 'red';
        }
        validThemes.forEach(function (name) {
            body.classList.remove('theme-' + name);
        });
        body.classList.add('theme-' + theme);
        try {
            localStorage.setItem('theme', theme);
        } catch (error) {
            // The visual theme must still work when storage is unavailable.
        }
    }

    function initialize() {
        var savedTheme = 'red';
        try {
            savedTheme = localStorage.getItem('theme') || 'red';
        } catch (error) {
            // Use the default theme when storage is unavailable.
        }
        applyTheme(savedTheme);
    }

    window.setTheme = applyTheme;
    document.addEventListener('click', function (event) {
        var button = event.target.closest('.theme-btn');
        if (button) applyTheme(button.getAttribute('data-theme'));
    });

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(window, document));

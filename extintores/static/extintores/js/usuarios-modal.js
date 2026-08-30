(function (document) {
    'use strict';
    var modalEditar = document.getElementById('modalEditar');
    if (modalEditar) modalEditar.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        if (!button) return;
        document.getElementById('editar_user_id').value = button.dataset.id;
        document.getElementById('editar_username_display').textContent = button.dataset.username || '';
        document.getElementById('editar_first_name').value = button.dataset.first || '';
        document.getElementById('editar_last_name').value = button.dataset.last || '';
        document.getElementById('editar_email').value = button.dataset.email || '';
        document.getElementById('editar_is_active').checked = button.dataset.active === '1';
        document.getElementById('editar_is_technician').checked = button.dataset.technician === '1';
        var roles = (button.dataset.roles || '').split(',').filter(Boolean);
        document.querySelectorAll('#modalEditar .role-check').forEach(function (input) { input.checked = roles.indexOf(input.value) !== -1; });
        var permissions = (button.dataset.permissions || '').split(',').filter(Boolean);
        document.querySelectorAll('#modalEditar .permission-check').forEach(function (input) { input.checked = permissions.indexOf(input.value) !== -1; });
    });
    var modalPassword = document.getElementById('modalPassword');
    if (modalPassword) modalPassword.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        if (!button) return;
        document.getElementById('password_user_id').value = button.dataset.id;
        document.getElementById('password_username_display').textContent = button.dataset.username || '';
    });
}(document));

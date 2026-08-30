(function () {
    function escapeHtml(value) {
        const element = document.createElement('span');
        element.textContent = value == null ? '' : value;
        return element.innerHTML;
    }

    function init() {
        const clienteSearch = document.getElementById('cliente-search');
        if (!clienteSearch) return;

        const clienteResults = document.getElementById('cliente-results');
        const clienteId = document.getElementById('cliente-id');
        const clienteSelected = document.getElementById('cliente-selected');
        const clienteNombre = document.getElementById('cliente-nombre');
        const clienteDetails = document.getElementById('cliente-details');
        const clienteClear = document.getElementById('cliente-clear');
        const searchUrl = clienteSearch.dataset.searchUrl;

        let searchTimeout;
        let currentResults = [];

        function buscarClientes(query) {
            if (query.length < 2) {
                clienteResults.style.display = 'none';
                return;
            }

            fetch(`${searchUrl}?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    currentResults = data.clientes;
                    mostrarResultados(data.clientes);
                })
                .catch(error => {
                    console.error('Error en búsqueda:', error);
                    clienteResults.style.display = 'none';
                });
        }

        function mostrarResultados(clientes) {
            if (clientes.length === 0) {
                clienteResults.innerHTML = '<div class="cliente-result-item text-muted">No se encontraron clientes</div>';
            } else {
                clienteResults.innerHTML = clientes.map(cliente => `
                    <div class="cliente-result-item" data-cliente-id="${cliente.id}">
                        <div class="cliente-result-name">${escapeHtml(cliente.nombre)}</div>
                        <div class="cliente-result-details">
                            ${cliente.rut ? `RUT: ${escapeHtml(cliente.rut)}` : ''}
                            ${cliente.telefono ? ` | Tel: ${escapeHtml(cliente.telefono)}` : ''}
                            ${cliente.correo ? ` | ${escapeHtml(cliente.correo)}` : ''}
                        </div>
                    </div>
                `).join('');
            }
            clienteResults.style.display = 'block';
        }

        clienteSearch.addEventListener('input', function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => buscarClientes(this.value), 300);
        });

        clienteResults.addEventListener('click', function (event) {
            const item = event.target.closest('.cliente-result-item');
            if (!item) return;
            const cliente = currentResults.find(c => c.id == item.dataset.clienteId);
            if (cliente) seleccionarCliente(cliente);
        });

        function seleccionarCliente(cliente) {
            clienteId.value = cliente.id;
            clienteNombre.textContent = cliente.nombre;
            clienteDetails.textContent = `${cliente.rut || 'Sin RUT'} | ${cliente.telefono || 'Sin teléfono'} | ${cliente.correo || 'Sin correo'}`;

            const formClienteField = document.querySelector('select[name="cliente"]');
            if (formClienteField) formClienteField.value = cliente.id;

            clienteSearch.style.display = 'none';
            clienteResults.style.display = 'none';
            clienteSelected.style.display = 'block';
        }

        clienteClear.addEventListener('click', function () {
            clienteId.value = '';
            clienteSearch.value = '';

            const formClienteField = document.querySelector('select[name="cliente"]');
            if (formClienteField) formClienteField.value = '';

            clienteSearch.style.display = 'block';
            clienteSelected.style.display = 'none';
            clienteResults.style.display = 'none';
        });

        document.addEventListener('click', function (event) {
            if (!event.target.closest('.cliente-search-container')) {
                clienteResults.style.display = 'none';
            }
        });

        document.querySelector('form').addEventListener('submit', function (event) {
            const formClienteField = document.querySelector('select[name="cliente"]');
            if (!formClienteField || !formClienteField.value) {
                event.preventDefault();
                alert('Por favor seleccione un cliente antes de continuar.');
                clienteSearch.focus();
                return false;
            }
        });
    }

    document.addEventListener('DOMContentLoaded', init);
}());

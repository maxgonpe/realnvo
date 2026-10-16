(function (document, window) {
    'use strict';

    function initialize() {
        const button = document.getElementById('add-form');
        if (!button) return;
        const container = document.getElementById(button.dataset.containerId);
        const total = document.getElementById(button.dataset.totalId);
        const template = document.getElementById(button.dataset.templateId);
        if (!container || !total || !template) return;
        const MAX_PER_BATCH = 325;

        function addForm(options = {}) {
            const index = Number.parseInt(total.value, 10);
            if (!Number.isInteger(index) || index < 0) return null;
            container.insertAdjacentHTML('beforeend', template.innerHTML.replace(/__prefix__/g, index));
            total.value = String(index + 1);
            const card = container.lastElementChild;
            if (!card) return null;
            const counter = card.querySelector('.form-counter');
            const watermark = card.querySelector('.watermark-card');
            if (counter) counter.textContent = '#' + (index + 1);
            if (watermark) watermark.textContent = '#' + (index + 1);
            function applyValue(name, value) {
                if (value === undefined || value === null || value === '') return;
                const field = card.querySelector('[name="detalles-' + index + '-' + name + '"]');
                if (field) field.value = String(value);
            }
            applyValue('agente', options.agente);
            applyValue('ubicacion', options.ubicacion);
            applyValue('ultima_fecha', options.ultimaFecha);
            applyValue('nro_precinto', options.nroPrecinto);
            return card;
        }

        // Mantener intacta la acción individual que ya utiliza edición.
        button.addEventListener('click', function () { addForm(); });

        const openButton = document.getElementById('btnMultiExtintores');
        const generateButton = document.getElementById('btnGenerarExtintores');
        const modalEl = document.getElementById('multiExtModal');
        if (!openButton || !generateButton || !modalEl) return;

        const cantidadEl = document.getElementById('cantExtintores');
        const agenteEl = document.getElementById('agentePredeterminado');
        const ubicacionEl = document.getElementById('ubicacionPredeterminada');
        const fechaEl = document.getElementById('ultimaFechaPredeterminada');
        const precintoEl = document.getElementById('precintoInicial');
        const previewEl = document.getElementById('multiExtPreview');

        function numericInput(raw) {
            if (!/^(0|[1-9]\d*)$/.test(String(raw).trim())) return null;
            const value = Number(raw);
            return Number.isSafeInteger(value) ? value : null;
        }

        function preview() {
            const qty = numericInput(cantidadEl.value);
            const start = numericInput(precintoEl.value);
            if (qty === null || qty < 1 || qty > MAX_PER_BATCH) {
                previewEl.textContent = 'La cantidad debe ser un entero entre 1 y ' + MAX_PER_BATCH + '.';
                return;
            }
            if (start === null) {
                previewEl.textContent = 'Indique un número de precinto inicial entero no negativo.';
                return;
            }
            if ((!Number.isSafeInteger(start + qty - 1) || start + qty - 1 > 2147483647)) {
                previewEl.textContent = 'El rango de precintos excede la precisión numérica permitida.';
                return;
            }
            const first = Number.parseInt(total.value, 10) + 1;
            const lines = [];
            for (let i = 0; i < Math.min(qty, 5); i++) {
                lines.push('Extintor #' + (first + i) + ' · Precinto ' + (start + i));
            }
            if (qty > 5) lines.push('... y ' + (qty - 5) + ' más; último precinto ' + (start + qty - 1));
            previewEl.textContent = lines.join('\n');
            previewEl.style.whiteSpace = 'pre-line';
        }

        [cantidadEl, ubicacionEl, fechaEl, precintoEl].forEach(function (el) {
            el.addEventListener('input', preview);
            el.addEventListener('change', preview);
        });

        openButton.addEventListener('click', function () {
            const fechaServicio = document.querySelector('input[name="fecha"]');
            if (fechaServicio && fechaServicio.value && !fechaEl.value) fechaEl.value = fechaServicio.value;
            try {
                const siguiente = window.sessionStorage.getItem('realnvo_precinto_siguiente');
                if (siguiente && !precintoEl.value) precintoEl.value = siguiente;
            } catch (error) { /* sessionStorage es opcional */ }
            preview();
            if (window.bootstrap && window.bootstrap.Modal) {
                window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
            } else {
                window.alert('Bootstrap Modal no está disponible en esta página.');
            }
        });

        generateButton.addEventListener('click', function () {
            const qty = numericInput(cantidadEl.value);
            const start = numericInput(precintoEl.value);
            if (qty === null || qty < 1 || qty > MAX_PER_BATCH) {
                window.alert('Ingrese una cantidad entera entre 1 y ' + MAX_PER_BATCH + '.'); return;
            }
            if (!agenteEl.value) { window.alert('Seleccione un agente predeterminado.'); return; }
            if (start === null || !Number.isSafeInteger(start + qty - 1) || start + qty - 1 > 2147483647) {
                window.alert('Ingrese un número de precinto inicial válido.'); return;
            }
            // Django limita por defecto la cantidad total de formularios del formset.
            // Conservar el máximo 2000 del formset en la interfaz para evitar descartar datos.
            const oldTotal = numericInput(total.value);
            if (oldTotal === null || oldTotal + qty > 2000) {
                window.alert('El total de formularios excede el límite de Django (2000).'); return;
            }
            const options = {
                agente: agenteEl.value,
                ubicacion: ubicacionEl.value.trim(),
                ultimaFecha: fechaEl.value
            };
            let firstCard = null;
            for (let i = 0; i < qty; i++) {
                const card = addForm(Object.assign({}, options, { nroPrecinto: start + i }));
                if (!firstCard) firstCard = card;
            }
            try { window.sessionStorage.setItem('realnvo_precinto_siguiente', String(start + qty)); }
            catch (error) { /* sessionStorage es opcional */ }
            if (window.bootstrap && window.bootstrap.Modal) {
                window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
            }
            if (firstCard) firstCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
        });
    }

    window.scrollToTop = function () { window.scrollTo({ top: 0, behavior: 'smooth' }); };
    window.scrollToBottom = function () { window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }); };
    window.scrollDown = function () { window.scrollBy({ top: window.innerHeight * 0.8, behavior: 'smooth' }); };
    window.scrollUp = function () { window.scrollBy({ top: -window.innerHeight * 0.8, behavior: 'smooth' }); };
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initialize);
    else initialize();
}(document, window));

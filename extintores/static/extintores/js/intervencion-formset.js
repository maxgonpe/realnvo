document.addEventListener('DOMContentLoaded', function() {
    const root = document.querySelector('[data-intervencion-formset]');
    if (!root) return;
    const prefix = root.dataset.prefix;
    const emptyForm = document.getElementById('empty-form').innerHTML;
    const formContainer = document.getElementById('form-container');
    const emptyState = document.getElementById('empty-state');
    const totalForms = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    let formCounter = parseInt(totalForms.value) || 0;
    function escapeHtml(value) {
        const element = document.createElement('span');
        element.textContent = value == null ? '' : value;
        return element.innerHTML;
    }

    function agregarFormulario(opciones = {}) {
        const agente = opciones.agente || null;
        const ubicacion = opciones.ubicacion || '';
        const ultimaFecha = opciones.ultimaFecha || '';
        const nroPrecinto = opciones.nroPrecinto;
        if(emptyState) emptyState.style.display = 'none';
        const newIndex = formCounter;
        const newFormHtml = emptyForm.replace(/__prefix__/g, newIndex)
            .replace(new RegExp(`${prefix}-__prefix__`, 'g'), `${prefix}-${newIndex}`)
            .replace(new RegExp(`id_${prefix}-__prefix__`, 'g'), `id_${prefix}-${newIndex}`);
        formContainer.insertAdjacentHTML('beforeend', newFormHtml);
        const newCard = formContainer.lastElementChild;
        const counterSpan = newCard.querySelector('.form-counter');
        if(counterSpan) counterSpan.textContent = `#${formCounter + 1}`;
        if(agente) { const field = newCard.querySelector(`select[name="${prefix}-${newIndex}-agente"]`); if(field) field.value = agente; }
        if(ubicacion) { const field = newCard.querySelector(`input[name="${prefix}-${newIndex}-ubicacion"]`); if(field) field.value = ubicacion; }
        if(ultimaFecha) { const field = newCard.querySelector(`input[name="${prefix}-${newIndex}-ultima_fecha"]`); if(field) field.value = ultimaFecha; }
        if(nroPrecinto !== undefined && nroPrecinto !== null && nroPrecinto !== '') { const field = newCard.querySelector(`input[name="${prefix}-${newIndex}-nro_precinto"]`); if(field) field.value = nroPrecinto; }
        formCounter++; totalForms.value = formCounter; return newCard;
    }
    document.getElementById('add-form').addEventListener('click', function() { agregarFormulario(); });
    function agregarMultiplesFormularios(cantidad, agente, ubicacion, precintoInicial, ultimaFecha) {
        const base = parseInt(precintoInicial, 10), usar = !Number.isNaN(base); let primero = null;
        for(let i = 0; i < cantidad; i++) { const card = agregarFormulario({ agente, ubicacion, ultimaFecha, nroPrecinto: usar ? base + i : null }); if(i === 0) primero = card; }
        if(primero) { primero.scrollIntoView({ behavior: 'smooth', block: 'center' }); primero.classList.add('border', 'border-success'); setTimeout(() => primero.classList.remove('border', 'border-success'), 2500); }
    }
    function formatearFechaPreview(fecha) { if(!fecha) return '(sin fecha)'; const partes = fecha.split('-'); if(partes.length !== 3) return fecha; return `${partes[2]}/${partes[1]}/${partes[0]}`; }
    function actualizarVistaPreviaMultiExt() {
        const preview = document.getElementById('multiExtPreview'), cantidad = parseInt(document.getElementById('cantExtintores').value, 10) || 0;
        const ubicacion = document.getElementById('ubicacionPredeterminada').value.trim(), fecha = document.getElementById('ultimaFechaPredeterminada').value, inicial = document.getElementById('precintoInicial').value.trim();
        if(cantidad < 1 || cantidad > 325) { preview.innerHTML = '<span class="text-danger">Cantidad debe estar entre 1 y 325.</span>'; return; }
        if(!inicial) { preview.innerHTML = '<span class="text-warning">Indique el N° de precinto inicial para ver la numeración.</span>'; return; }
        const base = parseInt(inicial, 10); if(Number.isNaN(base)) { preview.innerHTML = '<span class="text-danger">El precinto inicial debe ser un número entero.</span>'; return; }
        const filas = [], mostrar = Math.min(cantidad, 5), fechaTxt = formatearFechaPreview(fecha);
        const ubicacionSegura = escapeHtml(ubicacion || '(sin ubicación)');
        const fechaSegura = escapeHtml(fechaTxt);
        for(let i = 0; i < mostrar; i++) filas.push(`<div><strong>#${i + 1}</strong> Precinto <code>${base + i}</code> · ${ubicacionSegura} · ${fechaSegura}</div>`);
        if(cantidad > mostrar) filas.push(`<div class="text-muted mt-1">… y ${cantidad - mostrar} extintor${cantidad - mostrar === 1 ? '' : 'es'} más hasta precinto <code>${base + cantidad - 1}</code></div>`);
        preview.innerHTML = filas.join('');
    }
    ['cantExtintores', 'ubicacionPredeterminada', 'precintoInicial', 'ultimaFechaPredeterminada'].forEach(id => { document.getElementById(id).addEventListener('input', actualizarVistaPreviaMultiExt); document.getElementById(id).addEventListener('change', actualizarVistaPreviaMultiExt); });
    document.getElementById('btnMultiExtintores').addEventListener('click', function() {
        const fecha = document.getElementById('ultimaFechaPredeterminada'), servicio = document.querySelector('input[name="fecha"]');
        if(servicio && servicio.value && !fecha.value) fecha.value = servicio.value;
        actualizarVistaPreviaMultiExt(); new bootstrap.Modal(document.getElementById('multiExtModal')).show();
    });
    document.getElementById('btnGenerarExtintores').addEventListener('click', function() {
        const cantidad = parseInt(document.getElementById('cantExtintores').value, 10) || 0, agente = document.getElementById('agentePredeterminado').value, ubicacion = document.getElementById('ubicacionPredeterminada').value.trim(), fecha = document.getElementById('ultimaFechaPredeterminada').value, inicial = document.getElementById('precintoInicial').value.trim();
        if(cantidad < 1 || cantidad > 325) { alert('Ingrese una cantidad válida entre 1 y 325.'); return; } if(!agente) { alert('Seleccione un agente predeterminado.'); return; } if(!inicial) { alert('Ingrese el número de precinto inicial.'); return; } if(Number.isNaN(parseInt(inicial, 10))) { alert('El precinto inicial debe ser un número entero.'); return; }
        agregarMultiplesFormularios(cantidad, agente, ubicacion, inicial, fecha); try { sessionStorage.setItem('realnvo_precinto_siguiente', String(parseInt(inicial, 10) + cantidad)); } catch (e) {}
        bootstrap.Modal.getInstance(document.getElementById('multiExtModal')).hide();
    });
    try { const siguiente = sessionStorage.getItem('realnvo_precinto_siguiente'); if(siguiente && !document.getElementById('precintoInicial').value) document.getElementById('precintoInicial').value = siguiente; } catch (e) {}
});

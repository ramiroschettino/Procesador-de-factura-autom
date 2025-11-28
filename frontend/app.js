// ===== Configuración =====
const API_BASE = 'http://localhost:5000/api';

// ===== Estado de la Aplicación =====
let state = {
    facturaFile: null,
    facturaFilename: null,
    ocFile: null,
    ocFilename: null,
    processing: false
};

// ===== Elementos DOM =====
const elements = {
    // Tabs
    tabs: document.querySelectorAll('.tab'),
    tabContents: document.querySelectorAll('.tab-content'),

    // Factura
    invoiceUploadArea: document.getElementById('invoiceUploadArea'),
    invoiceInput: document.getElementById('invoiceInput'),
    invoiceFileItem: document.getElementById('invoiceFileItem'),
    btnProcessInvoice: document.getElementById('btnProcessInvoice'),
    btnExtractOnly: document.getElementById('btnExtractOnly'),
    logsCard: document.getElementById('logsCard'),
    logsContainer: document.getElementById('logsContainer'),
    resultsCard: document.getElementById('resultsCard'),
    resultDetails: document.getElementById('resultDetails'),

    // OC
    ocUploadArea: document.getElementById('ocUploadArea'),
    ocInput: document.getElementById('ocInput'),
    ocFileItem: document.getElementById('ocFileItem'),
    btnSearchProvider: document.getElementById('btnSearchProvider'),
    logsOcCard: document.getElementById('logsOcCard'),
    logsOcContainer: document.getElementById('logsOcContainer'),
    providerResultsCard: document.getElementById('providerResultsCard'),
    providerResults: document.getElementById('providerResults'),

    // Historial
    historyList: document.getElementById('historyList'),
    btnRefreshHistory: document.getElementById('btnRefreshHistory'),

    // Global
    loadingOverlay: document.getElementById('loadingOverlay'),
    loadingText: document.getElementById('loadingText'),
    statusDot: document.getElementById('statusDot'),
    statusText: document.getElementById('statusText')
};

// ===== Inicialización =====
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    checkServerStatus();
    loadHistory();
});

function initializeEventListeners() {
    // Tabs
    elements.tabs.forEach(tab => {
        tab.addEventListener('click', () => switchTab(tab.dataset.tab));
    });

    // Upload de factura
    elements.invoiceUploadArea.addEventListener('click', () => elements.invoiceInput.click());
    elements.invoiceInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0], 'invoice'));
    setupDragAndDrop(elements.invoiceUploadArea, elements.invoiceInput);

    // Upload de OC
    elements.ocUploadArea.addEventListener('click', () => elements.ocInput.click());
    elements.ocInput.addEventListener('change', (e) => handleFileSelect(e.target.files[0], 'oc'));
    setupDragAndDrop(elements.ocUploadArea, elements.ocInput);

    // Botones
    elements.btnProcessInvoice.addEventListener('click', processInvoice);
    elements.btnExtractOnly.addEventListener('click', extractOnly);
    elements.btnSearchProvider.addEventListener('click', searchProvider);
    elements.btnRefreshHistory.addEventListener('click', loadHistory);
}

// ===== Tabs =====
function switchTab(tabName) {
    elements.tabs.forEach(tab => {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
    });

    elements.tabContents.forEach(content => {
        content.classList.toggle('active', content.id === `tab-${tabName}`);
    });
}

// ===== Drag & Drop =====
function setupDragAndDrop(area, input) {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        area.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        area.addEventListener(eventName, () => area.classList.add('dragover'), false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        area.addEventListener(eventName, () => area.classList.remove('dragover'), false);
    });

    area.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            input.files = files;
            input.dispatchEvent(new Event('change'));
        }
    }, false);
}

// ===== Manejo de Archivos =====
function handleFileSelect(file, type) {
    if (!file) return;

    if (!validateFile(file)) {
        alert('Archivo no válido. Solo PDF, PNG, JPG (máx. 16MB)');
        return;
    }

    if (type === 'invoice') {
        state.facturaFile = file;
        state.facturaFilename = file.name;
        elements.invoiceUploadArea.style.display = 'none';
        elements.invoiceFileItem.style.display = 'flex';
        elements.invoiceFileItem.querySelector('.filename').textContent = file.name;
        elements.btnProcessInvoice.disabled = false;
        elements.btnExtractOnly.disabled = false;
        uploadFile(file, 'factura');
    } else if (type === 'oc') {
        state.ocFile = file;
        state.ocFilename = file.name;
        elements.ocUploadArea.style.display = 'none';
        elements.ocFileItem.style.display = 'flex';
        elements.ocFileItem.querySelector('.filename').textContent = file.name;
        elements.btnSearchProvider.disabled = false;
        uploadFile(file, 'factura'); // Usa el mismo endpoint
    }
}

function validateFile(file) {
    const validTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    const maxSize = 16 * 1024 * 1024; // 16MB
    return validTypes.includes(file.type) && file.size <= maxSize;
}

window.removeFile = function (type) {
    if (type === 'invoice') {
        state.facturaFile = null;
        state.facturaFilename = null;
        elements.invoiceInput.value = '';
        elements.invoiceUploadArea.style.display = 'flex';
        elements.invoiceFileItem.style.display = 'none';
        elements.btnProcessInvoice.disabled = true;
        elements.btnExtractOnly.disabled = true;
    } else if (type === 'oc') {
        state.ocFile = null;
        state.ocFilename = null;
        elements.ocInput.value = '';
        elements.ocUploadArea.style.display = 'flex';
        elements.ocFileItem.style.display = 'none';
        elements.btnSearchProvider.disabled = true;
    }
}

// ===== Upload de Archivos =====
async function uploadFile(file, fieldName) {
    const formData = new FormData();
    formData.append(fieldName, file);

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Error al subir archivo');
        const data = await response.json();
        console.log('Archivo subido:', data);
    } catch (error) {
        console.error('Error:', error);
        alert('Error al subir archivo: ' + error.message);
    }
}

// ===== Procesamiento de Factura =====
async function processInvoice() {
    if (!state.facturaFilename || state.processing) return;

    state.processing = true;
    showLoading('Procesando factura completa...');

    // Mostrar logs
    elements.logsCard.style.display = 'block';
    elements.logsContainer.innerHTML = '';
    elements.resultsCard.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/process`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                factura_filename: state.facturaFilename
            })
        });

        if (!response.ok) throw new Error('Error en el procesamiento');

        const result = await response.json();
        displayResults(result);
        loadHistory();

    } catch (error) {
        console.error('Error:', error);
        addLog('error', 'Error en el procesamiento: ' + error.message);
        alert('Error en el procesamiento: ' + error.message);
    } finally {
        state.processing = false;
        hideLoading();
    }
}

async function extractOnly() {
    if (!state.facturaFilename || state.processing) return;

    state.processing = true;
    showLoading('Extrayendo datos de la factura...');

    elements.logsCard.style.display = 'block';
    elements.logsContainer.innerHTML = '';
    elements.resultsCard.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/extract`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                factura_filename: state.facturaFilename
            })
        });

        if (!response.ok) throw new Error('Error en la extracción');

        const result = await response.json();
        displayExtractionOnly(result.data);

    } catch (error) {
        console.error('Error:', error);
        addLog('error', 'Error en la extracción: ' + error.message);
        alert('Error en la extracción: ' + error.message);
    } finally {
        state.processing = false;
        hideLoading();
    }
}

// ===== Búsqueda de Proveedor =====
async function searchProvider() {
    if (!state.ocFilename || state.processing) return;

    state.processing = true;
    showLoading('Buscando proveedor...');

    // Mostrar logs
    elements.logsOcCard.style.display = 'block';
    elements.logsOcContainer.innerHTML = '';
    elements.providerResultsCard.style.display = 'none';

    addLogOc('info', '🔍 Iniciando búsqueda automática de proveedor...');

    try {
        const response = await fetch(`${API_BASE}/process_oc_auto`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                oc_filename: state.ocFilename
            })
        });

        if (!response.ok) throw new Error('Error en la búsqueda');

        const result = await response.json();
        displayProviderResults(result);

    } catch (error) {
        console.error('Error:', error);
        addLogOc('error', '❌ Error en la búsqueda: ' + error.message);
        alert('Error en la búsqueda: ' + error.message);
    } finally {
        state.processing = false;
        hideLoading();
    }
}

// ===== Visualización de Resultados =====
function displayResults(result) {
    elements.resultsCard.style.display = 'block';

    let html = '<div class="result-summary">';

    if (result.success) {
        html += '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Factura procesada exitosamente</div>';
    } else {
        html += '<div class="alert alert-error"><i class="fas fa-exclamation-circle"></i> Error al procesar factura</div>';
    }

    if (result.extraction) {
        html += '<h4><i class="fas fa-file-invoice"></i> Datos Extraídos:</h4>';
        html += `<pre>${JSON.stringify(result.extraction, null, 2)}</pre>`;
    }

    if (result.reconciliation) {
        html += '<h4><i class="fas fa-balance-scale"></i> Conciliación:</h4>';
        html += `<pre>${JSON.stringify(result.reconciliation, null, 2)}</pre>`;
    }

    if (result.database) {
        html += '<h4><i class="fas fa-database"></i> Base de Datos:</h4>';
        html += `<p class="db-message">${result.database.message}</p>`;
    }

    if (result.errors && result.errors.length > 0) {
        html += '<h4><i class="fas fa-exclamation-triangle"></i> Errores:</h4><ul>';
        result.errors.forEach(error => {
            html += `<li class="error-item">${error}</li>`;
        });
        html += '</ul>';
    }

    html += '</div>';
    elements.resultDetails.innerHTML = html;
}

function displayExtractionOnly(data) {
    elements.resultsCard.style.display = 'block';
    let html = '<h4><i class="fas fa-file-invoice"></i> Datos Extraídos:</h4>';
    html += `<pre>${JSON.stringify(data, null, 2)}</pre>`;
    elements.resultDetails.innerHTML = html;
}

function displayProviderResults(result) {
    elements.providerResultsCard.style.display = 'block';

    if (!result.success) {
        elements.providerResults.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i> ${result.message}
            </div>
        `;
        addLogOc('warning', `⚠️ ${result.message}`);
        return;
    }

    addLogOc('success', `✅ Nombre extraído: ${result.nombre_extraido}`);
    addLogOc('success', `✅ CUIT extraído: ${result.cuit_extraido || 'No disponible'}`);
    addLogOc('info', `🔍 Tipo de búsqueda: ${result.match_type}`);
    addLogOc('success', `✅ Encontrados ${result.proveedores.length} proveedor(es)`);

    let html = `
        <div class="search-summary">
            <p><strong>Nombre extraído:</strong> ${result.nombre_extraido}</p>
            <p><strong>CUIT extraído:</strong> ${result.cuit_extraido || 'No disponible'}</p>
            <p><strong>Tipo de match:</strong> <span class="badge badge-info">${result.match_type}</span></p>
        </div>
    `;

    result.proveedores.forEach(prov => {
        const recommended = prov.recomendado ? 'recommended' : '';
        html += `
            <div class="provider-card ${recommended}">
                <div class="provider-header">
                    <div class="provider-info">
                        <h4>${prov.nombre}</h4>
                        <p class="provider-meta">
                            Código: ${prov.codigo} | CUIT: ${prov.cuit || 'N/A'} | 
                            Score: ${prov.score}
                        </p>
                    </div>
                    <div>
                        ${prov.activo ? '<span class="badge badge-success">Activo</span>' : '<span class="badge badge-warning">Inactivo</span>'}
                        ${prov.recomendado ? '<span class="badge badge-success">Recomendado</span>' : ''}
                    </div>
                </div>
                
                ${prov.ordenes_compra.length > 0 ? `
                    <div class="oc-list">
                        <h5>Órdenes de Compra Activas (${prov.ordenes_compra.length}):</h5>
                        ${prov.ordenes_compra.map(oc => `
                            <div class="oc-item ${oc.recomendado ? 'recommended' : ''}">
                                <div class="oc-details">
                                    <div class="oc-number">OC ${oc.nro_orden}</div>
                                    <div class="oc-meta">
                                        Fecha: ${oc.fecha} | Estado: ${oc.estado} | 
                                        Total: $${oc.monto_total.toFixed(2)} | 
                                        Pendiente: $${oc.pendiente_total.toFixed(2)} (${oc.items_pendientes} items)
                                    </div>
                                </div>
                                ${oc.recomendado ? '<span class="badge badge-success">Con Pendientes</span>' : ''}
                            </div>
                        `).join('')}
                    </div>
                ` : '<p class="empty-state">No tiene OCs activas</p>'}
            </div>
        `;

        addLogOc('info', `📋 ${prov.nombre} - ${prov.ordenes_compra.length} OC(s) activa(s)`);
    });

    elements.providerResults.innerHTML = html;
}

// ===== Logs =====
function addLog(type, message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    logEntry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${message}`;
    elements.logsContainer.appendChild(logEntry);
    elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
}

function addLogOc(type, message) {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${type}`;
    logEntry.innerHTML = `<span class="log-timestamp">[${timestamp}]</span> ${message}`;
    elements.logsOcContainer.appendChild(logEntry);
    elements.logsOcContainer.scrollTop = elements.logsOcContainer.scrollHeight;
}

// ===== Historial =====
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/history`);
        if (!response.ok) throw new Error('Error al cargar historial');

        const history = await response.json();
        displayHistory(history);

    } catch (error) {
        console.error('Error:', error);
        elements.historyList.innerHTML = '<p class="empty-state">Error al cargar historial</p>';
    }
}

function displayHistory(history) {
    if (!history || history.length === 0) {
        elements.historyList.innerHTML = '<p class="empty-state">No hay facturas procesadas aún</p>';
        return;
    }

    let html = '';
    history.forEach(item => {
        const date = formatTimestamp(item.timestamp);
        const statusClass = item.success ? 'success' : 'error';
        const statusText = item.success ? '✓ Exitoso' : '✗ Error';

        const preview = item.preview || {};
        const numero = preview.numero_comprobante || 'N/A';
        const tipo = preview.tipo_comprobante || 'Factura';

        html += `
            <div class="history-item" onclick="viewHistoryItem('${item.filename}')">
                <div class="history-item-info">
                    <h4>${tipo} ${numero}</h4>
                    <p>${date}</p>
                </div>
                <div class="history-item-status ${statusClass}">${statusText}</div>
            </div>
        `;
    });

    elements.historyList.innerHTML = html;
}

async function viewHistoryItem(filename) {
    try {
        const response = await fetch(`${API_BASE}/result/${filename}`);
        if (!response.ok) throw new Error('Error al cargar resultado');

        const result = await response.json();
        switchTab('factura');
        displayResults(result);
        elements.resultsCard.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar detalle');
    }
}

// ===== Utilidades =====
function showLoading(text) {
    elements.loadingText.textContent = text;
    elements.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    elements.loadingOverlay.style.display = 'none';
}

function formatTimestamp(timestamp) {
    if (!timestamp || timestamp.length !== 15) return timestamp;

    const year = timestamp.substring(0, 4);
    const month = timestamp.substring(4, 6);
    const day = timestamp.substring(6, 8);
    const hour = timestamp.substring(9, 11);
    const minute = timestamp.substring(11, 13);

    return `${day}/${month}/${year} ${hour}:${minute}`;
}

async function checkServerStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (response.ok) {
            elements.statusDot.classList.add('online');
            elements.statusText.textContent = 'Sistema Online';
        } else {
            throw new Error('Server error');
        }
    } catch (error) {
        elements.statusDot.classList.remove('online');
        elements.statusText.textContent = 'Desconectado';
    }
}

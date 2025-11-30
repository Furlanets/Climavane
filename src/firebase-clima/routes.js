// --- routes.js ---
function navegarParaDetalhes(idSensor) {
    const urlDestino = `detalhes.html?sensor=${idSensor}`;
    
    window.location.href = urlDestino;
}

function obterSensorDaURL() {
    const params = new URLSearchParams(window.location.search);
    return params.get('sensor');
}
// Similaires.js - Logique pour la recherche de biens similaires

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('searchForm');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const surface = parseFloat(document.getElementById('searchSurface').value);
        const nb_pieces = parseFloat(document.getElementById('searchPieces').value);
        const code_commune = document.getElementById('searchCommune').value.trim();

        if (!surface || !nb_pieces || !code_commune) {
            showError('Veuillez remplir tous les champs');
            return;
        }

        await searchSimilar(surface, nb_pieces, code_commune);
    });
});

async function searchSimilar(surface, nb_pieces, code_commune) {
    showLoading();
    hideAll();

    try {
        const response = await fetch('/api/find-similar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                surface: surface,
                nb_pieces: nb_pieces,
                code_commune: code_commune
            })
        });

        const data = await response.json();

        hideLoading();

        if (data.success && data.results.length > 0) {
            displayResults(data.results);
        } else if (data.success && data.results.length === 0) {
            showError('Aucun bien similaire trouvé dans ce secteur');
        } else {
            showError(data.error || 'Erreur lors de la recherche');
        }

    } catch (error) {
        hideLoading();
        showError('Erreur de connexion');
        console.error(error);
    }
}

function displayResults(results) {
    // Tableau
    const tbody = document.querySelector('#tableResults tbody');
    tbody.innerHTML = '';

    results.forEach(bien => {
        const row = `
            <tr>
                <td>${bien.code_commune}</td>
                <td><strong>${formatPrice(bien.prix)}</strong></td>
                <td>${bien.surface.toFixed(1)} m²</td>
                <td>${bien.nb_pieces}</td>
                <td>${formatPrice(bien.prix_m2)}</td>
                <td><span class="px-3 py-1 rounded-full text-xs font-semibold ${getStandingColorTailwind(bien.standing)}">${getStandingLabel(bien.standing)}</span></td>
            </tr>
        `;
        tbody.innerHTML += row;
    });

    // Nombre de résultats
    document.getElementById('nbResults').textContent = results.length;

    // Carte
    displayMiniMap(results);

    // Affichage
    document.getElementById('resultsSection').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('fade-in-up');
}

function displayMiniMap(results) {
    const lats = results.map(r => r.latitude);
    const lons = results.map(r => r.longitude);
    const texts = results.map(r =>
        `${r.code_commune}<br>${formatPrice(r.prix)}<br>${r.surface.toFixed(1)}m² - ${r.nb_pieces}P`
    );

    const trace = {
        type: 'scattermapbox',
        lat: lats,
        lon: lons,
        mode: 'markers',
        marker: {
            size: 12,
            color: 'red'
        },
        text: texts,
        hoverinfo: 'text'
    };

    // Centre de la carte = moyenne des positions
    const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
    const centerLon = lons.reduce((a, b) => a + b, 0) / lons.length;

    const layout = {
        mapbox: {
            style: 'open-street-map',
            center: { lat: centerLat, lon: centerLon },
            zoom: 10
        },
        margin: { t: 0, b: 0, l: 0, r: 0 },
        height: 400
    };

    Plotly.newPlot('miniMap', [trace], layout, { responsive: true });
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorCard').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
}

function hideAll() {
    document.getElementById('errorCard').classList.add('hidden');
    document.getElementById('resultsSection').classList.add('hidden');
    document.getElementById('initialCard').classList.add('hidden');
}

function formatPrice(price) {
    return new Intl.NumberFormat('fr-FR', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

function getStandingLabel(code) {
    const labels = {
        '1_Decote_Travaux': 'Décote',
        '2_Bonne_Affaire': 'Affaire',
        '3_Standard_Marche': 'Standard',
        '4_Premium': 'Premium',
        '5_Prestige_Exception': 'Prestige'
    };
    return labels[code] || 'N/A';
}

function getStandingColorTailwind(code) {
    const colors = {
        '1_Decote_Travaux': 'bg-red-100 text-red-700',
        '2_Bonne_Affaire': 'bg-yellow-100 text-yellow-700',
        '3_Standard_Marche': 'bg-blue-100 text-blue-700',
        '4_Premium': 'bg-green-100 text-green-700',
        '5_Prestige_Exception': 'bg-purple-100 text-purple-700'
    };
    return colors[code] || 'bg-gray-100 text-gray-700';
}

function showLoading() {
    const spinner = document.createElement('div');
    spinner.id = 'loadingSpinner';
    spinner.className = 'spinner-overlay';
    spinner.innerHTML = '<div class="spinner-border text-light" style="width: 3rem; height: 3rem;"></div>';
    document.body.appendChild(spinner);
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) spinner.remove();
}

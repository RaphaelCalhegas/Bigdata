// cartographie.js - Logique pour la carte interactive

const clusterNames = {
    0: "Petits Appartements Province Sud",
    1: "Appartements Premium Paris/IDF",
    2: "Appartements Familiaux IDF Périphérie",
    3: "Appartements Standard Province",
    4: "Grandes Maisons Familiales",
    5: "Studios/T2 Province Dynamique"
};

const clusterColors = ['#ef4444', '#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#eab308'];

document.addEventListener('DOMContentLoaded', function () {
    const btnLoadMap = document.getElementById('btnLoadMap');
    if (btnLoadMap) {
        btnLoadMap.addEventListener('click', async function () {
            await loadMapData();
        });
    }
});

async function loadMapData() {
    showLoading();

    try {
        const response = await fetch('/api/map-data');
        const data     = await response.json();

        hideLoading();

        if (data.error) {
            alert(data.error);
            return;
        }

        const filterMin    = parseFloat(document.getElementById('filterPrixMin').value) || 0;
        const filterMax    = parseFloat(document.getElementById('filterPrixMax').value) || 999999;
        const filteredData = filterData(data, filterMin, filterMax);

        displayMapPlotly(filteredData);
        updateStats(filteredData);

    } catch (error) {
        hideLoading();
        alert('Erreur: ' + error.message);
        console.error(error);
    }
}

function filterData(data, minPrix, maxPrix) {
    const filtered = { latitudes: [], longitudes: [], prix_m2: [], clusters: [], communes: [] };

    for (let i = 0; i < data.prix_m2.length; i++) {
        if (data.prix_m2[i] >= minPrix && data.prix_m2[i] <= maxPrix) {
            filtered.latitudes.push(data.latitudes[i]);
            filtered.longitudes.push(data.longitudes[i]);
            filtered.prix_m2.push(data.prix_m2[i]);
            filtered.clusters.push(data.clusters[i]);
            filtered.communes.push(data.communes[i]);
        }
    }

    return filtered;
}

function displayMapPlotly(data) {
    const customColorscale = [
        [0,   clusterColors[0]],
        [0.2, clusterColors[1]],
        [0.4, clusterColors[2]],
        [0.6, clusterColors[3]],
        [0.8, clusterColors[4]],
        [1,   clusterColors[5]]
    ];

    const trace = {
        type: 'scattermapbox',
        lat:  data.latitudes,
        lon:  data.longitudes,
        mode: 'markers',
        marker: {
            size:       5,
            color:      data.clusters.length > 0 ? data.clusters : data.prix_m2,
            colorscale: data.clusters.length > 0 ? customColorscale : 'Viridis',
            showscale:  true,
            cmin:       0,
            cmax:       5,
            colorbar: {
                title:    data.clusters.length > 0 ? 'Segment' : 'Prix m²',
                thickness: 15,
                len:       0.7,
                tickmode:  data.clusters.length > 0 ? 'array' : 'auto',
                tickvals:  data.clusters.length > 0 ? [0, 1, 2, 3, 4, 5] : undefined,
                ticktext:  data.clusters.length > 0 ? ['Seg. 0', 'Seg. 1', 'Seg. 2', 'Seg. 3', 'Seg. 4', 'Seg. 5'] : undefined
            }
        },
        text: data.communes.map((commune, i) => {
            const clusterName = data.clusters.length > 0 && data.clusters[i] !== undefined
                ? clusterNames[data.clusters[i]]
                : 'N/A';
            return `Commune: ${commune}<br>Prix m²: ${data.prix_m2[i].toLocaleString('fr-FR')} €<br>Segment: ${clusterName}`;
        }),
        hoverinfo: 'text'
    };

    const layout = {
        mapbox: {
            style:  'open-street-map',
            center: { lat: 46.603354, lon: 1.888334 },
            zoom:   5
        },
        margin: { t: 0, b: 0, l: 0, r: 0 },
        height: 600
    };

    Plotly.newPlot('mapContainer', [trace], layout, { responsive: true });

    if (data.clusters.length > 0) {
        updateLegend(data.clusters);
    }
}

function updateLegend(clusters) {
    const uniqueClusters = [...new Set(clusters)].sort();
    let legendHTML = '<div class="space-y-2">';

    uniqueClusters.forEach(cluster => {
        const color = clusterColors[cluster % clusterColors.length];
        const name  = clusterNames[cluster];
        legendHTML += `
            <div class="flex items-center space-x-3 p-2 rounded-lg hover:bg-gray-50 transition-colors">
                <div class="w-4 h-4 rounded-full" style="background-color: ${color};"></div>
                <span class="text-sm font-medium text-gray-700">${name}</span>
            </div>
        `;
    });

    legendHTML += '</div>';
    document.getElementById('legendeContainer').innerHTML = legendHTML;
}

function updateStats(data) {
    document.getElementById('statNbPoints').textContent = data.latitudes.length.toLocaleString('fr-FR');

    const avgPrix = data.prix_m2.reduce((a, b) => a + b, 0) / data.prix_m2.length;
    document.getElementById('statPrixMoyen').textContent =
        new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR' }).format(avgPrix);

    if (data.clusters.length > 0) {
        document.getElementById('statNbClusters').textContent = new Set(data.clusters).size;
    } else {
        document.getElementById('statNbClusters').textContent = 'N/A';
    }
}

function showLoading() {
    const spinner     = document.createElement('div');
    spinner.id        = 'loadingSpinner';
    spinner.className = 'spinner-overlay';
    spinner.innerHTML = '<div class="spinner"></div>';
    document.body.appendChild(spinner);
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) spinner.remove();
}

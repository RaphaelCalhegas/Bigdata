// Analyse Marché.js - Logique pour l'onglet Analyse de Marché

let chartPrixDistribution = null;
let chartStanding = null;

document.addEventListener('DOMContentLoaded', function () {
    const btnAnalyser = document.getElementById('btnAnalyser');
    const selectDept = document.getElementById('selectDepartement');

    btnAnalyser.addEventListener('click', async function () {
        const codeDept = selectDept.value;

        if (!codeDept) {
            alert('Veuillez sélectionner un département');
            return;
        }

        await analyserDepartement(codeDept);
    });
});

async function analyserDepartement(codeDept) {
    showLoading();

    try {
        // Récupération stats département
        const response = await fetch(`/api/analyse-departement/${codeDept}`);
        const stats = await response.json();

        if (stats.error) {
            alert(stats.error);
            hideLoading();
            return;
        }

        // Récupération top communes
        const responseCommunes = await fetch(`/api/top-communes/${codeDept}`);
        const topCommunes = await responseCommunes.json();

        hideLoading();

        // Affichage
        displayKPIs(stats);
        displayCharts(stats);
        displayTopCommunes(topCommunes);

        // Montrer la section
        document.getElementById('kpiSection').classList.remove('hidden');
        document.getElementById('initialMessage').classList.add('hidden');

    } catch (error) {
        hideLoading();
        alert('Erreur lors du chargement des données');
        console.error(error);
    }
}

function displayKPIs(stats) {
    document.getElementById('kpiTransactions').textContent = stats.nb_transactions.toLocaleString('fr-FR');
    document.getElementById('kpiPrixMedian').textContent = formatPrice(stats.prix_m2_median) + '/m²';
    document.getElementById('kpiSurface').textContent = stats.surface_moyenne.toFixed(1) + ' m²';
    document.getElementById('kpiPrixMoyen').textContent = formatPrice(stats.prix_moyen);
}

function displayCharts(stats) {
    // Chart 1 : Distribution des prix (Box Plot simplifié)
    const ctxPrix = document.getElementById('chartPrixDistribution');

    if (chartPrixDistribution) {
        chartPrixDistribution.destroy();
    }

    chartPrixDistribution = new Chart(ctxPrix, {
        type: 'bar',
        data: {
            labels: ['Q1 (25%)', 'Médiane', 'Moyenne', 'Q3 (75%)'],
            datasets: [{
                label: 'Prix au m² (€)',
                data: [
                    stats.prix_m2_q25,
                    stats.prix_m2_median,
                    stats.prix_m2_mean,
                    stats.prix_m2_q75
                ],
                backgroundColor: [
                    'rgba(54, 162, 235, 0.6)',
                    'rgba(75, 192, 192, 0.6)',
                    'rgba(255, 206, 86, 0.6)',
                    'rgba(153, 102, 255, 0.6)'
                ],
                borderColor: [
                    'rgba(54, 162, 235, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(153, 102, 255, 1)'
                ],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            return value.toLocaleString('fr-FR') + ' €';
                        }
                    }
                }
            }
        }
    });

    // Chart 2 : Répartition Standing
    const ctxStanding = document.getElementById('chartStanding');

    if (chartStanding) {
        chartStanding.destroy();
    }

    const standingData = stats.repartition_standing || {};
    const labels = Object.keys(standingData).map(k => getStandingLabel(k));
    const values = Object.values(standingData);

    chartStanding = new Chart(ctxStanding, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    'rgba(220, 53, 69, 0.7)',
                    'rgba(255, 193, 7, 0.7)',
                    'rgba(13, 202, 240, 0.7)',
                    'rgba(25, 135, 84, 0.7)',
                    'rgba(13, 110, 253, 0.7)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

function displayTopCommunes(communes) {
    const tbody = document.querySelector('#tableTopCommunes tbody');
    tbody.innerHTML = '';

    if (communes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Aucune donnée</td></tr>';
        return;
    }

    communes.forEach((commune, index) => {
        const row = `
            <tr>
                <td><strong>#${index + 1}</strong></td>
                <td>${commune.code_commune}</td>
                <td>${commune.nb_transactions.toLocaleString('fr-FR')}</td>
                <td>${formatPrice(commune.prix_m2_median)}</td>
                <td>${commune.surface_moyenne.toFixed(1)} m²</td>
            </tr>
        `;
        tbody.innerHTML += row;
    });
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
        '2_Bonne_Affaire': 'Bonne Affaire',
        '3_Standard_Marche': 'Standard',
        '4_Premium': 'Premium',
        '5_Prestige_Exception': 'Prestige'
    };
    return labels[code] || code;
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

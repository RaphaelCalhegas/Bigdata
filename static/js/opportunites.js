// opportunites.js - Détection d'opportunités d'investissement via Isolation Forest

document.addEventListener('DOMContentLoaded', function () {
    const btnAnalyze = document.getElementById('btnAnalyze');
    const contamination = document.getElementById('contamination');
    const maxRatio = document.getElementById('maxRatio');
    const zoneFilter = document.getElementById('zoneFilter');

    btnAnalyze.addEventListener('click', detectOpportunities);

    async function detectOpportunities() {
        try {
            showLoading();

            const response = await fetch('/api/opportunities', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    contamination: parseFloat(contamination.value),
                    max_ratio: parseFloat(maxRatio.value),
                    zone_filter: zoneFilter.value
                })
            });

            const data = await response.json();

            if (data.success) {
                displayResults(data);
            } else {
                showError(data.error || 'Erreur lors de la détection');
            }
        } catch (error) {
            showError('Erreur réseau: ' + error.message);
        }
    }

    function displayResults(data) {
        hideMessages();

        // KPIs
        document.getElementById('kpiOpportunities').textContent = data.nb_opportunities.toLocaleString();
        document.getElementById('kpiDecote').textContent = `-${data.median_decote}%`;
        document.getElementById('kpiPrixMedian').textContent = `${Math.round(data.median_prix_m2).toLocaleString()} €`;
        document.getElementById('kpiSurface').textContent = `${Math.round(data.median_surface)} m²`;

        document.getElementById('kpiSection').classList.remove('hidden');

        // Tableau
        const tbody = document.querySelector('#tableOpportunities tbody');
        tbody.innerHTML = '';

        data.opportunities.forEach((opp, idx) => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>
                    <div class="flex items-center space-x-2">
                        <span class="text-2xl">${idx < 3 ? '🥇🥈🥉'[idx] : '💎'}</span>
                        <span class="font-bold text-lg">${Math.round(opp.investment_score)}</span>
                    </div>
                </td>
                <td class="font-bold text-green-600">-${opp.decote_pct}%</td>
                <td>${Math.round(opp.valeur_fonciere).toLocaleString()} €</td>
                <td>${Math.round(opp.prix_m2).toLocaleString()} €</td>
                <td class="text-gray-600">${Math.round(opp.marche_prix_m2_median).toLocaleString()} €</td>
                <td>${Math.round(opp.surface_reelle_bati)} m²</td>
                <td>${opp.nombre_pieces_principales}</td>
                <td><span class="px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800">${formatZone(opp.categorie_geo)}</span></td>
                <td><span class="px-3 py-1 rounded-full text-sm bg-purple-100 text-purple-800">${formatStanding(opp.standing_relative)}</span></td>
            `;
        });

        // Graphiques
        renderCharts(data);

        document.getElementById('resultsSection').classList.remove('hidden');
    }

    function renderCharts(data) {
        // Chart 1: Distribution des Scores
        const ctxScores = document.getElementById('chartScores').getContext('2d');
        if (window.chartScores && typeof window.chartScores.destroy === 'function') {
            window.chartScores.destroy();
        }

        window.chartScores = new Chart(ctxScores, {
            type: 'bar',
            data: {
                labels: data.score_bins.labels,
                datasets: [{
                    label: 'Nombre d\'opportunités',
                    data: data.score_bins.counts,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title: {
                        display: true,
                        text: 'Plus le score est élevé, meilleure est l\'opportunité'
                    }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });

        // Chart 2: Répartition par Zone
        const ctxZones = document.getElementById('chartZones').getContext('2d');
        if (window.chartZones && typeof window.chartZones.destroy === 'function') {
            window.chartZones.destroy();
        }

        window.chartZones = new Chart(ctxZones, {
            type: 'doughnut',
            data: {
                labels: data.zone_distribution.labels,
                datasets: [{
                    data: data.zone_distribution.counts,
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)',
                        'rgba(147, 51, 234, 0.8)',
                        'rgba(236, 72, 153, 0.8)',
                        'rgba(34, 197, 94, 0.8)'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    function formatZone(zone) {
        const map = {
            '1_Metropole_Top15': 'Métropole',
            '2_Ile_de_France': 'IDF',
            '3_Zone_Touristique': 'Tourisme',
            '4_Province_Standard': 'Province'
        };
        return map[zone] || zone;
    }

    function formatStanding(standing) {
        const map = {
            '1_Decote_Travaux': 'Travaux',
            '2_Bonne_Affaire': 'Affaire',
            '3_Standard_Marche': 'Standard',
            '4_Premium': 'Premium',
            '5_Prestige_Exception': 'Prestige'
        };
        return map[standing] || standing;
    }

    function showLoading() {
        btnAnalyze.disabled = true;
        btnAnalyze.innerHTML = '<i class="fas fa-spinner fa-spin text-xl"></i><span>Analyse en cours...</span>';
        hideMessages();
    }

    function hideMessages() {
        document.getElementById('initialMessage').classList.add('hidden');
        document.getElementById('errorAlert').classList.add('hidden');
        document.getElementById('kpiSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
    }

    function showError(message) {
        btnAnalyze.disabled = false;
        btnAnalyze.innerHTML = '<i class="fas fa-search-dollar text-xl"></i><span>Détecter Opportunités</span>';

        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorAlert').classList.remove('hidden');
    }
});

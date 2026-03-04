// Estimation.js - Logique pour l'onglet Estimation

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('estimationForm');
    const resultsCard = document.getElementById('resultsCard');
    const instructionsCard = document.getElementById('instructionsCard');
    const errorAlert = document.getElementById('errorAlert');

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        // Récupération des valeurs
        const surface = parseFloat(document.getElementById('surface').value);
        const nb_pieces = parseFloat(document.getElementById('nb_pieces').value);
        const code_commune = document.getElementById('code_commune').value.trim();

        // Validation
        if (!surface || !nb_pieces || !code_commune) {
            showError('Veuillez remplir tous les champs');
            return;
        }

        // Masquer les éléments
        hideAll();
        showLoading();

        try {
            // Appel API
            const response = await fetch('/api/estimate', {
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

            if (data.success) {
                displayResults(data);
            } else {
                showError(data.error || 'Erreur lors de l\'estimation');
            }

        } catch (error) {
            hideLoading();
            showError('Erreur de connexion au serveur');
            console.error(error);
        }
    });

    function displayResults(data) {
        // Prix principal
        document.getElementById('prixEstime').textContent = formatPrice(data.prix_estime);
        document.getElementById('prixM2').textContent = formatPrice(data.prix_m2);

        // Fourchette
        document.getElementById('prixMin').textContent = formatPrice(data.prix_min);
        document.getElementById('prixMax').textContent = formatPrice(data.prix_max);

        // Standing
        const standingAlert = document.getElementById('standingAlert');
        const standing = data.standing;
        standingAlert.className = `alert alert-${standing.color}`;
        document.getElementById('standingContent').innerHTML = `
            <p class="text-sm">
                <strong class="text-base">${standing.icon} ${standing.label}</strong><br>
                <span class="text-gray-600">Rapport au marché local : ${standing.ratio}x</span>
            </p>
        `;

        // Stats commune
        const stats = data.commune_stats;
        document.getElementById('communeStats').innerHTML = `
            <li><strong>Prix m² médian :</strong> ${formatPrice(stats.prix_m2_median)}</li>
            <li><strong>Prix m² moyen :</strong> ${formatPrice(stats.prix_m2_mean)}</li>
            <li><strong>Nb transactions :</strong> ${stats.nb_transactions}</li>
            <li><strong>Surface moyenne :</strong> ${stats.surface_moyenne.toFixed(1)} m²</li>
            <li><strong>Zone :</strong> ${getZoneLabel(stats.categorie_geo)}</li>
        `;

        // Cluster info (si disponible)
        if (data.cluster_info) {
            const clusterDiv = document.getElementById('clusterInfo');
            clusterDiv.classList.remove('hidden');
            document.getElementById('clusterText').innerHTML = `
                Votre bien appartient au <strong>Cluster ${data.cluster_info.id}</strong>
                (${data.cluster_info.nb_biens} biens similaires, prix moyen : ${formatPrice(data.cluster_info.prix_m2_moyen)}/m²)
            `;
        }

        // Affichage
        instructionsCard.classList.add('hidden');
        resultsCard.classList.remove('hidden');
        resultsCard.classList.add('fade-in-up');
    }

    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorAlert.classList.remove('hidden');
        instructionsCard.classList.add('hidden');
        resultsCard.classList.add('hidden');
    }

    function hideAll() {
        errorAlert.classList.add('hidden');
        resultsCard.classList.add('hidden');
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

    function formatPrice(price) {
        return new Intl.NumberFormat('fr-FR', {
            style: 'currency',
            currency: 'EUR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(price);
    }

    function getZoneLabel(code) {
        const labels = {
            '1_Metropole_Top15': 'Métropole Top 15',
            '2_Ile_de_France': 'Île-de-France',
            '3_Zone_Touristique': 'Zone Touristique',
            '4_Province_Standard': 'Province Standard'
        };
        return labels[code] || code;
    }
});

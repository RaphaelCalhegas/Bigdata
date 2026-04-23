// estimation.js - Logique pour l'onglet Estimation

document.addEventListener('DOMContentLoaded', function () {
    const form             = document.getElementById('estimationForm');
    const resultsCard      = document.getElementById('resultsCard');
    const instructionsCard = document.getElementById('instructionsCard');
    const errorAlert       = document.getElementById('errorAlert');
    const codePostalInput  = document.getElementById('code_postal');
    const codeInseeInput   = document.getElementById('code_commune');
    const suggestionsDiv   = document.getElementById('communeSuggestions');
    const communeSelected  = document.getElementById('communeSelected');

    // --- Recherche commune par code postal ou nom ---
    let searchTimeout = null;

    codePostalInput.addEventListener('input', function () {
        const val = this.value.trim();
        codeInseeInput.value      = '';
        communeSelected.innerHTML = '';

        if (val.length < 2) {
            suggestionsDiv.classList.add('hidden');
            return;
        }

        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => searchCommunes(val), 300);
    });

    async function searchCommunes(query) {
        try {
            const isPostal = /^\d+$/.test(query);

            // Données des grandes villes découpées en arrondissements
            const grandesVilles = {
                'paris': {
                    noms:  ['Paris 1er','Paris 2ème','Paris 3ème','Paris 4ème','Paris 5ème','Paris 6ème','Paris 7ème','Paris 8ème','Paris 9ème','Paris 10ème','Paris 11ème','Paris 12ème','Paris 13ème','Paris 14ème','Paris 15ème','Paris 16ème','Paris 17ème','Paris 18ème','Paris 19ème','Paris 20ème'],
                    codes: ['75101','75102','75103','75104','75105','75106','75107','75108','75109','75110','75111','75112','75113','75114','75115','75116','75117','75118','75119','75120'],
                    cps:   ['75001','75002','75003','75004','75005','75006','75007','75008','75009','75010','75011','75012','75013','75014','75015','75016','75017','75018','75019','75020']
                },
                'lyon': {
                    noms:  ['Lyon 1er','Lyon 2ème','Lyon 3ème','Lyon 4ème','Lyon 5ème','Lyon 6ème','Lyon 7ème','Lyon 8ème','Lyon 9ème'],
                    codes: ['69381','69382','69383','69384','69385','69386','69387','69388','69389'],
                    cps:   ['69001','69002','69003','69004','69005','69006','69007','69008','69009']
                },
                'marseille': {
                    noms:  ['Marseille 1er','Marseille 2ème','Marseille 3ème','Marseille 4ème','Marseille 5ème','Marseille 6ème','Marseille 7ème','Marseille 8ème','Marseille 9ème','Marseille 10ème','Marseille 11ème','Marseille 12ème','Marseille 13ème','Marseille 14ème','Marseille 15ème','Marseille 16ème'],
                    codes: ['13201','13202','13203','13204','13205','13206','13207','13208','13209','13210','13211','13212','13213','13214','13215','13216'],
                    cps:   ['13001','13002','13003','13004','13005','13006','13007','13008','13009','13010','13011','13012','13013','13014','13015','13016']
                }
            };

            const queryLower = query.toLowerCase().trim();

            // Recherche par nom de grande ville
            for (const [ville, data] of Object.entries(grandesVilles)) {
                if (queryLower === ville || queryLower.startsWith(ville + ' ')) {
                    const suggestions = data.noms.map((nom, i) => ({
                        nom:          nom,
                        code:         data.codes[i],
                        codesPostaux: [data.cps[i]]
                    }));
                    displaySuggestions(suggestions);
                    return;
                }
            }

            // Recherche par code postal Paris (75001-75020)
            if (isPostal && query.startsWith('75') && query.length <= 5) {
                const data        = grandesVilles['paris'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom:          nom,
                    code:         data.codes[i],
                    codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) {
                    displaySuggestions(suggestions);
                    return;
                }
            }

            // Recherche par code postal Lyon (69001-69009)
            if (isPostal && query.startsWith('69') && query.length <= 5) {
                const data        = grandesVilles['lyon'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom:          nom,
                    code:         data.codes[i],
                    codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) {
                    displaySuggestions(suggestions);
                    return;
                }
            }

            // Recherche par code postal Marseille (13001-13016)
            if (isPostal && query.startsWith('13') && query.length <= 5) {
                const data        = grandesVilles['marseille'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom:          nom,
                    code:         data.codes[i],
                    codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) {
                    displaySuggestions(suggestions);
                    return;
                }
            }

            // Recherche normale via API geo pour toutes les autres communes
            const paramKey = isPostal ? 'codePostal' : 'nom';
            const response = await fetch(
                `https://geo.api.gouv.fr/communes?${paramKey}=${query}&fields=nom,code,codesPostaux&limit=8`
            );
            const communes = await response.json();

            // Exclure Paris/Lyon/Marseille des résultats API (codes globaux inutilisables)
            const codesAExclure   = ['75056', '69123', '13055'];
            const communesFiltrees = communes.filter(c => !codesAExclure.includes(c.code));

            displaySuggestions(communesFiltrees);

        } catch (e) {
            console.error('Erreur recherche commune :', e);
        }
    }

    function displaySuggestions(communes) {
        if (!communes.length) {
            suggestionsDiv.classList.add('hidden');
            return;
        }

        suggestionsDiv.innerHTML = '';
        communes.forEach(commune => {
            const cp  = commune.codesPostaux?.[0] || '';
            const div = document.createElement('div');
            div.className = 'px-4 py-3 hover:bg-emerald-50 cursor-pointer border-b border-slate-100 last:border-0 transition-colors';
            div.innerHTML = `
                <span class="font-semibold text-slate-800">${commune.nom}</span>
                <span class="text-sm text-slate-400 ml-2">CP : ${cp} &nbsp;·&nbsp; INSEE : ${commune.code}</span>
            `;
            div.addEventListener('click', () => selectCommune(commune));
            suggestionsDiv.appendChild(div);
        });

        suggestionsDiv.classList.remove('hidden');
    }

    function selectCommune(commune) {
        const cp              = commune.codesPostaux?.[0] || '';
        codePostalInput.value = cp + ' — ' + commune.nom;
        codeInseeInput.value  = commune.code;
        communeSelected.innerHTML = `
            <i class="fas fa-check-circle text-emerald-500 mr-1"></i>
            <strong>${commune.nom}</strong> &nbsp;—&nbsp; CP : ${cp} &nbsp;·&nbsp; INSEE : ${commune.code}
        `;
        suggestionsDiv.classList.add('hidden');
    }

    // Fermer suggestions si clic extérieur
    document.addEventListener('click', function (e) {
        if (!suggestionsDiv.contains(e.target) && e.target !== codePostalInput) {
            suggestionsDiv.classList.add('hidden');
        }
    });

    // --- Soumission du formulaire ---
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const surface      = parseFloat(document.getElementById('surface').value);
        const nb_pieces    = parseFloat(document.getElementById('nb_pieces').value);
        const code_commune = codeInseeInput.value.trim();

        if (!surface || !nb_pieces) {
            showError('Veuillez remplir tous les champs');
            return;
        }

        if (!code_commune) {
            showError('Veuillez sélectionner une commune dans la liste déroulante');
            return;
        }

        hideAll();
        showLoading();

        try {
            const response = await fetch('/api/estimate', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ surface, nb_pieces, code_commune })
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

    // --- Affichage des résultats ---
    function displayResults(data) {
        document.getElementById('prixEstime').textContent = formatPrice(data.prix_estime);
        document.getElementById('prixM2').textContent     = formatPrice(data.prix_m2);
        document.getElementById('prixMin').textContent    = formatPrice(data.prix_min);
        document.getElementById('prixMax').textContent    = formatPrice(data.prix_max);

        const standingAlert = document.getElementById('standingAlert');
        const standing      = data.standing;
        standingAlert.className = `alert alert-${standing.color}`;
        document.getElementById('standingContent').innerHTML = `
            <p class="text-sm">
                <strong class="text-base">${standing.label}</strong><br>
                <span class="text-gray-600">Rapport au marché local : ${standing.ratio}x</span>
            </p>
        `;

        const stats = data.commune_stats;
        document.getElementById('communeStats').innerHTML = `
            <li><strong>Prix m² médian :</strong> ${formatPrice(stats.prix_m2_median)}</li>
            <li><strong>Prix m² moyen :</strong> ${formatPrice(stats.prix_m2_mean)}</li>
            <li><strong>Nombre de transactions :</strong> ${stats.nb_transactions}</li>
            <li><strong>Surface moyenne :</strong> ${stats.surface_moyenne.toFixed(1)} m²</li>
            <li><strong>Zone :</strong> ${getZoneLabel(stats.categorie_geo)}</li>
        `;

        if (data.cluster_info) {
            const clusterDiv = document.getElementById('clusterInfo');
            if (clusterDiv) {
                clusterDiv.classList.remove('hidden');
                document.getElementById('clusterText').innerHTML = `
                    Votre bien appartient au <strong>Cluster ${data.cluster_info.id}</strong>
                    (${data.cluster_info.nb_biens} biens similaires,
                    prix moyen : ${formatPrice(data.cluster_info.prix_m2_moyen)}/m²)
                `;
            }
        }

        instructionsCard.classList.add('hidden');
        resultsCard.classList.remove('hidden');
        resultsCard.classList.add('fade-in');
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

    function formatPrice(price) {
        return new Intl.NumberFormat('fr-FR', {
            style:                 'currency',
            currency:              'EUR',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(price);
    }

    function getZoneLabel(code) {
        const labels = {
            '1_Metropole_Top15':   'Métropole Top 15',
            '2_Ile_de_France':     'Île-de-France',
            '3_Zone_Touristique':  'Zone Touristique',
            '4_Province_Standard': 'Province Standard'
        };
        return labels[code] || code;
    }
});
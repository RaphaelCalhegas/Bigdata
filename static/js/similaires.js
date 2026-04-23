// similaires.js - Logique pour la recherche de biens similaires

let allResults        = [];
let allResultsInfo    = [];
let currentPageSim    = 1;
const itemsPerPageSim = 10;

document.addEventListener('DOMContentLoaded', function () {
    const form            = document.getElementById('searchForm');
    const codePostalInput = document.getElementById('searchCodePostal');
    const codeInseeInput  = document.getElementById('searchCommune');
    const suggestionsDiv  = document.getElementById('searchSuggestions');
    const communeSelected = document.getElementById('searchCommuneSelected');
    const tooltip         = document.getElementById('tooltip-global-sim');

    // Gestion globale du tooltip
    document.addEventListener('mousemove', function (e) {
        if (tooltip && tooltip.style.display === 'block') {
            tooltip.style.left = (e.clientX + 14) + 'px';
            tooltip.style.top  = (e.clientY - 10) + 'px';
        }
    });

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

            for (const [ville, data] of Object.entries(grandesVilles)) {
                if (queryLower === ville || queryLower.startsWith(ville + ' ')) {
                    displaySuggestions(data.noms.map((nom, i) => ({
                        nom: nom, code: data.codes[i], codesPostaux: [data.cps[i]]
                    })));
                    return;
                }
            }

            if (isPostal && query.startsWith('75') && query.length <= 5) {
                const data        = grandesVilles['paris'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom: nom, code: data.codes[i], codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) { displaySuggestions(suggestions); return; }
            }

            if (isPostal && query.startsWith('69') && query.length <= 5) {
                const data        = grandesVilles['lyon'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom: nom, code: data.codes[i], codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) { displaySuggestions(suggestions); return; }
            }

            if (isPostal && query.startsWith('13') && query.length <= 5) {
                const data        = grandesVilles['marseille'];
                const suggestions = data.noms.map((nom, i) => ({
                    nom: nom, code: data.codes[i], codesPostaux: [data.cps[i]]
                })).filter(s => s.codesPostaux[0].startsWith(query));
                if (suggestions.length) { displaySuggestions(suggestions); return; }
            }

            const paramKey         = isPostal ? 'codePostal' : 'nom';
            const response         = await fetch(
                `https://geo.api.gouv.fr/communes?${paramKey}=${query}&fields=nom,code,codesPostaux&limit=8`
            );
            const communes         = await response.json();
            const codesAExclure    = ['75056', '69123', '13055'];
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
        const cp                  = commune.codesPostaux?.[0] || '';
        codePostalInput.value     = cp + ' — ' + commune.nom;
        codeInseeInput.value      = commune.code;
        communeSelected.innerHTML = `
            <i class="fas fa-check-circle text-emerald-500 mr-1"></i>
            <strong>${commune.nom}</strong> &nbsp;—&nbsp; CP : ${cp} &nbsp;·&nbsp; INSEE : ${commune.code}
        `;
        suggestionsDiv.classList.add('hidden');
    }

    document.addEventListener('click', function (e) {
        if (!suggestionsDiv.contains(e.target) && e.target !== codePostalInput) {
            suggestionsDiv.classList.add('hidden');
        }
    });

    // --- Soumission du formulaire ---
    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const surface      = parseFloat(document.getElementById('searchSurface').value);
        const nb_pieces    = parseFloat(document.getElementById('searchPieces').value);
        const code_commune = codeInseeInput.value.trim();

        if (!surface || !nb_pieces) {
            showError('Veuillez remplir tous les champs');
            return;
        }

        if (!code_commune) {
            showError('Veuillez sélectionner une commune dans la liste déroulante');
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
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ surface, nb_pieces, code_commune })
        });

        const data = await response.json();
        hideLoading();

        if (data.success && data.results.length > 0) {
            await displayResults(data.results);
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

async function getCommuneInfo(codeInsee) {
    try {
        const response = await fetch(`https://geo.api.gouv.fr/communes/${codeInsee}?fields=nom,codesPostaux`);
        const data     = await response.json();
        return {
            nom:        data.nom || codeInsee,
            codePostal: data.codesPostaux?.[0] || '-'
        };
    } catch {
        return { nom: codeInsee, codePostal: '-' };
    }
}

async function displayResults(results) {
    const tbody = document.querySelector('#tableResults tbody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-gray-500">Chargement des communes...</td></tr>';

    allResultsInfo = await Promise.all(results.map(r => getCommuneInfo(r.code_commune)));
    allResults     = results;
    currentPageSim = 1;

    renderResultsPage(currentPageSim);
    renderResultsPagination();

    document.getElementById('paginationResults').classList.remove('hidden');
    document.getElementById('nbResults').textContent = results.length;

    displayMiniMap(results);

    document.getElementById('resultsSection').classList.remove('hidden');
    document.getElementById('resultsSection').classList.add('fade-in');
}

function attachTooltipsSim() {
    const tooltip = document.getElementById('tooltip-global-sim');
    if (!tooltip) return;

    document.querySelectorAll('[data-tooltip-sim]').forEach(el => {
        el.addEventListener('mouseenter', function () {
            tooltip.innerHTML     = this.getAttribute('data-tooltip-sim');
            tooltip.style.display = 'block';
        });
        el.addEventListener('mouseleave', function () {
            tooltip.style.display = 'none';
        });
    });
}

function renderResultsPage(page) {
    const tbody = document.querySelector('#tableResults tbody');
    const start = (page - 1) * itemsPerPageSim;
    const end   = start + itemsPerPageSim;
    const data  = allResults.slice(start, end);

    tbody.innerHTML = '';
    data.forEach((bien, i) => {
        const info = allResultsInfo[start + i];
        tbody.innerHTML += `
            <tr>
                <td>
                    <div class="cursor-help"
                        data-tooltip-sim="<strong class='text-emerald-400'>Commune</strong><br><br>
                        Nom de la commune issu de l'API officielle geo.gouv.fr.<br><br>
                        Le code postal sous le nom permet de localiser précisément
                        l'arrondissement ou la commune dans le département recherché.">
                        <div class="font-semibold text-slate-800">${info.nom}</div>
                        <div class="text-xs text-slate-400">${info.codePostal}</div>
                    </div>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip-sim="<strong class='text-emerald-400'>Prix total du bien</strong><br><br>
                        Prix de vente total déclaré lors de la transaction, issu des données
                        officielles DVF 2025 publiées par la Direction Générale des Finances Publiques.<br><br>
                        Ce prix est celui de la transaction réelle — pas une estimation.">
                        <strong>${formatPrice(bien.prix)}</strong>
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip-sim="<strong class='text-emerald-400'>Surface réelle bâtie</strong><br><br>
                        Surface habitable déclarée dans les données DVF 2025.<br><br>
                        Correspond à la surface habitable hors caves, garages, terrasses et annexes.<br><br>
                        Filtre appliqué : ±30% de la surface que vous avez saisie.">
                        ${bien.surface.toFixed(1)} m²
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip-sim="<strong class='text-emerald-400'>Nombre de pièces principales</strong><br><br>
                        T1 = 1 pièce &nbsp; T2 = 2 pièces &nbsp; T3 = 3 pièces, etc.<br><br>
                        Ne comprend pas la cuisine, la salle de bain et les WC.<br><br>
                        Filtre appliqué : ±1 pièce par rapport à votre critère.">
                        ${bien.nb_pieces}
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip-sim="<strong class='text-emerald-400'>Prix au m² du bien</strong><br><br>
                        Prix au m² calculé en divisant le prix total par la surface réelle bâtie.<br><br>
                        Permet de comparer objectivement des biens de surfaces différentes.<br><br>
                        Utile pour évaluer si un bien est cher ou abordable dans sa zone.">
                        ${formatPrice(bien.prix_m2)}
                    </span>
                </td>
                <td>
                    <span class="px-3 py-1 rounded-full text-xs font-semibold cursor-help ${getStandingColor(bien.standing)}"
                        data-tooltip-sim="<strong class='text-emerald-400'>Standing relatif</strong><br><br>
                        Positionnement du prix de ce bien par rapport aux autres ventes de la même commune.
                        Indicateur purement mathématique :<br><br>
                        <span class='text-red-400'>&bull; Décote</span> : prix &lt; 70% du marché — bien probablement
                        dégradé ou vendu en urgence.<br>
                        <span class='text-amber-400'>&bull; Affaire</span> : prix entre 70-90% du marché —
                        bien sous-évalué, opportunité à étudier.<br>
                        <span class='text-blue-400'>&bull; Standard</span> : prix dans la moyenne du marché local.<br>
                        <span class='text-emerald-400'>&bull; Premium</span> : prix au-dessus du marché (115-140%) —
                        bien vendu plus cher que la médiane.<br>
                        <span class='text-purple-400'>&bull; Prestige</span> : prix très au-dessus du marché (&gt;140%) —
                        transaction atypique.">
                        ${getStandingLabel(bien.standing)}
                    </span>
                </td>
            </tr>
        `;
    });

    attachTooltipsSim();

    const total = allResults.length;
    document.getElementById('paginationResultsInfo').textContent =
        `Affichage ${start + 1}-${Math.min(end, total)} sur ${total} biens`;

    document.getElementById('btnPrevResults').disabled = page === 1;
    document.getElementById('btnNextResults').disabled = page === Math.ceil(total / itemsPerPageSim);
}

function renderResultsPagination() {
    const totalPages = Math.ceil(allResults.length / itemsPerPageSim);
    const container  = document.getElementById('paginationResultsPages');
    container.innerHTML = '';

    for (let i = 1; i <= totalPages; i++) {
        const btn       = document.createElement('button');
        btn.textContent = i;
        btn.className   = `w-9 h-9 text-sm font-semibold rounded-xl transition-all duration-200 ${
            i === currentPageSim
                ? 'bg-emerald-600 text-white shadow'
                : 'text-emerald-700 border-2 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50'
        }`;
        btn.addEventListener('click', () => {
            currentPageSim = i;
            renderResultsPage(currentPageSim);
            renderResultsPagination();
        });
        container.appendChild(btn);
    }

    document.getElementById('btnPrevResults').onclick = () => {
        if (currentPageSim > 1) {
            currentPageSim--;
            renderResultsPage(currentPageSim);
            renderResultsPagination();
        }
    };

    document.getElementById('btnNextResults').onclick = () => {
        if (currentPageSim < totalPages) {
            currentPageSim++;
            renderResultsPage(currentPageSim);
            renderResultsPagination();
        }
    };
}

function displayMiniMap(results) {
    const lats  = results.map(r => r.latitude).filter(v => v && !isNaN(v));
    const lons  = results.map(r => r.longitude).filter(v => v && !isNaN(v));
    const texts = results.map(r =>
        `${r.code_commune}<br>${formatPrice(r.prix)}<br>${r.surface.toFixed(1)}m² - ${r.nb_pieces}P`
    );

    if (!lats.length || !lons.length) return;

    const centerLat = lats.reduce((a, b) => a + b, 0) / lats.length;
    const centerLon = lons.reduce((a, b) => a + b, 0) / lons.length;

    const latRange = Math.max(...lats) - Math.min(...lats);
    const lonRange = Math.max(...lons) - Math.min(...lons);
    const maxRange = Math.max(latRange, lonRange);

    let zoom = 12;
    if (maxRange > 1.0)       zoom = 7;
    else if (maxRange > 0.5)  zoom = 8;
    else if (maxRange > 0.2)  zoom = 10;
    else if (maxRange > 0.05) zoom = 11;
    else                      zoom = 13;

    const trace = {
        type:      'scattermapbox',
        lat:       lats,
        lon:       lons,
        mode:      'markers',
        marker:    { size: 12, color: '#10b981' },
        text:      texts,
        hoverinfo: 'text'
    };

    const layout = {
        mapbox: {
            style:  'open-street-map',
            center: { lat: centerLat, lon: centerLon },
            zoom:   zoom
        },
        margin: { t: 0, b: 0, l: 0, r: 0 },
        height: 450
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
        style:                 'currency',
        currency:              'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(price);
}

function getStandingLabel(code) {
    const labels = {
        '1_Decote_Travaux':     'Décote',
        '2_Bonne_Affaire':      'Affaire',
        '3_Standard_Marche':    'Standard',
        '4_Premium':            'Premium',
        '5_Prestige_Exception': 'Prestige'
    };
    return labels[code] || 'N/A';
}

function getStandingColor(code) {
    const colors = {
        '1_Decote_Travaux':     'bg-red-100 text-red-700',
        '2_Bonne_Affaire':      'bg-yellow-100 text-yellow-700',
        '3_Standard_Marche':    'bg-blue-100 text-blue-700',
        '4_Premium':            'bg-green-100 text-green-700',
        '5_Prestige_Exception': 'bg-purple-100 text-purple-700'
    };
    return colors[code] || 'bg-gray-100 text-gray-700';
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
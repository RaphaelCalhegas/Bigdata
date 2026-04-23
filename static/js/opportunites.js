// opportunites.js - Détection d'opportunités d'investissement via Isolation Forest

let allOpportunities     = [];
let _backupOpportunities = [];
let currentPageOpp       = 1;
const itemsPerPageOpp    = 10;

// -----------------------------------------------------------------------
// CACHE COMMUNES
// -----------------------------------------------------------------------

const communeCache = {
    '75101': 'Paris 1er',    '75102': 'Paris 2ème',   '75103': 'Paris 3ème',
    '75104': 'Paris 4ème',   '75105': 'Paris 5ème',   '75106': 'Paris 6ème',
    '75107': 'Paris 7ème',   '75108': 'Paris 8ème',   '75109': 'Paris 9ème',
    '75110': 'Paris 10ème',  '75111': 'Paris 11ème',  '75112': 'Paris 12ème',
    '75113': 'Paris 13ème',  '75114': 'Paris 14ème',  '75115': 'Paris 15ème',
    '75116': 'Paris 16ème',  '75117': 'Paris 17ème',  '75118': 'Paris 18ème',
    '75119': 'Paris 19ème',  '75120': 'Paris 20ème',
    '69381': 'Lyon 1er',     '69382': 'Lyon 2ème',    '69383': 'Lyon 3ème',
    '69384': 'Lyon 4ème',    '69385': 'Lyon 5ème',    '69386': 'Lyon 6ème',
    '69387': 'Lyon 7ème',    '69388': 'Lyon 8ème',    '69389': 'Lyon 9ème',
    '13201': 'Marseille 1er',  '13202': 'Marseille 2ème',  '13203': 'Marseille 3ème',
    '13204': 'Marseille 4ème', '13205': 'Marseille 5ème',  '13206': 'Marseille 6ème',
    '13207': 'Marseille 7ème', '13208': 'Marseille 8ème',  '13209': 'Marseille 9ème',
    '13210': 'Marseille 10ème','13211': 'Marseille 11ème', '13212': 'Marseille 12ème',
    '13213': 'Marseille 13ème','13214': 'Marseille 14ème', '13215': 'Marseille 15ème',
    '13216': 'Marseille 16ème'
};

async function fetchCommuneLabel(codeCommune) {
    if (communeCache[codeCommune]) return communeCache[codeCommune];
    try {
        const res  = await fetch(`https://geo.api.gouv.fr/communes/${codeCommune}?fields=nom`);
        const data = await res.json();
        const nom  = data.nom || codeCommune;
        communeCache[codeCommune] = nom;
        return nom;
    } catch {
        communeCache[codeCommune] = codeCommune;
        return codeCommune;
    }
}

// -----------------------------------------------------------------------
// ZONES GÉOGRAPHIQUES PAR DÉPARTEMENT (filtre côté JS)
// -----------------------------------------------------------------------

function getDept(codeCommune) {
    if (!codeCommune) return '';
    const c = String(codeCommune);
    if (c.startsWith('97')) return c.substring(0, 3);
    return c.substring(0, 2);
}

const zoneDepts = {
    'idf_paris':          ['75', '92', '93', '94'],
    'idf_grande':         ['77', '78', '91', '95'],
    'metropoles':         ['69', '31', '33', '44', '59', '67', '35', '06', '13'],
    'cote_azur':          ['06', '13', '83', '84'],
    'montagne':           ['73', '74', '05', '38'],
    'atlantique':         ['33', '44', '85', '17', '64'],
    'bretagne_normandie': ['29', '22', '56', '35', '14', '76', '50', '61', '27'],
    'haut_de_gamme':      ['75', '06', '74', '92', '83'],
    'province_dynamique': ['31', '34', '35', '44', '33', '67', '69', '13', '06'],
    'province_accessible':['01','02','03','04','05','07','08','09','10','11','12',
                           '15','16','17','18','19','21','23','24','25','26',
                           '28','30','32','36','37','39','40','41','42',
                           '43','45','46','47','48','49','51','52','53','54',
                           '55','57','58','60','61','62','63','65','66',
                           '68','70','71','72','79','80','81','82','86',
                           '87','88','89','90']
};

const zoneLabels = {
    'idf_paris':          'Paris & Petite Couronne',
    'idf_grande':         'Grande Couronne IDF',
    'metropoles':         'Grandes Métropoles',
    'cote_azur':          'Côte d\'Azur & PACA',
    'montagne':           'Stations de Montagne',
    'atlantique':         'Littoral Atlantique',
    'bretagne_normandie': 'Bretagne & Normandie',
    'haut_de_gamme':      'Marchés Haut de Gamme',
    'province_dynamique': 'Province Dynamique',
    'province_accessible':'Province Accessible'
};

function matchZone(codeCommune, zoneValue) {
    if (zoneValue === 'all') return true;
    const dept  = getDept(codeCommune);
    const depts = zoneDepts[zoneValue] || [];
    return depts.includes(dept);
}

// -----------------------------------------------------------------------
// INIT
// -----------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', function () {
    const btnAnalyze    = document.getElementById('btnAnalyze');
    const contamination = document.getElementById('contamination');
    const maxRatio      = document.getElementById('maxRatio');
    const zoneFilter    = document.getElementById('zoneFilter');
    const tooltip       = document.getElementById('tooltip-global');

    document.getElementById('modalAnnonce').addEventListener('click', function (e) {
        if (e.target === this) closeModal();
    });

    document.addEventListener('mousemove', function (e) {
        if (tooltip.style.display === 'block') {
            tooltip.style.left = (e.clientX + 14) + 'px';
            tooltip.style.top  = (e.clientY - 10) + 'px';
        }
    });

    btnAnalyze.addEventListener('click', detectOpportunities);

    async function detectOpportunities() {
        try {
            showLoading();
            const response = await fetch('/api/opportunities', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({
                    contamination: parseFloat(contamination.value),
                    max_ratio:     parseFloat(maxRatio.value),
                    zone_filter:   'all'  // filtre zone géré côté JS
                })
            });
            const data = await response.json();
            if (data.success) {
                await displayResults(data);
            } else {
                showError(data.error || 'Erreur lors de la détection');
            }
        } catch (error) {
            showError('Erreur réseau : ' + error.message);
        }
    }

    async function displayResults(data) {
        hideMessages();

        document.getElementById('kpiOpportunities').textContent = data.nb_opportunities.toLocaleString();
        document.getElementById('kpiDecote').textContent        = `-${parseFloat(data.median_decote).toFixed(2)}%`;
        document.getElementById('kpiPrixMedian').textContent    = `${Math.round(data.median_prix_m2).toLocaleString()} €`;
        document.getElementById('kpiSurface').textContent       = `${Math.round(data.median_surface)} m²`;
        document.getElementById('kpiSection').classList.remove('hidden');

        // Pré-chargement de tous les noms de communes en parallèle
        await Promise.all(
            data.opportunities.map(opp => fetchCommuneLabel(opp.code_commune))
        );

        // Filtre zone JS appliqué dès la détection
        const zoneSelected = zoneFilter.value;
        const filtered     = zoneSelected === 'all'
            ? data.opportunities
            : data.opportunities.filter(opp => matchZone(opp.code_commune, zoneSelected));

        allOpportunities     = filtered;
        _backupOpportunities = filtered;
        currentPageOpp       = 1;

        document.getElementById('filtresSection').classList.remove('hidden');
        resetFiltres();

        renderCharts(data);
        document.getElementById('resultsSection').classList.remove('hidden');

        btnAnalyze.disabled  = false;
        btnAnalyze.innerHTML = '<i class="fas fa-search-dollar text-xl"></i><span>Détecter Opportunités</span>';
    }

    // -----------------------------------------------------------------------
    // FILTRES DYNAMIQUES
    // -----------------------------------------------------------------------

    window.applyFiltres = function () {
        const scoreMin   = parseInt(document.getElementById('filtreScore').value);
        const decoteMin  = parseInt(document.getElementById('filtreDecote').value);
        const surfaceMin = parseInt(document.getElementById('filtreSurface').value);
        const piecesMin  = parseInt(document.getElementById('filtrePieces').value);
        const prixMax    = parseInt(document.getElementById('filtrePrixMax').value);
        const prixM2Max  = parseInt(document.getElementById('filtrePrixM2Max').value);
        const standing   = document.getElementById('filtreStanding').value;
        const zone       = document.getElementById('filtreZone').value;

        const filtered = _backupOpportunities.filter(opp => {
            return (
                Math.round(opp.investment_score)          >= scoreMin   &&
                parseFloat(opp.decote_pct)                >= decoteMin  &&
                Math.round(opp.surface_reelle_bati)       >= surfaceMin &&
                Math.round(opp.nombre_pieces_principales) >= piecesMin  &&
                Math.round(opp.valeur_fonciere)           <= prixMax    &&
                Math.round(opp.prix_m2)                   <= prixM2Max  &&
                (standing === 'all' || opp.standing_relative === standing) &&
                matchZone(opp.code_commune, zone)
            );
        });

        const badges   = document.getElementById('filtresActifsBadges');
        const countEl  = document.getElementById('filtresCount');
        const actifDiv = document.getElementById('filtresActifs');
        badges.innerHTML = '';

        const actifs = [];
        if (scoreMin > 0)       actifs.push(`Score ≥ ${scoreMin}`);
        if (decoteMin > 0)      actifs.push(`Décote ≥ ${decoteMin}%`);
        if (surfaceMin > 0)     actifs.push(`Surface ≥ ${surfaceMin} m²`);
        if (piecesMin > 0)      actifs.push(`Pièces ≥ ${piecesMin}`);
        if (prixMax < 2000000)  actifs.push(`Prix ≤ ${prixMax.toLocaleString('fr-FR')} €`);
        if (prixM2Max < 20000)  actifs.push(`Prix/m² ≤ ${prixM2Max.toLocaleString('fr-FR')} €`);
        if (standing !== 'all') actifs.push(formatStanding(standing));
        if (zone !== 'all')     actifs.push(zoneLabels[zone] || zone);

        if (actifs.length > 0) {
            actifDiv.classList.remove('hidden');
            actifs.forEach(a => {
                badges.innerHTML += `
                    <span class="px-2 py-1 bg-emerald-100 text-emerald-700 text-xs rounded-full font-medium">
                        ${a}
                    </span>`;
            });
            countEl.textContent = `— ${filtered.length} résultat${filtered.length > 1 ? 's' : ''}`;
        } else {
            actifDiv.classList.add('hidden');
        }

        allOpportunities = filtered;
        currentPageOpp   = 1;
        renderOppPage(currentPageOpp);
        renderOppPagination();
        document.getElementById('paginationOpportunities').classList.remove('hidden');
    };

    window.resetFiltres = function () {
        document.getElementById('filtreScore').value     = 0;
        document.getElementById('filtreDecote').value    = 0;
        document.getElementById('filtreSurface').value   = 0;
        document.getElementById('filtrePieces').value    = 0;
        document.getElementById('filtrePrixMax').value   = 2000000;
        document.getElementById('filtrePrixM2Max').value = 20000;
        document.getElementById('filtreStanding').value  = 'all';
        document.getElementById('filtreZone').value      = 'all';

        document.getElementById('labelScoreMin').textContent   = '0';
        document.getElementById('labelDecoteMin').textContent  = '0';
        document.getElementById('labelSurfaceMin').textContent = '0';
        document.getElementById('labelPiecesMin').textContent  = '0';
        document.getElementById('labelPrixMax').textContent    = 'Illimité';
        document.getElementById('labelPrixM2Max').textContent  = 'Illimité';
        document.getElementById('filtresActifs').classList.add('hidden');

        allOpportunities = _backupOpportunities;
        currentPageOpp   = 1;
        renderOppPage(currentPageOpp);
        renderOppPagination();
        document.getElementById('paginationOpportunities').classList.remove('hidden');
    };

    // -----------------------------------------------------------------------
    // TABLEAU + PAGINATION
    // -----------------------------------------------------------------------

    function attachTooltips() {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            el.addEventListener('mouseenter', function () {
                tooltip.innerHTML     = this.getAttribute('data-tooltip');
                tooltip.style.display = 'block';
            });
            el.addEventListener('mouseleave', function () {
                tooltip.style.display = 'none';
            });
        });
    }

    window.renderOppPage = function (page) {
        const tbody = document.querySelector('#tableOpportunities tbody');
        const start = (page - 1) * itemsPerPageOpp;
        const end   = start + itemsPerPageOpp;
        const data  = allOpportunities.slice(start, end);

        tbody.innerHTML = '';

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-gray-500 py-8">
                        Aucun résultat pour ces filtres
                    </td>
                </tr>`;
            document.getElementById('paginationOppInfo').textContent = '0 résultat';
            document.getElementById('btnPrevOpp').disabled           = true;
            document.getElementById('btnNextOpp').disabled           = true;
            return;
        }

        data.forEach((opp, i) => {
            const globalIdx  = start + i;
            const communeNom = communeCache[opp.code_commune] || opp.code_commune;
            const row        = tbody.insertRow();
            row.innerHTML    = `
                <td>
                    <div class="flex flex-col cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Score d'opportunité</strong><br><br>
                        Indicateur de qualité de l'opportunité d'investissement.<br><br>
                        Un score élevé signifie que ce bien présente une décote importante par rapport
                        à son marché local, dans une zone attractive, avec une surface cohérente.<br><br>
                        Plus le score est proche de 100, plus le bien est considéré comme une opportunité rare à saisir.">
                        <span class="font-bold text-lg">${Math.round(opp.investment_score)}/100</span>
                        <span class="text-xs text-gray-400">Score investissement</span>
                    </div>
                </td>
                <td>
                    <span class="font-bold text-green-600 cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Décote vs marché local</strong><br><br>
                        Écart en pourcentage entre le prix de cette transaction et le prix médian au m² de la commune.<br><br>
                        Une décote de -50% signifie que ce bien a été vendu deux fois moins cher que la médiane locale.<br><br>
                        <span class='text-slate-300'>Cet écart peut s'expliquer par l'état du bien,
                        une vente rapide ou une succession.</span>">
                        -${parseFloat(opp.decote_pct).toFixed(2)}%
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Prix total du bien</strong><br><br>
                        Prix de vente total déclaré lors de la transaction, issu des données officielles
                        DVF 2025 publiées par la Direction Générale des Finances Publiques.">
                        ${Math.round(opp.valeur_fonciere).toLocaleString()} €
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Prix au m² du bien</strong><br><br>
                        Prix au m² calculé en divisant le prix total par la surface réelle bâtie.<br><br>
                        Permet de comparer objectivement des biens de surfaces différentes.">
                        ${Math.round(opp.prix_m2).toLocaleString()} €
                    </span>
                </td>
                <td>
                    <span class="text-gray-600 cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Prix médian du marché local</strong><br><br>
                        Prix médian au m² calculé sur l'ensemble des transactions d'appartements
                        enregistrées dans la même commune en 2025.<br><br>
                        C'est la référence utilisée pour calculer la décote de ce bien.">
                        ${Math.round(opp.marche_prix_m2_median).toLocaleString()} €
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Surface réelle bâtie</strong><br><br>
                        Surface habitable déclarée dans les données DVF 2025.<br><br>
                        Correspond à la surface habitable hors caves, garages, terrasses et annexes.">
                        ${Math.round(opp.surface_reelle_bati)} m²
                    </span>
                </td>
                <td>
                    <span class="cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Nombre de pièces principales</strong><br><br>
                        T1 = 1 pièce &nbsp; T2 = 2 pièces &nbsp; T3 = 3 pièces, etc.<br><br>
                        Ne comprend pas la cuisine, la salle de bain et les WC.">
                        ${opp.nombre_pieces_principales}
                    </span>
                </td>
                <td>
                    <span class="px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800 cursor-help"
                        data-tooltip="<strong class='text-emerald-400'>Commune</strong><br><br>
                        Nom de la commune issu de l'API officielle geo.gouv.fr.<br><br>
                        Zones disponibles dans les filtres :<br><br>
                        &bull; <strong>Paris & Petite Couronne</strong> : 75, 92, 93, 94<br>
                        &bull; <strong>Grande Couronne IDF</strong> : 77, 78, 91, 95<br>
                        &bull; <strong>Grandes Métropoles</strong> : Lyon, Bordeaux, Nantes, Toulouse...<br>
                        &bull; <strong>Côte d'Azur & PACA</strong> : 06, 13, 83, 84<br>
                        &bull; <strong>Montagne</strong> : 73, 74, 05, 38<br>
                        &bull; <strong>Littoral Atlantique</strong> : 33, 44, 85, 17, 64<br>
                        &bull; <strong>Bretagne & Normandie</strong> : 29, 22, 56, 35, 14, 76<br>
                        &bull; <strong>Haut de Gamme</strong> : 75, 06, 74, 92, 83<br>
                        &bull; <strong>Province Dynamique</strong> : 31, 34, 35, 44, 33, 67<br>
                        &bull; <strong>Province Accessible</strong> : reste du territoire">
                        ${communeNom}
                    </span>
                </td>
                <td>
                    <span class="px-3 py-1 rounded-full text-sm font-semibold cursor-help ${getStandingColor(opp.standing_relative)}"
                        data-tooltip="<strong class='text-emerald-400'>Standing relatif</strong><br><br>
                        Positionnement du prix de ce bien par rapport aux autres ventes de la même commune.
                        Indicateur purement mathématique :<br><br>
                        <span class='text-red-400'>&bull; Travaux</span> : prix &lt; 70% du marché — bien probablement
                        dégradé ou vendu en urgence. Fort potentiel de plus-value après rénovation.<br>
                        <span class='text-amber-400'>&bull; Bonne Affaire</span> : prix entre 70-90% du marché —
                        bien sous-évalué, opportunité à étudier.<br>
                        <span class='text-blue-400'>&bull; Standard</span> : prix dans la moyenne du marché local.<br>
                        <span class='text-emerald-400'>&bull; Premium</span> : prix au-dessus du marché (115-140%) —
                        bien vendu plus cher que la médiane, que ce soit justifié ou non.<br>
                        <span class='text-purple-400'>&bull; Prestige</span> : prix très au-dessus du marché (&gt;140%) —
                        transaction atypique, pas nécessairement un bien de luxe.">
                        ${formatStanding(opp.standing_relative)}
                    </span>
                </td>
                <td>
                    <button onclick="openModal(${globalIdx})"
                        class="px-3 py-2 text-xs font-semibold text-white bg-gradient-to-r from-emerald-600 to-teal-600
                               rounded-xl hover:scale-105 active:scale-95 transition-all duration-200 shadow-sm
                               hover:shadow-md whitespace-nowrap">
                        <i class="fas fa-eye mr-1"></i> Voir la fiche
                    </button>
                </td>
            `;
        });

        attachTooltips();

        const total = allOpportunities.length;
        document.getElementById('paginationOppInfo').textContent =
            `Affichage ${start + 1}-${Math.min(end, total)} sur ${total} opportunités`;
        document.getElementById('btnPrevOpp').disabled = page === 1;
        document.getElementById('btnNextOpp').disabled = page === Math.ceil(total / itemsPerPageOpp);
    };

    window.renderOppPagination = function () {
        const totalPages = Math.ceil(allOpportunities.length / itemsPerPageOpp);
        const container  = document.getElementById('paginationOppPages');
        container.innerHTML = '';

        for (let i = 1; i <= totalPages; i++) {
            const btn       = document.createElement('button');
            btn.textContent = i;
            btn.className   = `w-9 h-9 text-sm font-semibold rounded-xl transition-all duration-200 ${
                i === currentPageOpp
                    ? 'bg-emerald-600 text-white shadow'
                    : 'text-emerald-700 border-2 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50'
            }`;
            btn.addEventListener('click', () => {
                currentPageOpp = i;
                renderOppPage(currentPageOpp);
                renderOppPagination();
            });
            container.appendChild(btn);
        }

        document.getElementById('btnPrevOpp').onclick = () => {
            if (currentPageOpp > 1) {
                currentPageOpp--;
                renderOppPage(currentPageOpp);
                renderOppPagination();
            }
        };

        document.getElementById('btnNextOpp').onclick = () => {
            if (currentPageOpp < totalPages) {
                currentPageOpp++;
                renderOppPage(currentPageOpp);
                renderOppPagination();
            }
        };
    };

    // -----------------------------------------------------------------------
    // GRAPHIQUES
    // -----------------------------------------------------------------------

    function renderCharts(data) {
        const ctxScores = document.getElementById('chartScores').getContext('2d');
        if (window.chartScores && typeof window.chartScores.destroy === 'function') {
            window.chartScores.destroy();
        }

        window.chartScores = new Chart(ctxScores, {
            type: 'bar',
            data: {
                labels: data.score_bins.labels,
                datasets: [{
                    label:           'Nombre d\'opportunités',
                    data:            data.score_bins.counts,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor:     'rgb(59, 130, 246)',
                    borderWidth:     2
                }]
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    title:  { display: true, text: 'Plus le score est élevé, meilleure est l\'opportunité' }
                },
                scales: { y: { beginAtZero: true } }
            }
        });

        const ctxZones = document.getElementById('chartZones').getContext('2d');
        if (window.chartZones && typeof window.chartZones.destroy === 'function') {
            window.chartZones.destroy();
        }

        window.chartZones = new Chart(ctxZones, {
            type: 'doughnut',
            data: {
                labels: data.zone_distribution.labels,
                datasets: [{
                    data:            data.zone_distribution.counts,
                    backgroundColor: [
                        'rgba(59, 130, 246, 0.8)', 'rgba(147, 51, 234, 0.8)',
                        'rgba(236, 72, 153, 0.8)',  'rgba(34, 197, 94, 0.8)'
                    ]
                }]
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }

    // -----------------------------------------------------------------------
    // MODALE FICHE BIEN
    // -----------------------------------------------------------------------

    window.openModal = function (idx) {
        const opp        = allOpportunities[idx];
        const communeNom = communeCache[opp.code_commune] || opp.code_commune;
        const pieces     = Math.round(opp.nombre_pieces_principales);
        const surf       = Math.round(opp.surface_reelle_bati);
        const typoBien   = pieces <= 1 ? 'Studio' : `Appartement T${pieces}`;

        document.getElementById('modalTitre').textContent        = `${typoBien} — ${surf} m²`;
        document.getElementById('modalLocalisation').textContent = `${communeNom} · Données DVF 2025`;
        document.getElementById('modalScore').textContent        = `Score ${Math.round(opp.investment_score)}/100`;
        document.getElementById('modalPrix').textContent         = `${Math.round(opp.valeur_fonciere).toLocaleString('fr-FR')} €`;
        document.getElementById('modalSurface').textContent      = `${surf} m²`;
        document.getElementById('modalPieces').textContent       = `${pieces} pièce${pieces > 1 ? 's' : ''}`;
        document.getElementById('modalPrixM2').textContent       = `${Math.round(opp.prix_m2).toLocaleString('fr-FR')} €/m²`;
        document.getElementById('modalDecote').textContent       = `-${parseFloat(opp.decote_pct).toFixed(2)}%`;
        document.getElementById('modalMarche').textContent       = `${Math.round(opp.marche_prix_m2_median).toLocaleString('fr-FR')} €/m²`;
        document.getElementById('modalScoreDetail').textContent  = `${Math.round(opp.investment_score)}/100`;
        document.getElementById('modalZone').textContent         = communeNom;

        const plusValue = Math.round(opp.marche_prix_m2_median * surf) - Math.round(opp.valeur_fonciere);
        document.getElementById('modalPotentiel').textContent =
            `+${plusValue.toLocaleString('fr-FR')} € si remis au prix marché`;

        const standingBadge       = document.getElementById('modalStandingBadge');
        standingBadge.textContent = formatStanding(opp.standing_relative);
        standingBadge.className   = `px-3 py-1 rounded-full text-xs font-bold ${getStandingColor(opp.standing_relative)}`;

        document.getElementById('modalDescription').textContent =
            generateDescription(opp, typoBien, communeNom, surf, pieces);

        setTimeout(() => {
            Plotly.newPlot('modalMap', [{
                type:      'scattermapbox',
                lat:       [opp.latitude],
                lon:       [opp.longitude],
                mode:      'markers',
                marker:    { size: 16, color: '#10b981' },
                text:      [`${typoBien} — ${communeNom} — ${Math.round(opp.valeur_fonciere).toLocaleString('fr-FR')} €`],
                hoverinfo: 'text'
            }], {
                mapbox: {
                    style:  'open-street-map',
                    center: { lat: opp.latitude, lon: opp.longitude },
                    zoom:   13
                },
                margin: { t: 0, b: 0, l: 0, r: 0 },
                height: 250
            }, { responsive: true });
        }, 100);

        const modal = document.getElementById('modalAnnonce');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        document.body.style.overflow = 'hidden';
    };

    window.closeModal = function () {
        const modal = document.getElementById('modalAnnonce');
        modal.classList.add('hidden');
        modal.classList.remove('flex');
        document.body.style.overflow = '';
    };

    function generateDescription(opp, typoBien, communeNom, surf, pieces) {
        const standing  = opp.standing_relative;
        const decote    = parseFloat(opp.decote_pct).toFixed(0);
        const plusValue = Math.round((opp.marche_prix_m2_median - opp.prix_m2) * surf).toLocaleString('fr-FR');

        const introZone = {
            '1_Metropole_Top15':   'dans l\'une des métropoles les plus dynamiques de France,',
            '2_Ile_de_France':     'en Île-de-France dans un marché à forte demande locative,',
            '3_Zone_Touristique':  'dans une zone touristique à fort potentiel saisonnier,',
            '4_Province_Standard': 'en province avec un marché accessible et des rendements attractifs,'
        };

        const descStanding = {
            '1_Decote_Travaux':     `ce bien nécessite des travaux de rénovation, ce qui explique sa décote de ${decote}% par rapport au marché local. C'est une opportunité rare pour un investisseur prêt à rénover et réaliser une plus-value potentielle estimée à ${plusValue} €.`,
            '2_Bonne_Affaire':      `ce bien a été vendu ${decote}% sous le prix médian du marché local sans raison apparente majeure. Une opportunité à saisir rapidement avec un potentiel de valorisation estimé à ${plusValue} €.`,
            '3_Standard_Marche':    `ce bien est vendu dans la moyenne du marché local. L'algorithme Isolation Forest a détecté des caractéristiques atypiques qui en font une opportunité à étudier.`,
            '4_Premium':            `ce bien est vendu au-dessus de la médiane locale, mais l'algorithme a identifié une anomalie dans sa transaction qui mérite attention.`,
            '5_Prestige_Exception': `ce bien présente un prix très au-dessus de la médiane locale — transaction atypique détectée par Isolation Forest.`
        };

        const intro = introZone[opp.categorie_geo] || 'dans cette zone immobilière,';
        const desc  = descStanding[standing]        || 'ce bien présente des caractéristiques intéressantes selon notre algorithme.';

        return `Situé à ${communeNom}, ${intro} ${desc} Le bien propose ${surf} m² pour ${pieces} pièce${pieces > 1 ? 's' : ''} principales, avec un prix au m² de ${Math.round(opp.prix_m2).toLocaleString('fr-FR')} € contre ${Math.round(opp.marche_prix_m2_median).toLocaleString('fr-FR')} € pour le marché local. Détecté et scoré automatiquement par l'algorithme ImmoPRO (score ${Math.round(opp.investment_score)}/100).`;
    }

    // -----------------------------------------------------------------------
    // UTILITAIRES
    // -----------------------------------------------------------------------

    function formatStanding(standing) {
        const map = {
            '1_Decote_Travaux':     'Travaux',
            '2_Bonne_Affaire':      'Bonne Affaire',
            '3_Standard_Marche':    'Standard',
            '4_Premium':            'Premium',
            '5_Prestige_Exception': 'Prestige'
        };
        return map[standing] || standing;
    }

    function getStandingColor(standing) {
        const map = {
            '1_Decote_Travaux':     'bg-red-100 text-red-700 border border-red-200',
            '2_Bonne_Affaire':      'bg-amber-100 text-amber-700 border border-amber-200',
            '3_Standard_Marche':    'bg-blue-100 text-blue-700 border border-blue-200',
            '4_Premium':            'bg-emerald-100 text-emerald-700 border border-emerald-200',
            '5_Prestige_Exception': 'bg-purple-100 text-purple-700 border border-purple-200'
        };
        return map[standing] || 'bg-gray-100 text-gray-700 border border-gray-200';
    }

    function showLoading() {
        btnAnalyze.disabled  = true;
        btnAnalyze.innerHTML = '<i class="fas fa-spinner fa-spin text-xl"></i><span>Analyse en cours...</span>';
        hideMessages();
    }

    function hideMessages() {
        document.getElementById('initialMessage').classList.add('hidden');
        document.getElementById('errorAlert').classList.add('hidden');
        document.getElementById('kpiSection').classList.add('hidden');
        document.getElementById('resultsSection').classList.add('hidden');
        document.getElementById('filtresSection').classList.add('hidden');
    }

    function showError(message) {
        btnAnalyze.disabled  = false;
        btnAnalyze.innerHTML = '<i class="fas fa-search-dollar text-xl"></i><span>Détecter Opportunités</span>';
        document.getElementById('errorMessage').textContent = message;
        document.getElementById('errorAlert').classList.remove('hidden');
    }
});
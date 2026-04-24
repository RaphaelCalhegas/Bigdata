// analyse_marche.js - Logique pour l'onglet Analyse de Marché

let chartPrixDistribution = null;
let chartStanding         = null;
let allCommunes           = [];
let communesInfo          = [];
let currentPage           = 1;
const itemsPerPage        = 10;

document.addEventListener('DOMContentLoaded', function () {
    const btnAnalyser = document.getElementById('btnAnalyser');
    const selectDept  = document.getElementById('selectDepartement');

    btnAnalyser.addEventListener('click', async function () {
        const codeDept = selectDept.value;
        if (!codeDept) {
            alert('Veuillez sélectionner un département');
            return;
        }
        await analyserDepartement(codeDept);
    });

    // -----------------------------------------------------------------------
    // INFOBULLES — Clic sur ? pour afficher/masquer
    // -----------------------------------------------------------------------
    document.addEventListener('click', function (e) {
        const btn = e.target.closest('.info-btn');

        if (btn) {
            e.stopPropagation();
            const id  = btn.dataset.info;
            const box = document.getElementById(`info-${id}`);
            if (!box) return;

            // Ferme toutes les autres infobulles
            document.querySelectorAll('.info-box').forEach(b => {
                if (b !== box) b.classList.add('hidden');
            });

            // Toggle celle-ci
            box.classList.toggle('hidden');
        } else {
            // Clic ailleurs → ferme toutes
            document.querySelectorAll('.info-box').forEach(b => b.classList.add('hidden'));
        }
    });
});

async function analyserDepartement(codeDept) {
    showLoading();

    try {
        const [statsRes, communesRes] = await Promise.all([
            fetch(`/api/analyse-departement/${codeDept}`),
            fetch(`/api/top-communes/${codeDept}`)
        ]);

        const stats       = await statsRes.json();
        const topCommunes = await communesRes.json();

        if (stats.error) {
            alert(stats.error);
            hideLoading();
            return;
        }

        hideLoading();

        displayKPIs(stats);
        displayCharts(stats);
        await displayTopCommunes(topCommunes);

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
    document.getElementById('kpiPrixMedian').textContent   = formatPrice(stats.prix_m2_median) + '/m²';
    document.getElementById('kpiSurface').textContent      = stats.surface_moyenne.toFixed(1) + ' m²';
    document.getElementById('kpiPrixMoyen').textContent    = formatPrice(stats.prix_moyen);
}

function displayCharts(stats) {
    const ctxPrix = document.getElementById('chartPrixDistribution');
    if (chartPrixDistribution) chartPrixDistribution.destroy();

    chartPrixDistribution = new Chart(ctxPrix, {
        type: 'bar',
        data: {
            labels: ['Q1 (25%)', 'Médiane', 'Moyenne', 'Q3 (75%)'],
            datasets: [{
                label:           'Prix au m² (€)',
                data:            [stats.prix_m2_q25, stats.prix_m2_median, stats.prix_m2_mean, stats.prix_m2_q75],
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
            responsive:          true,
            maintainAspectRatio: true,
            plugins: { legend: { display: false } },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { callback: value => value.toLocaleString('fr-FR') + ' €' }
                }
            }
        }
    });

    const ctxStanding = document.getElementById('chartStanding');
    if (chartStanding) chartStanding.destroy();

    const standingData = stats.repartition_standing || {};
    const labels       = Object.keys(standingData).map(k => getStandingLabel(k));
    const values       = Object.values(standingData);

    chartStanding = new Chart(ctxStanding, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data:            values,
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
            responsive:          true,
            maintainAspectRatio: true,
            plugins: { legend: { position: 'bottom' } }
        }
    });
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

async function displayTopCommunes(communes) {
    const tbody = document.querySelector('#tableTopCommunes tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="text-center text-gray-500">Chargement des communes...</td></tr>';

    if (communes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-gray-500">Aucune donnée</td></tr>';
        return;
    }

    allCommunes  = communes;
    communesInfo = await Promise.all(communes.map(c => getCommuneInfo(c.code_commune)));
    currentPage  = 1;

    renderPage(currentPage);
    renderPagination();

    document.getElementById('paginationCommunes').classList.remove('hidden');
}

function renderPage(page) {
    const tbody    = document.querySelector('#tableTopCommunes tbody');
    const start    = (page - 1) * itemsPerPage;
    const end      = start + itemsPerPage;
    const pageData = allCommunes.slice(start, end);

    tbody.innerHTML = '';

    pageData.forEach((commune, i) => {
        const index = start + i;
        const info  = communesInfo[index];
        const rang  = index + 1;

        tbody.innerHTML += `
            <tr>
                <td><strong>#${rang}</strong></td>
                <td>
                    <div class="font-semibold text-slate-800">${info.nom}</div>
                    <div class="text-xs text-slate-400">CP : ${info.codePostal} &nbsp;·&nbsp; INSEE : ${commune.code_commune}</div>
                </td>
                <td>${commune.nb_transactions.toLocaleString('fr-FR')}</td>
                <td>${formatPrice(commune.prix_m2_median)}</td>
                <td>${commune.surface_moyenne.toFixed(1)} m²</td>
            </tr>
        `;
    });

    const total = allCommunes.length;
    document.getElementById('paginationInfo').textContent =
        `Affichage ${start + 1}-${Math.min(end, total)} sur ${total} communes`;

    document.getElementById('btnPrevPage').disabled = page === 1;
    document.getElementById('btnNextPage').disabled = page === Math.ceil(total / itemsPerPage);
}

function renderPagination() {
    const totalPages = Math.ceil(allCommunes.length / itemsPerPage);
    const container  = document.getElementById('paginationPages');
    container.innerHTML = '';

    for (let i = 1; i <= totalPages; i++) {
        const btn       = document.createElement('button');
        btn.textContent = i;
        btn.className   = `w-9 h-9 text-sm font-semibold rounded-xl transition-all duration-200 ${
            i === currentPage
                ? 'bg-emerald-600 text-white shadow'
                : 'text-emerald-700 border-2 border-emerald-200 hover:border-emerald-400 hover:bg-emerald-50'
        }`;
        btn.addEventListener('click', () => {
            currentPage = i;
            renderPage(currentPage);
            renderPagination();
        });
        container.appendChild(btn);
    }

    document.getElementById('btnPrevPage').onclick = () => {
        if (currentPage > 1) { currentPage--; renderPage(currentPage); renderPagination(); }
    };
    document.getElementById('btnNextPage').onclick = () => {
        if (currentPage < totalPages) { currentPage++; renderPage(currentPage); renderPagination(); }
    };
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
        '2_Bonne_Affaire':      'Bonne Affaire',
        '3_Standard_Marche':    'Standard',
        '4_Premium':            'Premium',
        '5_Prestige_Exception': 'Prestige'
    };
    return labels[code] || code;
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

# 🏘️ ImmoPRO - Plateforme d'Analyse Immobilière par Intelligence Artificielle

Application Flask de pointe exploitant le Machine Learning pour l'analyse approfondie du marché immobilier français à partir des données **DVF 2025** (Demande de Valeurs Foncières).

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.1.3-green)
![MongoDB](https://img.shields.io/badge/MongoDB_Atlas-cloud-green)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.7.2-orange)
![Render](https://img.shields.io/badge/Deployed-Render-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

🌐 **Application en ligne** : [https://bigdata-ggqx.onrender.com](https://bigdata-ggqx.onrender.com)

---

## 📋 Table des matières

1. [Vue d'ensemble](#-vue-densemble)
2. [Architecture du projet](#-architecture-du-projet)
3. [Base de données MongoDB Atlas](#-base-de-données-mongodb-atlas)
4. [Pipeline de traitement des données](#-pipeline-de-traitement-des-données)
5. [Machine Learning et Clustering](#-machine-learning-et-clustering)
6. [Fonctionnalités de l'application](#-fonctionnalités-de-lapplication)
7. [Authentification et recommandations](#-authentification-et-recommandations)
8. [API Geo.gouv.fr](#-api-geogouv)
9. [Installation locale](#-installation-locale)
10. [Déploiement production](#-déploiement-production)
11. [Technologies utilisées](#-technologies-utilisées)

---

## 🎯 Vue d'ensemble

**ImmoPRO** est une plateforme web d'analyse immobilière qui exploite **346 639 transactions immobilières** de l'année 2025 pour fournir :

- ✅ **Estimations de prix** basées sur l'analyse par clustering K-Means
- 📊 **Analyses de marché** par département avec 96 départements couverts
- 🗺️ **Cartographie interactive** des transactions via Plotly
- 🔍 **Détection d'opportunités d'investissement** via Isolation Forest
- 📈 **Recherche de biens comparables** avec scoring de similarité
- 👤 **Authentification utilisateur** avec historique et recommandations personnalisées
- 🗄️ **Base de données MongoDB Atlas** (cloud) pour une architecture Big Data scalable
- 🌍 **Intégration API Geo.gouv.fr** pour la résolution des codes communes en noms réels

---

## 🏗️ Architecture du projet

```
Bigdata-main/
│
├── app.py                      # Application Flask principale (routes et API)
├── prepare_models.py           # Pipeline ETL et entraînement des modèles ML
├── migrate_reference_data.py   # Script de migration des données vers MongoDB Atlas
├── analyze_clusters.py         # Script d'analyse des clusters K-Means
├── pyproject.toml              # Configuration des dépendances
├── requirements.txt            # Dépendances Python pour Render
├── .python-version             # Version Python forcée (3.11.9) pour Render
├── gunicorn.conf.py            # Configuration Gunicorn (timeout, workers)
│
├── models/                     # Modèles ML sérialisés (non régénérés en prod)
│   ├── kmeans_model.pkl        # Modèle K-Means (6 clusters)
│   └── scaler.pkl              # StandardScaler pour normalisation
│
├── utils/                      # Modules utilitaires
│   ├── __init__.py             # Exports des classes principales
│   ├── data_loader.py          # DataManager (connexion MongoDB + requêtes)
│   ├── clustering.py           # Fonctions d'analyse des clusters
│   ├── predictor.py            # PriceEstimator (estimation de prix)
│   ├── opportunities.py        # Isolation Forest (détection anomalies)
│   ├── db.py                   # Connexion MongoDB Atlas (certifi + TLS)
│   ├── auth.py                 # Authentification (inscription/connexion)
│   └── recommendations.py     # Moteur de recommandations personnalisées
│
├── templates/                  # Templates HTML (Jinja2)
│   ├── base.html               # Layout de base (navigation + footer)
│   ├── landing.html            # Page d'accueil publique
│   ├── index.html              # Dashboard utilisateur connecté
│   ├── estimation.html         # Onglet 1 : Estimation de bien
│   ├── analyse_marche.html     # Onglet 2 : Analyse de marché (96 depts)
│   ├── cartographie.html       # Onglet 3 : Carte interactive Plotly
│   ├── similaires.html         # Onglet 4 : Biens comparables
│   ├── opportunites.html       # Onglet 5 : Détection d'opportunités
│   ├── clusters.html           # Profils des 6 segments de marché
│   ├── login.html              # Page de connexion
│   ├── register.html           # Page d'inscription
│   └── profile.html            # Profil utilisateur + recommandations
│
└── static/                     # Assets frontend
    ├── css/
    │   └── style.css           # Styles Tailwind CSS personnalisés
    └── js/                     # Logique JavaScript par onglet
        ├── estimation.js       # Autocomplétion code postal + estimation
        ├── analyse_marche.js   # Sélecteur 96 départements + pagination Top 20
        ├── cartographie.js     # Carte Plotly (5 000 points)
        ├── similaires.js       # Recherche comparables + tooltips + pagination
        └── opportunites.js     # Isolation Forest + filtres + modale + zones JS
```

---

## 🗄️ Base de données MongoDB Atlas

ImmoPRO utilise **MongoDB Atlas** (cloud) comme base de données principale. Les données ne sont plus stockées en fichiers `.pkl` locaux — tout est requêté en temps réel depuis Atlas.

### Collections

| Collection | Documents | Contenu |
|------------|-----------|---------|
| `properties` | 346 639 | Transactions DVF 2025 enrichies (prix, surface, coords, cluster, standing...) |
| `communes` | 6 767 | Statistiques agrégées par commune (prix médian, nb transactions...) |
| `users` | Variable | Comptes utilisateurs (email, hash mot de passe) |
| `search_sessions` | Variable | Historique des recherches par utilisateur |
| `recommendations` | Variable | Suggestions personnalisées générées |

### Connexion sécurisée

```python
# utils/db.py
import certifi
from pymongo import MongoClient

_client = MongoClient(
    MONGO_URI,                        # Variable d'environnement
    serverSelectionTimeoutMS=5000,
    tlsCAFile=certifi.where()         # Certificats SSL pour Atlas
)
```

### Optimisation mémoire (Render gratuit)

Pour la route `/api/opportunities`, l'échantillonnage est fait **directement dans MongoDB** via `$sample` pour éviter de charger 346K lignes en RAM :

```python
docs = list(data_manager.db["properties"].aggregate([
    {"$match": {"valeur_fonciere": {"$gte": 50000}, "prix_m2": {"$gte": 500}}},
    {"$sample": {"size": 15000}},
    {"$project": {"_id": 0}}
]))
```

---

## 📦 Pipeline de traitement des données

Le script `prepare_models.py` exécute un **pipeline ETL complet** pour préparer les données initiales.

### 1️⃣ Extraction des données

**Source** : [geo-dvf (data.gouv.fr)](https://files.data.gouv.fr/geo-dvf/latest/csv/2025/full.csv.gz)

**Filtres appliqués** :
- Nature mutation = `Vente`
- Type local = `Appartement`
- France métropolitaine uniquement
- Coordonnées GPS valides
- Surface terrain = `0`

**Résultat brut** : ~450 000 ventes d'appartements

### 2️⃣ Nettoyage et outliers

Filtrage par quantiles P1-P99 sur `surface_reelle_bati`, `valeur_fonciere` et `nombre_pieces_principales`.

**Dataset final** : **346 639 transactions** propres

### 3️⃣ Feature Engineering

| Variable | Description |
|----------|-------------|
| `prix_m2` | `valeur_fonciere / surface_reelle_bati` |
| `marche_prix_m2_median` | Prix médian au m² par commune |
| `categorie_geo` | 4 zones géographiques (Métropole, IDF, Touristique, Province) |
| `standing_relative` | 5 niveaux de standing (ratio prix/marché local) |
| `cluster_kmeans` | Segment K-Means (0-5) |

### 4️⃣ Standing relatif

| Standing | Ratio | Description |
|----------|-------|-------------|
| `1_Decote_Travaux` | < 0.70 | -30% sous le marché |
| `2_Bonne_Affaire` | 0.70 - 0.90 | -10 à -30% sous le marché |
| `3_Standard_Marche` | 0.90 - 1.15 | ±15% du marché |
| `4_Premium` | 1.15 - 1.40 | +15 à +40% au-dessus |
| `5_Prestige_Exception` | > 1.40 | +40% et plus |

---

## 🤖 Machine Learning et Clustering

### K-Means — 6 segments de marché

| Cluster | Nom | Caractéristiques | % marché |
|---------|-----|-----------------|---------|
| **0** | Petits Apparts Province Sud | 37m², 3 700€/m², 134K€ | 22.1% |
| **1** | Apparts Premium Paris/IDF | 43m², 9 900€/m², 425K€ | 9.5% |
| **2** | Apparts Familiaux IDF Périphérie | 70m², 3 100€/m², 218K€ | 19.5% |
| **3** | Apparts Standard Province | 70m², 2 900€/m², 202K€ | 21.8% |
| **4** | Grandes Surfaces Familiales | 111m², 2 960€/m², 329K€ | 7.4% |
| **5** | Studios/T2 Province Dynamique | 38m², 3 470€/m², 129K€ | 19.8% |

**Métriques** :
- Score Silhouette : **0.260**
- Davies-Bouldin : **1.251**
- Calinski-Harabasz : **3 220**

### Isolation Forest — Détection d'opportunités

**Score d'investissement multi-critères** :

```python
investment_score = (
    45% × score_decote    +   # Décote vs marché local
    20% × score_surface   +   # Qualité surface (pénalise < 25m² ou > 200m²)
    20% × score_zone      +   # Attractivité zone géographique
    15% × score_anomalie      # Degré d'anomalie détecté par Isolation Forest
)
```

**Paramètres production** (optimisés pour Render gratuit 512MB) :
- `n_estimators=30`
- `n_jobs=1`
- Échantillon : 15 000 lignes via `$sample` MongoDB

---

## 🎨 Fonctionnalités de l'application

### 1️⃣ Estimation de bien (`/estimation`)

- Autocomplétion du code postal via API Geo.gouv.fr
- Gestion spéciale des arrondissements Paris / Lyon / Marseille
- Estimation basée sur le prix médian communal + ajustement par typologie
- Fourchette ±15%, standing relatif, cluster K-Means associé

### 2️⃣ Analyse de marché (`/analyse-marche`)

- **96 départements** organisés par région en `<optgroup>`
- Graphiques : distribution des prix, répartition des standings
- **Top 20 communes** les plus actives (pagination 10 par page)
- Données DVF 2025 en temps réel depuis MongoDB

### 3️⃣ Cartographie interactive (`/cartographie`)

- Carte Plotly avec 5 000 points échantillonnés via `$sample` MongoDB
- Marqueurs colorés par cluster K-Means
- Filtres prix min/max, zoom adaptatif

### 4️⃣ Biens Comparables (`/similaires`)

- Autocomplétion code postal → nom commune (API Geo.gouv.fr)
- Gestion arrondissements Paris / Lyon / Marseille
- Critères : même département, ±30% surface, ±1 pièce
- Tableau avec infobulles sur chaque colonne
- Pagination 10 par 10, carte Plotly des résultats
- Sidebar sticky sur desktop

### 5️⃣ Opportunités d'Investissement (`/opportunites`)

- **Isolation Forest** sur 15 000 transactions échantillonnées
- **8 filtres dynamiques** : score min, décote min, surface, pièces, prix total, prix/m², standing, zone
- **10 zones géographiques** filtrées côté JS par département :
  - Paris & Petite Couronne (75, 92, 93, 94)
  - Grande Couronne IDF (77, 78, 91, 95)
  - Grandes Métropoles (Lyon, Bordeaux, Nantes...)
  - Côte d'Azur & PACA (06, 13, 83, 84)
  - Stations de Montagne (73, 74, 05, 38)
  - Littoral Atlantique (33, 44, 85, 17, 64)
  - Bretagne & Normandie (29, 22, 56, 35, 14, 76)
  - Marchés Haut de Gamme (75, 06, 74, 92, 83)
  - Province Dynamique (31, 34, 35, 44, 33, 67)
  - Province Accessible (reste du territoire)
- Noms de communes résolus via **API Geo.gouv.fr** avec cache JS
- **Modale fiche bien** : carte Plotly, analyse ImmoPRO, description auto-générée
- Badges filtres actifs, pagination 10 par 10, tooltips sur toutes les colonnes

### 6️⃣ Segments de marché (`/clusters`)

- Profils détaillés des 6 clusters K-Means
- Stats : prix moyen/m², surface moyenne, nb biens, % du marché total
- Zones et départements dominants par cluster

---

## 👤 Authentification et recommandations

- **Inscription** (`/register`) : Validation + hashage bcrypt
- **Connexion** (`/login`) : Session Flask-Login
- **Profil** (`/profile`) : Historique des recherches + recommandations personnalisées
- Chaque recherche est sauvegardée en MongoDB (collection `search_sessions`)
- Le moteur de recommandations analyse l'historique pour suggérer des communes cohérentes

### Routes

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/register` | GET/POST | Non | Inscription |
| `/login` | GET/POST | Non | Connexion |
| `/logout` | GET | Oui | Déconnexion |
| `/profile` | GET | Oui | Profil utilisateur |
| `/api/profile/preferences` | POST | Oui | Mise à jour préférences |
| `/api/recommendations/refresh` | POST | Oui | Actualisation recommandations |

---

## 🌍 API Geo.gouv

ImmoPRO intègre l'**API officielle Geo.gouv.fr** pour résoudre les codes INSEE en noms de communes réels.

### Utilisation

```javascript
// Résolution d'un code commune → nom réel
const res  = await fetch(`https://geo.api.gouv.fr/communes/${codeCommune}?fields=nom`);
const data = await res.json();
// data.nom → "Rueil-Malmaison", "Paris 7ème", "Lyon 3ème"...
```

### Pages concernées

| Page | Usage |
|------|-------|
| **Estimation** | Autocomplétion code postal → commune |
| **Comparables** | Autocomplétion + affichage nom commune dans tableau |
| **Opportunités** | Résolution des codes communes dans tableau + modale |

### Cache JS (Opportunités)

Pour éviter des appels API répétés, un cache JS est pré-rempli avec les arrondissements de Paris, Lyon et Marseille, puis alimenté dynamiquement :

```javascript
const communeCache = {
    '75107': 'Paris 7ème',
    '69383': 'Lyon 3ème',
    // ...
};

async function fetchCommuneLabel(codeCommune) {
    if (communeCache[codeCommune]) return communeCache[codeCommune];
    // Appel API Geo.gouv.fr si non en cache
}
```

Le pré-chargement de tous les noms de communes se fait en parallèle au chargement des résultats via `Promise.all`.

---

## 💻 Installation locale

### Prérequis

- **Python 3.11+**
- **MongoDB local** (ou compte MongoDB Atlas)
- **pip**

### Étapes

1. **Cloner le projet** :
   ```bash
   git clone https://github.com/RaphaelCalhegas/Bigdata.git
   cd Bigdata-main
   ```

2. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

3. **Configurer les variables d'environnement** — créer un fichier `.env` :
   ```env
   MONGO_URI=mongodb://localhost:27017/
   DB_NAME=immopro
   SECRET_KEY=votre-cle-secrete
   ```

4. **Peupler MongoDB** (si base vide) :
   ```bash
   python prepare_models.py
   python migrate_reference_data.py
   ```

5. **Lancer l'application** :
   ```bash
   python app.py
   ```

   **Serveur** : http://localhost:5000

---

## 🚀 Déploiement production

ImmoPRO est déployé sur **Render** avec **MongoDB Atlas**.

### Stack production

| Composant | Service | Détails |
|-----------|---------|---------|
| Application | Render (Web Service) | Instance gratuite, Python 3.11.9 |
| Base de données | MongoDB Atlas | Cluster M0 gratuit (512MB) |
| Serveur WSGI | Gunicorn | `--timeout 120 --workers 1` |
| SSL MongoDB | certifi | `tlsCAFile=certifi.where()` |

### Variables d'environnement Render

```
MONGO_URI  = mongodb+srv://<user>:<pass>@cluster.mongodb.net/immopro?retryWrites=true&w=majority
DB_NAME    = immopro
SECRET_KEY = <clé-secrète>
```

### Start Command

```bash
gunicorn app:app --config gunicorn.conf.py
```

### Points de vigilance

- L'instance gratuite Render **s'endort après 15 min** d'inactivité → délai de réveil de ~50 secondes
- MongoDB Atlas : Network Access doit inclure `0.0.0.0/0` pour Render
- Les modèles ML (`.pkl`) sont inclus dans le repo GitHub (kmeans + scaler uniquement)
- `prepare_models.py` n'est **plus nécessaire** en production — les données sont dans Atlas

### URL de production

🌐 [https://bigdata-ggqx.onrender.com](https://bigdata-ggqx.onrender.com)

---

## 🛠️ Technologies utilisées

### Backend

| Technologie | Version | Usage |
|-------------|---------|-------|
| Flask | 3.1.3 | Framework web |
| Flask-Login | 0.6.3 | Gestion sessions |
| Flask-Bcrypt | 1.0.1 | Hashage mots de passe |
| PyMongo | 4.16.0 | Driver MongoDB |
| certifi | 2024+ | Certificats SSL Atlas |
| pandas | 2.3.3 | Manipulation données |
| NumPy | 2.2.6 | Calculs numériques |
| scikit-learn | 1.7.2 | K-Means, Isolation Forest |
| dnspython | 2.8.0 | Résolution DNS Atlas |
| Gunicorn | 21.2.0 | Serveur WSGI production |

### Frontend

| Technologie | Usage |
|-------------|-------|
| Tailwind CSS | Framework CSS utility-first |
| JavaScript Vanilla | Logique interactive par onglet |
| Jinja2 | Templates Flask |
| Font Awesome 6.5.1 | Icônes |
| Plotly 2.27.0 | Cartographie + graphiques |
| Chart.js 4.4.0 | Graphiques analyse marché |

### APIs externes

| API | Usage |
|-----|-------|
| [Geo.gouv.fr](https://geo.api.gouv.fr) | Résolution codes communes → noms réels, autocomplétion |

### Data

| Élément | Valeur |
|---------|--------|
| Source | [DVF data.gouv.fr](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/) |
| Millésime | DVF 2025 |
| Volume | 346 639 transactions d'appartements |
| Communes | 6 767 communes référencées |
| Couverture | France métropolitaine |

---

## 📊 Performances et métriques

| Indicateur | Valeur |
|------------|--------|
| Score Silhouette K-Means | 0.260 |
| Davies-Bouldin | 1.251 |
| Calinski-Harabasz | 3 220 |
| Temps réponse API estimation | < 100ms |
| Temps détection opportunités | ~10 secondes |
| Chargement carte (5K points) | ~2 secondes |

---

## 📝 Fonctionnalités complétées

- [x] Authentification utilisateur (inscription, connexion, profil)
- [x] MongoDB Atlas (migration complète depuis .pkl)
- [x] Déploiement Render + SSL certifi
- [x] 96 départements dans l'Analyse Marché
- [x] Top 20 communes avec pagination
- [x] Autocomplétion code postal (API Geo.gouv.fr)
- [x] Biens comparables avec tooltips + pagination + carte
- [x] Opportunités : 10 zones JS, 8 filtres dynamiques, modale fiche bien
- [x] Noms communes via Geo.gouv.fr (cache + Promise.all)
- [x] Optimisation mémoire ($sample MongoDB)

## 🔜 Améliorations futures

- [ ] Export PDF des analyses
- [ ] Cache Redis pour requêtes récurrentes
- [ ] Docker pour déploiement simplifié
- [ ] XGBoost/LightGBM pour estimation de prix plus précise
- [ ] Prédictions temporelles (évolution des prix)
- [ ] Dashboard admin + monitoring

---

## 📄 Licence

MIT License — Libre d'utilisation et modification

---

## 👨‍💻 Auteurs

**Raphael Calhegas** — **Emma Feneau**  
Projet d'analyse immobilière IA — BIG DATA *(CY TECH — ING3 FINTECH — 2026)*

---

## 🙏 Remerciements

- **Enseignants** : Bruno Ixsil et Julien Savry
- **data.gouv.fr** : Mise à disposition des données DVF
- **Geo.gouv.fr** : API de référence des communes françaises

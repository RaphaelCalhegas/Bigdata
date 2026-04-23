# 🏘️ ImmoInsight Pro - Plateforme d'Analyse Immobilière par Intelligence Artificielle 

Application Flask de pointe exploitant le Machine Learning pour l'analyse approfondie du marché immobilier français à partir des données **DVF 2024** (Demande de Valeurs Foncières).

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green)
![MongoDB](https://img.shields.io/badge/MongoDB-8.2-green)
![scikit--learn](https://img.shields.io/badge/scikit--learn-1.3.0-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## 📋 Table des matières

1. [Vue d'ensemble](#-vue-densemble)
2. [Architecture du projet](#-architecture-du-projet)
3. [Pipeline de traitement des données](#-pipeline-de-traitement-des-données)
4. [Machine Learning et Clustering](#-machine-learning-et-clustering)
5. [Fonctionnalités de l'application](#-fonctionnalités-de-lapplication)
6. [Authentification et recommandations](#-authentification-et-recommandations)
7. [Installation](#-installation)
8. [Utilisation](#-utilisation)
9. [Technologies utilisées](#-technologies-utilisées)

---

## 🎯 Vue d'ensemble

**ImmoInsight Pro** est une plateforme web d'analyse immobilière qui exploite **302,000+ transactions immobilières** de l'année 2024 pour fournir :

- ✅ **Estimations de prix** basées sur l'analyse par clustering K-Means
- 📊 **Analyses de marché** par département et commune
- 🗺️ **Cartographie interactive** des transactions
- 🔍 **Détection d'opportunités d'investissement** via Isolation Forest
- 📈 **Recherche de biens similaires** avec scoring de similarité
- 👤 **Authentification utilisateur** avec historique et recommandations personnalisées
- 🗄️ **Base de données MongoDB** pour une architecture Big Data scalable

L'application s'appuie sur des algorithmes de Machine Learning avancés (K-Means, HDBSCAN, Isolation Forest) pour segmenter le marché et identifier les patterns de prix. Elle intègre désormais une couche Big Data avec MongoDB et un moteur de recommandations personnalisées.

---

## 🏗️ Architecture du projet

```
clustering_immo_app/
│
├── app.py                    # Application Flask principale (routes et API)
├── prepare_models.py         # Pipeline ETL et entraînement des modèles ML
├── analyze_clusters.py       # Script d'analyse des clusters K-Means
├── pyproject.toml           # Configuration des dépendances (uv/pip)
│
├── models/                  # Modèles ML et données sérialisées (générés)
│   ├── df_reference.pkl     # Dataset enrichi avec clusters (302K lignes)
│   ├── df_communes.pkl      # Statistiques agrégées par commune
│   ├── kmeans_model.pkl     # Modèle K-Means (6 clusters)
│   └── scaler.pkl           # StandardScaler pour normalisation
│
├── utils/                   # Modules utilitaires
│   ├── __init__.py          # Exports des classes principales
│   ├── data_loader.py       # DataManager (chargement et recherche)
│   ├── clustering.py        # Fonctions d'analyse des clusters
│   ├── predictor.py         # PriceEstimator (estimation de prix)
│   ├── opportunities.py     # Isolation Forest (détection anomalies)
│   ├── db.py                # Connexion et collections MongoDB
│   ├── auth.py              # Authentification (inscription/connexion)
│   └── recommendations.py  # Moteur de recommandations personnalisées
│
├── templates/               # Templates HTML (Jinja2)
│   ├── base.html            # Layout de base (navigation)
│   ├── index.html           # Page d'accueil
│   ├── estimation.html      # Onglet 1 : Estimation de bien
│   ├── analyse_marche.html  # Onglet 2 : Analyse de marché
│   ├── cartographie.html    # Onglet 3 : Carte interactive
│   ├── similaires.html      # Onglet 4 : Biens similaires
│   ├── opportunites.html    # Onglet 5 : Détection d'opportunités
│   ├── clusters.html        # Profils des 6 clusters
│   ├── login.html           # Page de connexion
│   ├── register.html        # Page d'inscription
│   └── profile.html         # Profil utilisateur + recommandations
│
└── static/                  # Assets frontend
    ├── css/
    │   └── style.css        # Styles Tailwind CSS personnalisés
    └── js/                  # Logique JavaScript par onglet
        ├── estimation.js
        ├── analyse_marche.js
        ├── cartographie.js
        ├── similaires.js
        └── opportunites.js
```

---

## 📦 Pipeline de traitement des données

Le script `prepare_models.py` exécute un **pipeline ETL complet** avant le lancement de l'application.

### 1️⃣ Extraction des données (ETL)

**Source** : [geo-dvf (data.gouv.fr)](https://files.data.gouv.fr/geo-dvf/latest/csv/2024/full.csv.gz)

```python
def extract_apartment_sales(year: int = 2024) -> pd.DataFrame
```

**Processus** :
- ⬇️ **Téléchargement** du fichier DVF 2024 complet (6M+ lignes)
- 🔍 **Filtrage métier** :
  - Nature mutation = `Vente`
  - Type local = `Appartement`
  - Localisation = France métropolitaine (exclusion DOM-TOM)
  - Coordonnées GPS valides (`latitude` et `longitude` non nulles)
  - Surface terrain = `0` (pour isoler les appartements sans terrain)
- 🧹 **Dédoublonnage** : Suppression des duplicatas sur `id_mutation` + champs clés
- ∑ **Agrégation** : Regroupement par mutation (certaines mutations = plusieurs lignes)
- 🎯 **Projection** : Sélection de 7 colonnes cibles :
  - `id_mutation`, `valeur_fonciere`, `surface_reelle_bati`, `nombre_pieces_principales`, `code_commune`, `latitude`, `longitude`

**Résultat** : ~450,000 ventes d'appartements

---

### 2️⃣ Nettoyage des valeurs aberrantes

```python
def remove_statistical_outliers(df: pd.DataFrame) -> pd.DataFrame
```

**Méthode** : Filtrage par **quantiles** pour supprimer les valeurs extrêmes :
- `surface_reelle_bati` : conservation du P1-P99 (1er au 99e percentile)
- `valeur_fonciere` : conservation du P1-P99
- `nombre_pieces_principales` : conservation du P1-P99.9

**Impact** : ~148,000 lignes supprimées (~33% des données brutes) pour garantir la qualité

**Dataset final** : **~302,000 transactions** propres et exploitables

---

### 3️⃣ Feature Engineering

```python
def add_features(df: pd.DataFrame) -> pd.DataFrame
```

**Nouvelles variables créées** :

#### 📐 Variables numériques

- **`prix_m2`** : `valeur_fonciere / surface_reelle_bati`
- **`marche_prix_m2_median`** : Prix médian au m² par commune (contexte local)

#### 🗺️ Catégorisation géographique

Variable **`categorie_geo`** (4 segments) :

| Catégorie | Description | Exemples |
|-----------|-------------|----------|
| `1_Metropole_Top15` | Paris + 14 grandes métropoles (Lyon, Marseille, Bordeaux...) | Paris 75001-75020, Lyon 69001-69009, Marseille 13001-13016 |
| `2_Ile_de_France` | Départements IDF hors Paris | 92 (Hauts-de-Seine), 93, 94, 77, 78, 91, 95 |
| `3_Zone_Touristique` | Départements attractifs/tension | 06 (Alpes-Maritimes), 33 (Gironde), 83 (Var), 74, 69, 44, 34 |
| `4_Province_Standard` | Reste du territoire | Tous les autres départements |

#### ⭐ Standing relatif

Variable **`standing_relative`** (5 niveaux) basée sur le ratio `prix_m2 / marche_prix_m2_median` :

| Standing | Ratio | Signification |
|----------|-------|---------------|
| `1_Decote_Travaux` | < 0.70 | -30% sous le marché local (potentiel travaux) |
| `2_Bonne_Affaire` | 0.70 - 0.90 | -10 à -30% sous le marché |
| `3_Standard_Marche` | 0.90 - 1.15 | ±15% du marché (prix normal) |
| `4_Premium` | 1.15 - 1.40 | +15 à +40% au-dessus du marché |
| `5_Prestige_Exception` | > 1.40 | +40% et plus (luxe, vue exceptionnelle, etc.) |

---

### 4️⃣ Entraînement des modèles Machine Learning

```python
def train_models(df: pd.DataFrame, models_dir: Path)
```

#### A. Préparation des données

**Features sélectionnées** (5 dimensions) :
- `surface_reelle_bati` : Taille du bien
- `nombre_pieces_principales` : Typologie (T1, T2, T3...)
- `latitude`, `longitude` : Localisation géographique
- `prix_m2` : Niveau de prix

**Échantillonnage** : 50,000 biens pour l'entraînement (optimisation des performances)

**Normalisation** : `StandardScaler` (moyenne=0, écart-type=1) pour harmoniser les échelles

#### B. Clustering K-Means

**Algorithme** : K-Means avec **k=6 clusters** (choix optimal après analyse)

**Paramètres** :
- `n_clusters=6` : 6 segments de marché distincts
- `random_state=42` : Reproductibilité
- `n_init='auto'` : Optimisation automatique

**Application** : Prédiction sur l'intégralité des 302,000 biens → Colonne `cluster_kmeans`

#### C. Statistiques par commune

Agrégation des **métriques clés par commune** :
- Prix médian/moyen au m²
- Surface moyenne
- Prix moyen
- Catégorie géographique dominante
- Nombre de transactions

**Résultat** : ~13,000 communes référencées

#### D. Sauvegarde

4 fichiers Pickle générés dans `models/` :
- `df_reference.pkl` : Dataset complet avec clusters
- `kmeans_model.pkl` : Modèle K-Means entraîné
- `scaler.pkl` : Scaler pour nouvelles prédictions
- `df_communes.pkl` : Statistiques communales

---

## 🤖 Machine Learning et Clustering

### Les 6 Clusters K-Means (Segments de marché)

Analyse des **302,016 transactions** DVF 2024 :

| Cluster | Nom | Description | Caractéristiques clés | % du marché |
|---------|-----|-------------|----------------------|-------------|
| **0** | Petits Appartements Province Sud | T1-T2 en PACA/Occitanie | 37m², 3,700€/m², 134K€ | **22.1%** (66,626 biens) |
| **1** | Appartements Premium Paris/IDF | T2 parisiens haut de gamme | 43m², 9,900€/m², 425K€ | **9.5%** (28,725 biens) |
| **2** | Appartements Familiaux IDF Périphérie | T3-T4 banlieue IDF | 70m², 3,100€/m², 218K€ | **19.5%** (58,780 biens) |
| **3** | Appartements Standard Province | T3-T4 grandes villes | 70m², 2,900€/m², 202K€ | **21.8%** (65,836 biens) |
| **4** | Grandes Maisons Familiales | T4-T5+ dispersés | 111m², 2,960€/m², 329K€ | **7.4%** (22,388 biens) |
| **5** | Studios/T2 Province Dynamique | Petits biens métropoles | 38m², 3,470€/m², 129K€ | **19.8%** (59,661 biens) |

**Utilité** :
- 🎯 Affiner les estimations en comparant aux biens du même cluster
- 📊 Identifier les typologies de marché dominantes par zone
- 💡 Comprendre le positionnement d'un bien dans son segment

---

### Isolation Forest (Détection d'anomalies)

**Objectif** : Identifier les biens **sous-évalués** (opportunités d'investissement)

**Fonctionnement** :

```python
def fit_isolation_forest(df, contamination=0.02)
```

1. **Features d'entrée** :
   - `surface_reelle_bati`
   - `nombre_pieces_principales`
   - `prix_m2`
   - `marche_prix_m2_median`
   - `ratio_prix_marche` (prix_m2 / prix_marché_local)

2. **Algorithme** :
   - `IsolationForest` avec 500 arbres
   - `contamination=0.02` (2% d'anomalies attendues)
   - `random_state=42` (reproductibilité)

3. **Scoring multi-critères** :
   ```python
   investment_score = (
       45% × score_decote +        # Décote vs marché
       20% × score_surface +        # Qualité surface (pénalise < 25m² ou > 200m²)
       20% × score_zone +           # Attractivité zone (Métropole > Tourisme > IDF > Province)
       15% × score_anomalie         # Degré d'anomalie détecté
   )
   ```

4. **Filtres** :
   - `anomaly_label == -1` (identifié comme anomalie)
   - `ratio_prix_marche < max_ratio` (par défaut 0.85 = -15% de décote minimum)

**Résultat** : Liste des **Top 50 opportunités** avec score d'investissement (0-100)

---

## 🎨 Fonctionnalités de l'application

L'application web propose **5 onglets interactifs** :

### 1️⃣ Estimation de bien

**URL** : `/estimation`

**Fonction** : Estimer le prix d'un appartement en temps réel

**Inputs** :
- Surface (m²)
- Nombre de pièces
- Code commune (ex: 75001, 69001)

**Algorithme** :
```python
class PriceEstimator:
    def estimate_price(surface, nb_pieces, code_commune) -> Dict
```

1. Récupération du prix médian au m² de la commune
2. Ajustement selon le nombre de pièces :
   - T4+ → -5% (grands apparts moins chers au m²)
   - Studios/T1 → +5% (prime aux petites surfaces)
3. Calcul : `prix_estime = surface × prix_m2_ajusté`
4. Fourchette : ±15% autour de l'estimation
5. Détermination du standing (ratio vs marché local)
6. Assignation au cluster K-Means le plus proche

**Outputs** :
- Prix estimé + fourchette (min/max)
- Prix au m²
- Standing relatif (Décote → Prestige)
- Statistiques de la commune (nb transactions, prix moyen...)
- Cluster d'appartenance avec comparatifs

---

### 2️⃣ Analyse de marché

**URL** : `/analyse-marche`

**Fonction** : Analyse approfondie d'un département

**Input** : Code département (01-95)

**API** : `/api/analyse-departement/<code_dept>`

**Métriques calculées** :
- 📊 Nombre de transactions (volume du marché)
- 💰 Prix médian/moyen au m²
- 📈 Quartiles Q25/Q75 (dispersion des prix)
- 🏠 Surface moyenne
- 🏙️ Nombre de communes couvertes
- ⭐ Répartition par standing (% Décote, Bonne affaire, Standard, Premium, Prestige)
- 🗺️ Catégorie géographique dominante

**Bonus** : Top 10 communes les plus actives du département (tri par nb de transactions)

---

### 3️⃣ Cartographie interactive

**URL** : `/cartographie`

**Fonction** : Visualisation géographique des transactions

**API** : `/api/map-data`

**Données affichées** :
- Échantillon de 5,000 biens (optimisation performances)
- Latitude/Longitude de chaque transaction
- Prix au m² (pour gradient de couleur)
- Cluster K-Means (pour segmentation visuelle)
- Code commune (infobulles)

**Technologies** :
- Frontend : Leaflet.js ou Mapbox
- Marqueurs colorés par cluster ou prix
- Interaction : zoom, filtres, infobulles

---

### 4️⃣ Biens similaires

**URL** : `/similaires`

**Fonction** : Trouver des comparables dans le marché

**Inputs** :
- Surface (m²)
- Nombre de pièces
- Code commune

**Algorithme** :
```python
class PriceEstimator:
    def find_similar_properties(surface, nb_pieces, code_commune) -> DataFrame
```

**Critères de similarité** :
1. **Zone** : Même département (code commune[:2])
2. **Surface** : ±30% (`surface × 0.7` à `surface × 1.3`)
3. **Typologie** : ±1 pièce (`nb_pieces - 1` à `nb_pieces + 1`)
4. **Score** : Distance normalisée sur surface + écart de pièces

**Output** : Top 10 biens similaires avec détails (prix, localisation, standing...)

---

### 5️⃣ Détection d'opportunités

**URL** : `/opportunites`

**Fonction** : Identifier les meilleures affaires d'investissement

**Inputs** :
- `contamination` : Taux d'anomalies (0.01-0.10, défaut 0.02)
- `max_ratio` : Décote maximale acceptée (ex: 0.85 = -15%)
- `zone_filter` : Filtre géographique optionnel (Métropole, IDF, Tourisme, Province)

**API** : `/api/opportunities` (POST)

**Processus** :
1. Application d'Isolation Forest sur tout le dataset
2. Filtrage des anomalies avec ratio < max_ratio
3. Calcul du score d'investissement multi-critères
4. Tri par score décroissant
5. Retour des Top 50 opportunités

**Output** :
- Liste des opportunités avec :
  - Score d'investissement (0-100)
  - Décote en % (ex: -22%)
  - Prix, surface, pièces
  - Localisation (lat/long + commune)
  - Standing + zone géographique
- Statistiques globales :
  - Décote médiane
  - Prix/m² médian
  - Distribution des scores
  - Répartition par zone

---

---

## 👤 Authentification et recommandations

### Système utilisateur

L'application intègre un système complet de gestion des utilisateurs basé sur **Flask-Login** et **MongoDB** :

- **Inscription** (`/register`) : Création de compte avec validation et hashage du mot de passe (bcrypt)
- **Connexion** (`/login`) : Authentification sécurisée avec gestion de session
- **Profil** (`/profile`) : Tableau de bord personnel avec historique et recommandations

### Historique des recherches

Chaque recherche effectuée par un utilisateur connecté est automatiquement sauvegardée en MongoDB (collection `search_sessions`) avec le type, les paramètres et la date.

### Moteur de recommandations

Le moteur analyse l'historique de l'utilisateur pour construire un profil implicite :
- Zones et départements les plus recherchés
- Budget moyen estimé
- Surface typique recherchée

Il génère ensuite des suggestions de communes cohérentes avec ces préférences, actualisables depuis la page profil.

### Collections MongoDB

| Collection | Contenu |
|------------|---------|
| `properties` | Données immobilières DVF |
| `communes` | Statistiques agrégées par commune |
| `users` | Comptes utilisateurs |
| `search_sessions` | Historique des recherches |
| `recommendations` | Suggestions personnalisées |

### Nouvelles routes

| Endpoint | Méthode | Auth | Description |
|----------|---------|------|-------------|
| `/register` | GET/POST | Non | Inscription |
| `/login` | GET/POST | Non | Connexion |
| `/logout` | GET | Oui | Déconnexion |
| `/profile` | GET | Oui | Profil utilisateur |
| `/api/profile/preferences` | POST | Oui | Mise à jour préférences |
| `/api/recommendations/refresh` | POST | Oui | Actualisation recommandations |

## 💻 Installation

### Prérequis

- **Python 3.10+**
- **MongoDB 8.2+** (service démarré : `net start MongoDB`)
- **pip** ou **uv** (gestionnaire de paquets)

### Étapes

1. **Cloner le projet** :
   ```bash
   git clone <votre-repo>
   cd clustering_immo_app
   ```

2. **Installer les dépendances** :
   ```bash
   pip install flask pandas numpy scikit-learn matplotlib seaborn plotly hdbscan scipy requests pymongo flask-login flask-bcrypt
   ```

3. **Préparer les données et modèles** (obligatoire avant le premier lancement) :
   ```bash
   uv run python prepare_models.py
   ```
   
   **Durée** : ~5-10 minutes (téléchargement + traitement)
   
   **Ce script va** :
   - ⬇️ Télécharger DVF 2024 (6M+ lignes)
   - 🧹 Nettoyer et filtrer (→ 302K appartements)
   - 🛠️ Enrichir les données (prix_m2, standing, catégories...)
   - 🤖 Entraîner le K-Means (6 clusters)
   - 💾 Sauvegarder dans `models/` (4 fichiers .pkl)

4. **(Optionnel) Analyser les clusters** :
   ```bash
   uv run python analyze_clusters.py
   ```
   
   Affiche les statistiques détaillées des 6 clusters (prix, surface, zones...).

---

## 🚀 Utilisation

### Lancer l'application

```bash
uv run python app.py
```

**Serveur** : http://localhost:5000

**Debug mode** : Activé par défaut (recharge automatique sur modification)

### Navigation

1. **Page d'accueil** (`/`) : Présentation + liens vers les 5 onglets
2. **Estimation** (`/estimation`) : Formulaire d'estimation
3. **Analyse marché** (`/analyse-marche`) : Sélecteur de département
4. **Cartographie** (`/cartographie`) : Carte interactive Leaflet
5. **Biens similaires** (`/similaires`) : Recherche de comparables
6. **Opportunités** (`/opportunites`) : Détection Isolation Forest

### API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/estimate` | POST | Estimation de prix |
| `/api/analyse-departement/<code>` | GET | Stats département |
| `/api/top-communes/<code>` | GET | Top 10 communes |
| `/api/cluster-info/<id>` | GET | Détails cluster |
| `/api/map-data` | GET | Données cartographie |
| `/api/find-similar` | POST | Biens similaires |
| `/api/opportunities` | POST | Détection opportunités |
| `/api/search-communes` | GET | Recherche communes |
| `/api/departements` | GET | Liste départements |

---

## 🛠️ Technologies utilisées

### Backend

- **Flask 3.0.0** : Framework web léger
- **Flask-Login** : Gestion des sessions utilisateurs
- **Flask-Bcrypt** : Hashage sécurisé des mots de passe
- **MongoDB 8.2** : Base de données NoSQL orientée documents
- **PyMongo** : Driver Python pour MongoDB
- **pandas 2.0+** : Manipulation de données
- **NumPy 1.24+** : Calculs numériques
- **scikit-learn 1.3+** : Machine Learning (K-Means, Isolation Forest, StandardScaler)
- **HDBSCAN 0.8.33** : Clustering hiérarchique (alternatif, non utilisé en prod)
- **requests 2.31+** : Téléchargement DVF

### Frontend

- **Tailwind CSS** : Framework CSS utility-first
- **JavaScript (Vanilla)** : Logique interactive par onglet
- **Jinja2** : Moteur de templates Flask
- **Font Awesome** : Icônes
- **Leaflet.js / Mapbox** : Cartographie interactive

### Data Science

- **Source** : [DVF (Demande de Valeurs Foncières)](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres/) - data.gouv.fr
- **Volume** : 302,016 transactions d'appartements (année 2024, France métropolitaine)
- **Algorithmes** :
  - **K-Means** (clustering segmentation marché)
  - **Isolation Forest** (détection anomalies)
  - **StandardScaler** (normalisation features)

---

## 📊 Résultats et performances

### Clustering K-Means

- **Métrique Silhouette** : 0.260 (séparation modérée, typique pour des données géospatiales complexes)
- **Davies-Bouldin** : 1.251 (valeurs < 1.5 considérées bonnes)
- **Calinski-Harabasz** : 3220 (densité et séparation satisfaisantes)
- **Interprétabilité** : 6 segments métier clairement identifiables et exploitables
- **Choix k=6** : Optimisé pour k=6 clusters après analyse comparative (vs k=5 et HDBSCAN)

### Pipeline ETL

- **Temps d'exécution** : ~5-10 minutes (selon connexion)
- **Taux de conservation** : 67% après nettoyage (302K / 450K)
- **Mémoire** : ~500 MB pour le dataset complet

### Application Web

- **Temps de réponse API** : < 100ms (estimation/analyse)
- **Chargement initial** : ~3-5 secondes (lecture 4 fichiers .pkl)
- **Concurrence** : Support multi-utilisateurs (Flask production avec Gunicorn)

---

## 📝 Améliorations futures

- [ ] **API REST complète** : Documentation OpenAPI/Swagger
- [x] **Authentification** : Comptes utilisateurs + historique des recherches
- [ ] **Modèles avancés** : XGBoost/LightGBM pour estimation de prix
- [ ] **Prédictions temporelles** : Forecasting des prix (ARIMA, Prophet)
- [ ] **Export PDF** : Génération de rapports d'analyse
- [ ] **Cache Redis** : Optimisation des requêtes récurrentes
- [ ] **Docker** : Containerisation pour déploiement facile
- [ ] **Dashboard admin** : Monitoring des modèles + ré-entraînement

---

## 📄 Licence

MIT License - Libre d'utilisation et modification

---

## 👨‍💻 Auteurs

**Raphael Calhegas** - **Emma Feneau**  
Projet d'analyse immobilière IA - BIG DATA *(CY TECH - ING3 FINTECH - 2026)*

---

## 🙏 Remerciements

- **Enseignants** : Bruno Ixsil et Julien Savry
- **data.gouv.fr** : Mise à disposition des données DVF

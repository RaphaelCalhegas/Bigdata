"""
Script de préparation des données et entraînement des modèles.
Ce script doit être exécuté AVANT de lancer l'application Flask.

Usage:
    python prepare_models.py
"""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

import sys
sys.path.insert(0, str(Path(__file__).parent))


def extract_apartment_sales(year: int = 2025) -> pd.DataFrame:
    """
    Pipeline ETL pour les transactions immobilières DVF.
    Télécharge et filtre les ventes d'appartements depuis geo-dvf.
    """
    URL = f"https://files.data.gouv.fr/geo-dvf/latest/csv/{year}/full.csv.gz"

    TARGET_SCHEMA = {
        'id_mutation': 'object',
        'valeur_fonciere': 'float32',
        'surface_reelle_bati': 'float32',
        'nombre_pieces_principales': 'float32',
        'code_commune': 'object',
        'latitude': 'float32',
        'longitude': 'float32'
    }

    print(f"[ETL] Téléchargement DVF {year}...")
    print(f"[ETL] URL : {URL}")

    try:
        df = pd.read_csv(URL, compression='gzip', low_memory=False)
    except Exception as e:
        print(f"[ETL] Erreur critique : {e}")
        return pd.DataFrame()

    print(f"[ETL] Volume brut : {len(df):,} lignes.")

    # Filtrage métier
    print("[ETL] Application des filtres...")

    is_vente      = df['nature_mutation'] == 'Vente'
    is_appart     = df['type_local'] == 'Appartement'
    is_metropole  = ~df['code_departement'].astype(str).str.startswith('97', na=False)
    has_gps       = df['latitude'].notna() & df['longitude'].notna()

    terrain_clean    = pd.to_numeric(df['surface_terrain'], errors='coerce').fillna(0)
    is_terrain_zero  = (terrain_clean == 0)

    df = df.loc[is_vente & is_appart & is_metropole & has_gps & is_terrain_zero].copy()

    if df.empty:
        print("[ETL] Aucun enregistrement conservé après filtrage.")
        return df

    print(f"[ETL] Lignes conservées : {len(df):,}")

    # Dédoublonnage
    cols_doublons = [
        col for col in [
            "id_mutation", "valeur_fonciere", "type_local",
            "surface_reelle_bati", "id_parcelle",
            "lot1_numero", "adresse_numero", "adresse_nom_voie"
        ] if col in df.columns
    ]

    df.drop_duplicates(subset=cols_doublons, keep='first', inplace=True)
    print(f"[ETL] Après dédoublonnage : {len(df):,} lignes.")

    # Projection
    available_cols = [c for c in TARGET_SCHEMA.keys() if c in df.columns]
    df = df[available_cols]

    # Agrégation par mutation
    print("[ETL] Agrégation des mutations...")

    agg_rules = {col: 'first' for col in available_cols if col != 'id_mutation'}
    if 'surface_reelle_bati' in agg_rules:
        agg_rules['surface_reelle_bati'] = 'sum'

    df_final = df.groupby('id_mutation').agg(agg_rules).reset_index()

    # Casting des types
    print("[ETL] Conversion des types...")

    for col, dtype in TARGET_SCHEMA.items():
        if col in df_final.columns:
            try:
                if 'float' in dtype:
                    df_final[col] = pd.to_numeric(df_final[col], errors='coerce').astype(dtype)
                else:
                    df_final[col] = df_final[col].astype(dtype)
            except Exception as e:
                print(f"[ETL] Erreur typage {col} : {e}")

    final_cols_ordered = [c for c in TARGET_SCHEMA.keys() if c in df_final.columns]
    df_final = df_final[final_cols_ordered]

    print(f"[ETL] Terminé : {len(df_final):,} ventes uniques exportées.")
    return df_final


def remove_statistical_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Supprime les valeurs aberrantes par filtrage quantile.
    """
    print("[OUTLIERS] Filtrage statistique...")

    df_out      = df.copy()
    initial_len = len(df_out)

    cols_config = {
        'surface_reelle_bati':      (0.01, 0.99),
        'valeur_fonciere':           (0.01, 0.99),
        'nombre_pieces_principales': (0.01, 0.999)
    }

    for col, (q_min, q_max) in cols_config.items():
        if col not in df_out.columns:
            continue

        df_out[col] = pd.to_numeric(df_out[col], errors='coerce')

        low_bound  = df_out[col].quantile(q_min)
        high_bound = df_out[col].quantile(q_max)

        mask       = (df_out[col] >= low_bound) & (df_out[col] <= high_bound)
        nb_removed = len(df_out) - mask.sum()

        print(f"[OUTLIERS] {col:<30} : {nb_removed} lignes supprimées")

        df_out = df_out[mask]

    final_len = len(df_out)
    loss_pct  = ((initial_len - final_len) / initial_len) * 100

    print(f"[OUTLIERS] Lignes : {initial_len:,} -> {final_len:,} (perte : {loss_pct:.2f}%)")

    return df_out


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Feature engineering : prix au m², catégorie géographique, standing relatif.
    """
    print("[FEATURES] Enrichissement des données...")

    # Prix au m²
    df['prix_m2'] = df['valeur_fonciere'] / df['surface_reelle_bati']
    df['prix_m2'] = df['prix_m2'].replace([np.inf, -np.inf], np.nan)
    df.dropna(subset=['prix_m2'], inplace=True)

    # Prix médian du marché local par commune
    df['marche_prix_m2_median'] = df.groupby('code_commune')['prix_m2'].transform('median')

    # Catégorie géographique
    df['dept'] = df['code_commune'].astype(str).str[:2]

    depts_idf      = ['75', '92', '93', '94', '77', '78', '91', '95']
    depts_tourisme = ['06', '13', '33', '83', '74', '69', '44', '34', '2A', '2B', '64', '35', '17']
    top_villes     = ['31555', '06088', '44109', '67482', '34172', '33063', '59350', '35238']

    is_metropole = (
        df['code_commune'].isin(top_villes) |
        df['code_commune'].str.startswith('751') |
        df['code_commune'].str.startswith('693') |
        df['code_commune'].str.startswith('132')
    )
    is_idf      = df['dept'].isin(depts_idf)
    is_tourisme = df['dept'].isin(depts_tourisme)

    df['categorie_geo'] = np.select(
        [is_metropole, is_idf, is_tourisme],
        ['1_Metropole_Top15', '2_Ile_de_France', '3_Zone_Touristique'],
        default='4_Province_Standard'
    )
    df.drop(columns=['dept'], inplace=True)

    # Standing relatif
    ratio = df['prix_m2'] / df['marche_prix_m2_median']

    df['standing_relative'] = np.select(
        [
            ratio < 0.70,
            (ratio >= 0.70) & (ratio < 0.90),
            (ratio >= 0.90) & (ratio < 1.15),
            (ratio >= 1.15) & (ratio < 1.40),
            ratio >= 1.40
        ],
        [
            '1_Decote_Travaux',
            '2_Bonne_Affaire',
            '3_Standard_Marche',
            '4_Premium',
            '5_Prestige_Exception'
        ],
        default='3_Standard_Marche'
    )

    print(f"[FEATURES] Terminé : {df.shape[1]} colonnes.")
    return df


def train_models(df: pd.DataFrame, models_dir: Path):
    """
    Entraîne le scaler et le modèle K-Means, calcule les stats par commune,
    puis sauvegarde les 4 fichiers pkl dans models_dir.
    """
    print("[MODELS] Entraînement des modèles...")

    features = [
        'surface_reelle_bati', 'nombre_pieces_principales',
        'latitude', 'longitude', 'prix_m2'
    ]

    df_features = df[features].copy()

    # Échantillonnage pour l'entraînement
    sample_size = min(50000, len(df))
    df_sample   = df_features.sample(sample_size, random_state=42)

    # Standardisation
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(df_sample)

    # K-Means (k=6)
    print("[MODELS] Entraînement K-Means (k=6)...")
    kmeans = KMeans(n_clusters=6, random_state=42, n_init='auto')
    kmeans.fit(X_scaled)

    # Prédiction sur le dataset complet
    X_full_scaled    = scaler.transform(df_features)
    df['cluster_kmeans'] = kmeans.predict(X_full_scaled)

    # Statistiques par commune
    print("[MODELS] Calcul des statistiques par commune...")
    df_communes = df.groupby('code_commune').agg({
        'prix_m2':            ['median', 'mean'],
        'surface_reelle_bati': 'mean',
        'valeur_fonciere':     'mean',
        'categorie_geo':       lambda x: x.mode()[0] if len(x.mode()) > 0 else 'N/A',
        'code_commune':        'count'
    })
    df_communes.columns = ['prix_m2_median', 'prix_m2_mean', 'surface_mean',
                           'prix_mean', 'categorie_geo', 'count']

    # Sauvegarde
    print(f"[MODELS] Sauvegarde dans {models_dir}...")

    with open(models_dir / 'scaler.pkl', 'wb') as f:
        pickle.dump(scaler, f)

    with open(models_dir / 'kmeans_model.pkl', 'wb') as f:
        pickle.dump(kmeans, f)

    with open(models_dir / 'df_reference.pkl', 'wb') as f:
        pickle.dump(df, f)

    with open(models_dir / 'df_communes.pkl', 'wb') as f:
        pickle.dump(df_communes, f)

    print(f"[MODELS] Terminé — dataset : {len(df):,} lignes, communes : {len(df_communes):,}")


def main():
    """Pipeline principal : extraction, nettoyage, features, modèles."""
    print("=" * 60)
    print("PREPARATION DES DONNEES - IMMO PRO")
    print("=" * 60)

    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)

    # 1. Extraction
    df = extract_apartment_sales(2025)

    if df.empty:
        print("[MAIN] Impossible de continuer sans données.")
        return

    # 2. Nettoyage
    df_clean = remove_statistical_outliers(df)

    # 3. Feature engineering
    df_enrichi = add_features(df_clean)

    # 4. Entraînement et sauvegarde
    train_models(df_enrichi, models_dir)

    print("=" * 60)
    print("PREPARATION TERMINEE")
    print("=" * 60)
    print("\nPour lancer l'application :")
    print("   python app.py\n")


if __name__ == "__main__":
    main()
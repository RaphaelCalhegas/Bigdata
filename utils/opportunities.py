"""
Module de détection d'opportunités d'investissement via Isolation Forest.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def fit_isolation_forest(df, contamination=0.02):
    """
    Applique Isolation Forest pour détecter les anomalies de prix.
    
    Args:
        df: DataFrame avec les colonnes nécessaires
        contamination: Taux d'anomalies attendu (0.01 à 0.05)
    
    Returns:
        DataFrame enrichi avec anomaly_label et anomaly_score
    """
    df_out = df.copy()
    
    # Feature clé: ratio prix vs marché local
    df_out['ratio_prix_marche'] = df_out['prix_m2'] / df_out['marche_prix_m2_median']
    df_out.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Colonnes pour la détection
    feature_cols = [
        'surface_reelle_bati',
        'nombre_pieces_principales',
        'prix_m2',
        'marche_prix_m2_median',
        'ratio_prix_marche'
    ]
    
    # Filtrage des lignes valides
    mask = df_out[feature_cols].notna().all(axis=1)
    X = df_out.loc[mask, feature_cols].astype('float32')
    
    # Standardisation
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Modèle
    model = IsolationForest(
        n_estimators=500,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_scaled)
    
    # Prédictions
    df_out.loc[mask, 'anomaly_label'] = model.predict(X_scaled)
    df_out.loc[mask, 'anomaly_score'] = model.score_samples(X_scaled)
    
    return df_out


def score_decote(ratio):
    """Score basé sur la décote (0-100)."""
    if ratio < 0.30:
        ratio = 0.30
    return (1 - ratio) * 100


def score_surface(surface):
    """Score basé sur la surface (pénalise les extrêmes)."""
    if surface < 25 or surface > 200:
        return 30
    return 100 - abs(surface - 90)


def score_zone(cat):
    """Score basé sur la catégorie géographique."""
    return {
        '1_Metropole_Top15': 100,
        '3_Zone_Touristique': 95,
        '2_Ile_de_France': 90,
        '4_Province_Standard': 80
    }.get(cat, 75)


def compute_investment_score(df):
    """
    Calcule un score d'investissement multi-critères.
    
    Pondération:
    - 45% Décote vs marché
    - 20% Qualité surface
    - 20% Attractivité zone
    - 15% Score anomalie
    """
    df = df.copy()
    
    # Scores individuels
    df['score_decote'] = df['ratio_prix_marche'].apply(score_decote)
    df['score_surface'] = df['surface_reelle_bati'].apply(score_surface)
    df['score_zone'] = df['categorie_geo'].apply(score_zone)
    
    # Score anomalie normalisé
    s_min, s_max = df['anomaly_score'].min(), df['anomaly_score'].max()
    df['score_anomaly'] = ((s_max - df['anomaly_score']) / (s_max - s_min)) * 100
    
    # Score final pondéré
    df['investment_score'] = (
        0.45 * df['score_decote'] +
        0.20 * df['score_surface'] +
        0.20 * df['score_zone'] +
        0.15 * df['score_anomaly']
    )
    
    return df


def detect_opportunities(df_reference, contamination=0.02, max_ratio=0.85, zone_filter='all', top_n=50):
    """
    Pipeline complet de détection d'opportunités.
    
    Args:
        df_reference: DataFrame de référence
        contamination: Taux d'anomalies
        max_ratio: Ratio max accepté (ex: 0.85 = -15% décote)
        zone_filter: Filtre géographique ('all' ou code zone)
        top_n: Nombre d'opportunités à retourner
    
    Returns:
        dict avec statistiques et opportunités
    """
    # 1. Application Isolation Forest
    df_if = fit_isolation_forest(df_reference, contamination)
    
    # 2. Filtrage des candidats
    candidates = df_if[
        (df_if['anomaly_label'] == -1) &
        (df_if['ratio_prix_marche'] < max_ratio)
    ].copy()
    
    # Filtre zone si demandé
    if zone_filter != 'all':
        candidates = candidates[candidates['categorie_geo'] == zone_filter]
    
    if len(candidates) == 0:
        return {
            'success': True,
            'nb_opportunities': 0,
            'opportunities': [],
            'median_decote': 0,
            'median_prix_m2': 0,
            'median_surface': 0,
            'score_bins': {'labels': [], 'counts': []},
            'zone_distribution': {'labels': [], 'counts': []}
        }
    
    # 3. Calcul des scores
    ranked = compute_investment_score(candidates)
    
    # 4. Top opportunités
    top_opps = ranked.nlargest(top_n, 'investment_score')
    
    # 5. Statistiques
    median_ratio = ranked['ratio_prix_marche'].median()
    median_decote = round((1 - median_ratio) * 100, 1)
    
    # 6. Distribution des scores (bins)
    score_bins = pd.cut(ranked['investment_score'], bins=10)
    score_counts = score_bins.value_counts().sort_index()
    
    # 7. Répartition par zone
    zone_dist = ranked['categorie_geo'].value_counts()
    
    # 8. Préparation des opportunités pour JSON (Conversion explicite numpy -> Python)
    opportunities = []
    for _, row in top_opps.iterrows():
        # Conversion explicite de tous les types numpy en types Python natifs
        investment_score = row['investment_score']
        ratio = row['ratio_prix_marche']
        
        opportunities.append({
            'investment_score': float(investment_score.item() if hasattr(investment_score, 'item') else investment_score),
            'decote_pct': float(round((1 - (ratio.item() if hasattr(ratio, 'item') else ratio)) * 100, 1)),
            'valeur_fonciere': float(row['valeur_fonciere'].item() if hasattr(row['valeur_fonciere'], 'item') else row['valeur_fonciere']),
            'prix_m2': float(row['prix_m2'].item() if hasattr(row['prix_m2'], 'item') else row['prix_m2']),
            'marche_prix_m2_median': float(row['marche_prix_m2_median'].item() if hasattr(row['marche_prix_m2_median'], 'item') else row['marche_prix_m2_median']),
            'surface_reelle_bati': float(row['surface_reelle_bati'].item() if hasattr(row['surface_reelle_bati'], 'item') else row['surface_reelle_bati']),
            'nombre_pieces_principales': float(row['nombre_pieces_principales'].item() if hasattr(row['nombre_pieces_principales'], 'item') else row['nombre_pieces_principales']),
            'categorie_geo': str(row['categorie_geo']),
            'standing_relative': str(row['standing_relative']),
            'latitude': float(row['latitude'].item() if hasattr(row['latitude'], 'item') else row['latitude']),
            'longitude': float(row['longitude'].item() if hasattr(row['longitude'], 'item') else row['longitude'])
        })
    
    # Conversion explicite des statistiques numpy -> Python
    median_prix = ranked['prix_m2'].median()
    median_surf = ranked['surface_reelle_bati'].median()
    
    return {
        'success': True,
        'nb_opportunities': int(len(ranked)),
        'opportunities': opportunities,
        'median_decote': float(median_decote),
        'median_prix_m2': float(median_prix.item() if hasattr(median_prix, 'item') else median_prix),
        'median_surface': float(median_surf.item() if hasattr(median_surf, 'item') else median_surf),
        'score_bins': {
            'labels': [f"{int(interval.left)}-{int(interval.right)}" for interval in score_counts.index],
            'counts': [int(x) for x in score_counts.values]
        },
        'zone_distribution': {
            'labels': [str(z) for z in zone_dist.index],
            'counts': [int(x) for x in zone_dist.values]
        }
    }

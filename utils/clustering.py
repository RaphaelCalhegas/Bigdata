"""
Fonctions utilitaires pour le clustering et l'analyse des segments.
"""
import pandas as pd
import numpy as np
from typing import Dict, List


def get_cluster_name(cluster_id: int) -> str:
    """
    Retourne un nom descriptif pour chaque cluster.
    Basé sur l'analyse réelle des 302,016 transactions DVF 2024.
    """
    cluster_names = {
        0: "Petits Appartements Province Sud",
        1: "Appartements Premium Paris/IDF",
        2: "Appartements Familiaux IDF Périphérie",
        3: "Appartements Standard Province",
        4: "Grandes Maisons Familiales",
        5: "Studios/T2 Province Dynamique"
    }
    return cluster_names.get(cluster_id, f"Segment {cluster_id}")


def get_cluster_description(cluster_id: int) -> str:
    """
    Retourne une description détaillée du cluster.
    Basé sur les caractéristiques moyennes identifiées par l'algorithme K-Means.
    """
    descriptions = {
        0: "Petits appartements (37m², T1-T2) en Province Sud (PACA, Occitanie). Prix moyen 3,700€/m². "
           "Principalement Alpes-Maritimes (06), Bouches-du-Rhône (13), Var (83). Standing standard à premium. "
           "Valeur moyenne 134K€. Idéal primo-accédants ou investisseurs locatifs bord de mer.",
        
        1: "Appartements parisiens et proche banlieue (43m², T2). Prix élevé 9,900€/m². "
           "66% à Paris (75), 15% Hauts-de-Seine (92). Standing standard à premium. "
           "Valeur moyenne 425K€. Marché métropolitain haut de gamme avec forte demande locative.",
        
        2: "Appartements familiaux (70m², T3-T4) en périphérie d'Île-de-France. Prix modéré 3,100€/m². "
           "Hauts-de-Seine (92), Val-de-Marne (94), Yvelines (78). Standing standard avec opportunités. "
           "Valeur moyenne 218K€. Profil familles cherchant espace proche Paris.",
        
        3: "Appartements T3-T4 (70m²) en Province (hors sud). Prix accessible 2,900€/m². "
           "Lyon (69), Marseille (13), Nice (06), Toulouse (31). Standing standard avec potentiel rénovation. "
           "Valeur moyenne 202K€. Marché provincial équilibré pour familles et investisseurs.",
        
        4: "Grandes propriétés familiales (111m², T4-T5+). Prix variable 2,960€/m² selon localisation. "
           "Dispersées nationalement (Lyon, IDF, Province). Standing mixte avec 24% décote/travaux. "
           "Valeur moyenne 329K€. Profil familles nombreuses ou investisseurs rénovation.",
        
        5: "Studios et T2 (38m²) en zones urbaines dynamiques. Prix moyen 3,470€/m². "
           "Bordeaux (33), Nantes (44), Lille (59), banlieue IDF. Standing standard à premium. "
           "Valeur moyenne 129K€. Segment étudiant, jeunes actifs et investissement locatif."
    }
    return descriptions.get(cluster_id, "Segment de marché identifié par l'algorithme K-Means (6 clusters au total).")


def get_cluster_stats(cluster_id: int) -> Dict[str, any]:
    """
    Retourne les statistiques clés d'un cluster.
    """
    stats = {
        0: {
            "prix_m2_moyen": 3718,
            "surface_moyenne": 37.3,
            "pieces_moyennes": 1.6,
            "valeur_moyenne": 134361,
            "zone_principale": "Province Sud (PACA, Occitanie)",
            "departements_top": ["06 (Alpes-Maritimes)", "13 (Bouches-du-Rhône)", "83 (Var)"],
            "standing_dominant": "Standard Marché (36%)",
            "nb_biens": 66626,
            "pct_total": 22.1
        },
        1: {
            "prix_m2_moyen": 9874,
            "surface_moyenne": 43.2,
            "pieces_moyennes": 2.1,
            "valeur_moyenne": 425193,
            "zone_principale": "Paris & Proche Banlieue",
            "departements_top": ["75 (Paris)", "92 (Hauts-de-Seine)", "94 (Val-de-Marne)"],
            "standing_dominant": "Standard Marché (46%)",
            "nb_biens": 28725,
            "pct_total": 9.5
        },
        2: {
            "prix_m2_moyen": 3104,
            "surface_moyenne": 70.1,
            "pieces_moyennes": 3.3,
            "valeur_moyenne": 218413,
            "zone_principale": "Périphérie Île-de-France",
            "departements_top": ["92 (Hauts-de-Seine)", "94 (Val-de-Marne)", "78 (Yvelines)"],
            "standing_dominant": "Standard Marché (37%)",
            "nb_biens": 58780,
            "pct_total": 19.5
        },
        3: {
            "prix_m2_moyen": 2868,
            "surface_moyenne": 70.0,
            "pieces_moyennes": 3.3,
            "valeur_moyenne": 201769,
            "zone_principale": "Grandes Villes Province",
            "departements_top": ["13 (Bouches-du-Rhône)", "06 (Alpes-Maritimes)", "69 (Rhône)"],
            "standing_dominant": "Standard Marché (33%)",
            "nb_biens": 65836,
            "pct_total": 21.8
        },
        4: {
            "prix_m2_moyen": 2963,
            "surface_moyenne": 111.1,
            "pieces_moyennes": 4.4,
            "valeur_moyenne": 329458,
            "zone_principale": "Province (National)",
            "departements_top": ["69 (Rhône)", "92 (Hauts-de-Seine)", "75 (Paris)"],
            "standing_dominant": "Standard Marché (30%)",
            "nb_biens": 22388,
            "pct_total": 7.4
        },
        5: {
            "prix_m2_moyen": 3470,
            "surface_moyenne": 38.3,
            "pieces_moyennes": 1.7,
            "valeur_moyenne": 128547,
            "zone_principale": "Métropoles Régionales",
            "departements_top": ["33 (Gironde)", "44 (Loire-Atlantique)", "59 (Nord)"],
            "standing_dominant": "Standard Marché (39%)",
            "nb_biens": 59661,
            "pct_total": 19.8
        }
    }
    return stats.get(cluster_id, {})


def get_cluster_explanation() -> str:
    """
    Retourne une explication générale du clustering pour l'application.
    """
    return """
    Les segments (clusters) sont créés automatiquement par l'algorithme K-Means qui analyse 302,000+ transactions.
    
    L'algorithme regroupe les biens similaires selon 5 critères :
    • Prix au m² (niveau de marché)
    • Surface habitable (typologie du bien)
    • Nombre de pièces (T1, T2, T3...)
    • Zone géographique (latitude/longitude)
    • Standing relatif (ratio prix/marché local)
    
    Chaque bien est automatiquement assigné au segment dont il est le plus proche statistiquement.
    Cela permet de comparer des biens vraiment comparables et d'affiner les estimations.
    """


def get_cluster_profiles(df: pd.DataFrame, cluster_col: str = 'cluster_kmeans') -> pd.DataFrame:
    """
    Génère un profil détaillé de chaque cluster.
    
    Args:
        df: DataFrame avec les clusters assignés
        cluster_col: Nom de la colonne contenant les clusters
    
    Returns:
        DataFrame avec les stats par cluster
    """
    if cluster_col not in df.columns:
        return pd.DataFrame()
    
    # Variables numériques à agréger
    num_features = [
        'prix_m2', 'surface_reelle_bati', 
        'nombre_pieces_principales', 'valeur_fonciere'
    ]
    
    # Variables catégorielles (mode)
    cat_features = ['categorie_geo', 'standing_relative']
    
    profiles = []
    
    for cluster_id in sorted(df[cluster_col].unique()):
        cluster_data = df[df[cluster_col] == cluster_id]
        
        profile = {
            'cluster_id': int(cluster_id),
            'nb_biens': len(cluster_data),
            'pct_total': round(len(cluster_data) / len(df) * 100, 1)
        }
        
        # Stats numériques
        for col in num_features:
            if col in cluster_data.columns:
                profile[f'{col}_mean'] = round(cluster_data[col].mean(), 1)
                profile[f'{col}_median'] = round(cluster_data[col].median(), 1)
        
        # Stats catégorielles (valeur la plus fréquente)
        for col in cat_features:
            if col in cluster_data.columns:
                mode_val = cluster_data[col].mode()
                profile[f'{col}_dominant'] = mode_val.iloc[0] if len(mode_val) > 0 else 'N/A'
        
        profiles.append(profile)
    
    return pd.DataFrame(profiles)


def categorize_zone(code_commune: str) -> str:
    """
    Catégorise une commune (Métropole, IDF, Tourisme, Province).
    Reprise de la logique du notebook.
    """
    dept = code_commune[:2]
    
    # Métropoles (Top 15)
    top_villes_codes = ['31555', '06088', '44109', '67482', '34172', '33063', '59350', '35238']
    if (code_commune in top_villes_codes or 
        code_commune.startswith('751') or 
        code_commune.startswith('693') or 
        code_commune.startswith('132')):
        return '1_Metropole_Top15'
    
    # Île-de-France
    depts_idf = ['75', '92', '93', '94', '77', '78', '91', '95']
    if dept in depts_idf:
        return '2_Ile_de_France'
    
    # Zones touristiques/tension
    depts_tourisme = ['06', '13', '33', '83', '74', '69', '44', '34', '2A', '2B', '64', '35', '17']
    if dept in depts_tourisme:
        return '3_Zone_Touristique'
    
    return '4_Province_Standard'


def get_zone_label(categorie: str) -> str:
    """Retourne un label lisible pour les catégories de zone."""
    labels = {
        '1_Metropole_Top15': 'Métropole Top 15',
        '2_Ile_de_France': 'Île-de-France',
        '3_Zone_Touristique': 'Zone Touristique',
        '4_Province_Standard': 'Province Standard'
    }
    return labels.get(categorie, categorie)


def get_standing_label(standing: str) -> str:
    """Retourne un label lisible pour le standing."""
    labels = {
        '1_Decote_Travaux': 'Décote / Travaux',
        '2_Bonne_Affaire': 'Bonne Affaire',
        '3_Standard_Marche': 'Standard Marché',
        '4_Premium': 'Premium',
        '5_Prestige_Exception': 'Prestige'
    }
    return labels.get(standing, standing)


def analyze_departement(df: pd.DataFrame, code_dept: str) -> Dict:
    """
    Analyse complète d'un département.
    
    Returns:
        Dict avec KPIs et distributions
    """
    dept_data = df[df['code_commune'].str.startswith(code_dept)]
    
    if dept_data.empty:
        return {'error': 'Aucune donnée pour ce département'}
    
    # Conversion explicite en types Python natifs pour JSON
    repartition_standing = {}
    if 'standing_relative' in dept_data.columns:
        for k, v in dept_data['standing_relative'].value_counts().items():
            repartition_standing[str(k)] = int(v)
    
    return {
        'nb_transactions': int(len(dept_data)),
        'prix_m2_median': float(round(dept_data['prix_m2'].median(), 0)),
        'prix_m2_mean': float(round(dept_data['prix_m2'].mean(), 0)),
        'prix_m2_q25': float(round(dept_data['prix_m2'].quantile(0.25), 0)),
        'prix_m2_q75': float(round(dept_data['prix_m2'].quantile(0.75), 0)),
        'surface_moyenne': float(round(dept_data['surface_reelle_bati'].mean(), 1)),
        'prix_moyen': float(round(dept_data['valeur_fonciere'].mean(), 0)),
        'nb_communes': int(dept_data['code_commune'].nunique()),
        'repartition_standing': repartition_standing,
        'categorie_dominante': str(dept_data['categorie_geo'].mode().iloc[0]) if 'categorie_geo' in dept_data.columns else 'N/A'
    }

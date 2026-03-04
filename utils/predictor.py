"""
Fonctions de prédiction et d'estimation de prix immobiliers.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional


class PriceEstimator:
    """Estimateur de prix basé sur le clustering et les données de marché."""
    
    def __init__(self, data_manager):
        self.dm = data_manager
    
    def estimate_price(
        self, 
        surface: float, 
        nb_pieces: float, 
        code_commune: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict:
        """
        Estime le prix d'un bien immobilier.
        
        Returns:
            Dict avec estimation, fourchette, standing, etc.
        """
        # 1. Récupérer les stats de la commune
        commune_stats = self.dm.get_commune_stats(code_commune)
        
        if commune_stats is None:
            return {
                'success': False,
                'error': 'Commune non trouvée dans la base de données'
            }
        
        prix_m2_median = commune_stats['prix_m2_median']
        
        # 2. Calcul de base
        prix_estime = surface * prix_m2_median
        prix_m2 = prix_m2_median
        
        # 3. Ajustements selon nombre de pièces
        # Les grands appartements ont souvent un prix/m² plus faible
        if nb_pieces >= 4:
            prix_m2 *= 0.95
        elif nb_pieces <= 1.5:
            prix_m2 *= 1.05
        
        prix_estime = surface * prix_m2
        
        # 4. Fourchette (±15%)
        prix_min = prix_estime * 0.85
        prix_max = prix_estime * 1.15
        
        # 5. Détermination du standing (simplifié)
        standing = self._determine_standing(prix_m2, prix_m2_median)
        
        # 6. Cluster similaire (si modèle disponible)
        cluster_info = None
        if self.dm.kmeans_model and self.dm.scaler:
            cluster_info = self._find_cluster(surface, nb_pieces, prix_m2, code_commune)
        
        return {
            'success': True,
            'prix_estime': round(prix_estime, 0),
            'prix_min': round(prix_min, 0),
            'prix_max': round(prix_max, 0),
            'prix_m2': round(prix_m2, 0),
            'surface': surface,
            'nb_pieces': nb_pieces,
            'commune': code_commune,
            'standing': standing,
            'commune_stats': commune_stats,
            'cluster_info': cluster_info
        }
    
    def _determine_standing(self, prix_m2: float, prix_median: float) -> Dict:
        """Détermine le standing relatif du bien."""
        ratio = prix_m2 / prix_median if prix_median > 0 else 1.0
        
        if ratio < 0.70:
            label = "Décote / Travaux"
            color = "danger"
            icon = "⬇️"
        elif ratio < 0.90:
            label = "Bonne Affaire"
            color = "warning"
            icon = "💰"
        elif ratio < 1.15:
            label = "Standard Marché"
            color = "info"
            icon = "✅"
        elif ratio < 1.40:
            label = "Premium"
            color = "success"
            icon = "⭐"
        else:
            label = "Prestige"
            color = "primary"
            icon = "👑"
        
        return {
            'label': label,
            'ratio': round(ratio, 2),
            'color': color,
            'icon': icon
        }
    
    def _find_cluster(self, surface: float, nb_pieces: float, prix_m2: float, code_commune: str) -> Optional[Dict]:
        """Trouve le cluster auquel appartient le bien."""
        try:
            # Récupérer lat/lon moyens de la commune
            commune_data = self.dm.df_reference[
                self.dm.df_reference['code_commune'] == code_commune
            ]
            
            if commune_data.empty:
                return None
            
            lat = commune_data['latitude'].mean()
            lon = commune_data['longitude'].mean()
            
            # Préparer les features
            X = np.array([[surface, nb_pieces, lat, lon, prix_m2]])
            X_scaled = self.dm.scaler.transform(X)
            
            # Prédiction
            cluster_id = self.dm.kmeans_model.predict(X_scaled)[0]
            
            # Stats du cluster
            cluster_data = self.dm.df_reference[
                self.dm.df_reference['cluster_kmeans'] == cluster_id
            ]
            
            return {
                'id': int(cluster_id),
                'nb_biens': len(cluster_data),
                'prix_m2_moyen': round(cluster_data['prix_m2'].mean(), 0),
                'surface_moyenne': round(cluster_data['surface_reelle_bati'].mean(), 1)
            }
        except Exception as e:
            print(f"Erreur cluster: {e}")
            return None
    
    def find_similar_properties(
        self, 
        surface: float, 
        nb_pieces: float, 
        code_commune: str,
        max_results: int = 10
    ) -> pd.DataFrame:
        """Trouve les biens similaires dans la base."""
        if self.dm.df_reference is None:
            return pd.DataFrame()
        
        df = self.dm.df_reference.copy()
        
        # Filtres
        # 1. Même département
        dept = code_commune[:2]
        df = df[df['code_commune'].str.startswith(dept)]
        
        # 2. Surface similaire (±30%)
        df = df[
            (df['surface_reelle_bati'] >= surface * 0.7) & 
            (df['surface_reelle_bati'] <= surface * 1.3)
        ]
        
        # 3. Même nombre de pièces (±1)
        df = df[
            (df['nombre_pieces_principales'] >= nb_pieces - 1) & 
            (df['nombre_pieces_principales'] <= nb_pieces + 1)
        ]
        
        # Calcul de la distance (score de similarité)
        df['score_similarite'] = (
            abs(df['surface_reelle_bati'] - surface) / surface +
            abs(df['nombre_pieces_principales'] - nb_pieces) * 0.2
        )
        
        # Tri par similarité
        df = df.sort_values('score_similarite').head(max_results)
        
        # Sélection des colonnes pertinentes
        cols = [
            'code_commune', 'valeur_fonciere', 'surface_reelle_bati',
            'nombre_pieces_principales', 'prix_m2', 'standing_relative',
            'latitude', 'longitude'
        ]
        
        return df[[c for c in cols if c in df.columns]]

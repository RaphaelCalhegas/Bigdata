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

        Paris, Lyon et Marseille sont découpées en arrondissements dans DVF.
        L'API geo retourne le code INSEE de la ville entière (75056, 69123, 13055)
        qu'on corrige vers le 1er arrondissement représentatif.

        Returns:
            Dict avec estimation, fourchette, standing, etc.
        """
        corrections = {
            '75056': '75101',
            '69123': '69381',
            '13055': '13201',
        }
        code_commune = corrections.get(code_commune, code_commune)

        commune_stats = self.dm.get_commune_stats(code_commune)

        if commune_stats is None:
            return {
                'success': False,
                'error': 'Commune non trouvée dans la base de données'
            }

        prix_m2_median = commune_stats['prix_m2_median']
        prix_m2 = prix_m2_median

        if nb_pieces >= 4:
            prix_m2 *= 0.95
        elif nb_pieces <= 1.5:
            prix_m2 *= 1.05

        prix_estime = surface * prix_m2
        prix_min = prix_estime * 0.85
        prix_max = prix_estime * 1.15

        standing = self._determine_standing(prix_m2, prix_m2_median)
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
            icon = "bas"
        elif ratio < 0.90:
            label = "Bonne Affaire"
            color = "warning"
            icon = "bon"
        elif ratio < 1.15:
            label = "Standard Marché"
            color = "info"
            icon = "standard"
        elif ratio < 1.40:
            label = "Premium"
            color = "success"
            icon = "premium"
        else:
            label = "Prestige"
            color = "primary"
            icon = "prestige"

        return {
            'label': label,
            'ratio': round(ratio, 2),
            'color': color,
            'icon': icon
        }

    def _find_cluster(
        self,
        surface: float,
        nb_pieces: float,
        prix_m2: float,
        code_commune: str
    ) -> Optional[Dict]:
        """Trouve le cluster auquel appartient le bien."""
        try:
            commune_docs = list(self.dm.db["properties"].find(
                {"code_commune": str(code_commune)},
                {"_id": 0, "latitude": 1, "longitude": 1}
            ))

            if not commune_docs:
                return None

            latitudes = [
                doc.get("latitude")
                for doc in commune_docs
                if doc.get("latitude") is not None
            ]
            longitudes = [
                doc.get("longitude")
                for doc in commune_docs
                if doc.get("longitude") is not None
            ]

            if not latitudes or not longitudes:
                return None

            lat = sum(latitudes) / len(latitudes)
            lon = sum(longitudes) / len(longitudes)

            X = np.array([[surface, nb_pieces, lat, lon, prix_m2]])
            X_scaled = self.dm.scaler.transform(X)

            cluster_id = int(self.dm.kmeans_model.predict(X_scaled)[0])

            cluster_docs = list(self.dm.db["properties"].find(
                {"cluster_kmeans": cluster_id},
                {"_id": 0, "prix_m2": 1, "surface_reelle_bati": 1}
            ))

            if not cluster_docs:
                return None

            prix_vals = [doc.get("prix_m2", 0) for doc in cluster_docs]
            surf_vals = [doc.get("surface_reelle_bati", 0) for doc in cluster_docs]

            return {
                "id": cluster_id,
                "nb_biens": len(cluster_docs),
                "prix_m2_moyen": round(sum(prix_vals) / len(prix_vals), 0),
                "surface_moyenne": round(sum(surf_vals) / len(surf_vals), 1),
            }

        except Exception as e:
            print(f"[Cluster] Erreur : {e}")
            return None

    def find_similar_properties(
        self,
        surface: float,
        nb_pieces: float,
        code_commune: str,
        max_results: int = 10
    ) -> pd.DataFrame:
        """Trouve les biens similaires dans MongoDB."""
        dept = str(code_commune)[:2]
        regex = f"^{dept}"

        docs = list(self.dm.db["properties"].find(
            {
                "code_commune": {"$regex": regex},
                "surface_reelle_bati": {"$gte": surface * 0.7, "$lte": surface * 1.3},
                "nombre_pieces_principales": {"$gte": nb_pieces - 1, "$lte": nb_pieces + 1},
            },
            {
                "_id": 0,
                "code_commune": 1,
                "valeur_fonciere": 1,
                "surface_reelle_bati": 1,
                "nombre_pieces_principales": 1,
                "prix_m2": 1,
                "standing_relative": 1,
                "latitude": 1,
                "longitude": 1,
            }
        ))

        if not docs:
            return pd.DataFrame()

        df = pd.DataFrame(docs)

        df["score_similarite"] = (
            abs(df["surface_reelle_bati"] - surface) / surface +
            abs(df["nombre_pieces_principales"] - nb_pieces) * 0.2
        )

        df = df.sort_values("score_similarite").head(max_results)

        cols = [
            "code_commune",
            "valeur_fonciere",
            "surface_reelle_bati",
            "nombre_pieces_principales",
            "prix_m2",
            "standing_relative",
            "latitude",
            "longitude"
        ]

        return df[[c for c in cols if c in df.columns]]
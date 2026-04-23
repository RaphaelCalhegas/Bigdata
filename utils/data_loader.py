"""
Utilitaires pour le chargement et la gestion des données immobilières.
Les données métier sont stockées dans MongoDB Atlas.
"""
import pandas as pd
import pickle
from pathlib import Path
from typing import Optional, Dict

from utils.db import get_db


class DataManager:
    """Gestionnaire centralisé pour les données et modèles."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.db = None
        self.scaler = None
        self.kmeans_model = None
        
    def load_all(self):
        """Initialise MongoDB et charge les modèles ML locaux."""
        print("📂 Chargement des données...")
        
        self.db = get_db()
        
        # Scaler
        scaler_path = self.models_dir / "scaler.pkl"
        if scaler_path.exists():
            with open(scaler_path, 'rb') as f:
                self.scaler = pickle.load(f)
            print("✅ Scaler chargé")
        
        # Modèle K-Means
        kmeans_path = self.models_dir / "kmeans_model.pkl"
        if kmeans_path.exists():
            with open(kmeans_path, 'rb') as f:
                self.kmeans_model = pickle.load(f)
            print("✅ Modèle K-Means chargé")
        
        properties_count = self.db["properties"].count_documents({})
        communes_count = self.db["communes"].count_documents({})
        print(f"✅ Properties disponibles dans MongoDB : {properties_count:,} lignes")
        print(f"✅ Statistiques communes disponibles dans MongoDB : {communes_count} communes")
        
        return self
    
    def get_commune_stats(self, code_commune: str) -> Optional[Dict]:
        """Récupère les stats d'une commune depuis MongoDB."""
        if self.db is None:
            self.db = get_db()
        
        stats = self.db["communes"].find_one(
            {"code_commune": str(code_commune)},
            {"_id": 0}
        )
        
        if not stats:
            return None
        
        return {
            'prix_m2_median': float(stats.get('prix_m2_median', 0)),
            'prix_m2_mean': float(stats.get('prix_m2_mean', 0)),
            'nb_transactions': int(stats.get('count', 0)),
            'surface_moyenne': float(stats.get('surface_mean', 0)),
            'categorie_geo': str(stats.get('categorie_geo', 'Inconnue'))
        }
    
    def get_departement_stats(self, code_dept: str) -> pd.DataFrame:
        """Récupère les données d'un département depuis MongoDB."""
        if self.db is None:
            self.db = get_db()
        
        regex = f"^{code_dept}"
        docs = list(
            self.db["properties"].find(
                {"code_commune": {"$regex": regex}},
                {"_id": 0}
            )
        )
        
        if not docs:
            return pd.DataFrame()
        
        return pd.DataFrame(docs)
    
    def search_communes(self, query: str, limit: int = 10) -> list:
        """Recherche des communes par code."""
        if self.db is None:
            self.db = get_db()
        
        query = str(query).lower().strip()
        if not query:
            return []
        
        docs = list(
            self.db["communes"].find(
                {"code_commune": {"$regex": query, "$options": "i"}},
                {"_id": 0}
            ).limit(limit)
        )
        
        results = []
        for doc in docs:
            stats = {
                'prix_m2_median': float(doc.get('prix_m2_median', 0)),
                'prix_m2_mean': float(doc.get('prix_m2_mean', 0)),
                'nb_transactions': int(doc.get('count', 0)),
                'surface_moyenne': float(doc.get('surface_mean', 0)),
                'categorie_geo': str(doc.get('categorie_geo', 'Inconnue'))
            }
            results.append({
                'code': doc.get('code_commune'),
                'label': f"{doc.get('code_commune')} ({stats['nb_transactions']} ventes)",
                'stats': stats
            })
        
        return results


# Instance globale
data_manager = DataManager()
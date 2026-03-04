"""
Utilitaires pour le chargement et la gestion des données immobilières.
"""
import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from typing import Optional, Dict


class DataManager:
    """Gestionnaire centralisé pour les données et modèles."""
    
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.df_reference = None
        self.scaler = None
        self.kmeans_model = None
        self.df_communes = None
        
    def load_all(self):
        """Charge tous les fichiers nécessaires."""
        print("📂 Chargement des données...")
        
        # Dataset de référence
        ref_path = self.models_dir / "df_reference.pkl"
        if ref_path.exists():
            with open(ref_path, 'rb') as f:
                self.df_reference = pickle.load(f)
            print(f"✅ Dataset chargé : {len(self.df_reference):,} lignes")
        
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
        
        # Statistiques par commune
        communes_path = self.models_dir / "df_communes.pkl"
        if communes_path.exists():
            with open(communes_path, 'rb') as f:
                self.df_communes = pickle.load(f)
            print(f"✅ Statistiques communes chargées : {len(self.df_communes)} communes")
        
        return self
    
    def get_commune_stats(self, code_commune: str) -> Optional[Dict]:
        """Récupère les stats d'une commune."""
        if self.df_communes is None or code_commune not in self.df_communes.index:
            return None
        
        stats = self.df_communes.loc[code_commune]
        return {
            'prix_m2_median': float(stats.get('prix_m2_median', 0)),
            'prix_m2_mean': float(stats.get('prix_m2_mean', 0)),
            'nb_transactions': int(stats.get('count', 0)),
            'surface_moyenne': float(stats.get('surface_mean', 0)),
            'categorie_geo': str(stats.get('categorie_geo', 'Inconnue'))
        }
    
    def get_departement_stats(self, code_dept: str) -> pd.DataFrame:
        """Récupère les stats d'un département."""
        if self.df_reference is None:
            return pd.DataFrame()
        
        # Extraction du code département
        mask = self.df_reference['code_commune'].str.startswith(code_dept)
        return self.df_reference[mask]
    
    def search_communes(self, query: str, limit: int = 10) -> list:
        """Recherche des communes par nom ou code."""
        if self.df_communes is None:
            return []
        
        query = query.lower()
        results = []
        
        for code in self.df_communes.index:
            if query in code.lower():
                stats = self.get_commune_stats(code)
                if stats:
                    results.append({
                        'code': code,
                        'label': f"{code} ({stats['nb_transactions']} ventes)",
                        'stats': stats
                    })
        
        return results[:limit]


# Instance globale
data_manager = DataManager()

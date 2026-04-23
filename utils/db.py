"""
Connexion et gestion de la base de données MongoDB.
"""
import os
import certifi
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

# Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME   = os.getenv("DB_NAME", "immopro")

# Client global
_client = None
_db     = None


def get_db():
    """Retourne l'instance de la base de données (singleton)."""
    global _client, _db

    if _db is None:
        try:
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where()
            )
            # Vérification de la connexion
            _client.admin.command("ping")
            _db = _client[DB_NAME]
            print(f"[MongoDB] Connecté à la base : {DB_NAME}")
        except ConnectionFailure as e:
            print(f"[MongoDB] Erreur de connexion : {e}")
            raise

    return _db


def get_collections():
    """Retourne toutes les collections utilisées dans l'app."""
    db = get_db()
    return {
        "properties":      db["properties"],       # Données immobilières
        "communes":        db["communes"],          # Stats par commune
        "users":           db["users"],             # Comptes utilisateurs
        "sessions":        db["search_sessions"],   # Historique des recherches
        "recommendations": db["recommendations"]    # Suggestions personnalisées
    }


def init_indexes():
    """Crée les index MongoDB pour optimiser les requêtes."""
    cols = get_collections()

    # Index sur les propriétés
    cols["properties"].create_index([("code_commune", ASCENDING)])
    cols["properties"].create_index([("prix_m2",      ASCENDING)])
    cols["properties"].create_index([("cluster_kmeans", ASCENDING)])

    # Index sur les communes
    cols["communes"].create_index([("code_commune", ASCENDING)], unique=True)

    # Index sur les utilisateurs
    cols["users"].create_index([("email",    ASCENDING)], unique=True)
    cols["users"].create_index([("username", ASCENDING)], unique=True)

    # Index sur les sessions de recherche
    cols["sessions"].create_index([("user_id",    ASCENDING)])
    cols["sessions"].create_index([("created_at", DESCENDING)])

    print("[MongoDB] Index créés avec succès")


def close_db():
    """Ferme la connexion MongoDB."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db     = None
        print("[MongoDB] Connexion fermée")
"""
Gestion de l'authentification et des utilisateurs.
"""
from flask_login import UserMixin
from flask_bcrypt import Bcrypt
from bson import ObjectId
from datetime import datetime
from utils.db import get_collections

bcrypt = Bcrypt()


class User(UserMixin):
    """
    Modèle utilisateur compatible avec Flask-Login.
    """

    def __init__(self, user_data: dict):
        self.id       = str(user_data["_id"])
        self.username = user_data["username"]
        self.email    = user_data["email"]
        self.created_at = user_data.get("created_at")
        self.preferences = user_data.get("preferences", {})

    @staticmethod
    def get_by_id(user_id: str):
        """Récupère un utilisateur par son identifiant."""
        cols = get_collections()
        user_data = cols["users"].find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_email(email: str):
        """Récupère un utilisateur par son adresse email."""
        cols = get_collections()
        user_data = cols["users"].find_one({"email": email.lower().strip()})
        return user_data

    @staticmethod
    def get_by_username(username: str):
        """Récupère un utilisateur par son nom d'utilisateur."""
        cols = get_collections()
        user_data = cols["users"].find_one({"username": username.strip()})
        return user_data


def register_user(username: str, email: str, password: str) -> dict:
    """
    Enregistre un nouvel utilisateur en base.

    Returns:
        dict avec 'success' (bool) et 'error' ou 'user_id' (str)
    """
    cols = get_collections()

    # Vérification unicité email
    if cols["users"].find_one({"email": email.lower().strip()}):
        return {"success": False, "error": "Cette adresse email est déjà utilisée."}

    # Vérification unicité username
    if cols["users"].find_one({"username": username.strip()}):
        return {"success": False, "error": "Ce nom d'utilisateur est déjà pris."}

    # Validation basique
    if len(password) < 8:
        return {"success": False, "error": "Le mot de passe doit contenir au moins 8 caractères."}

    if len(username) < 3:
        return {"success": False, "error": "Le nom d'utilisateur doit contenir au moins 3 caractères."}

    # Hashage du mot de passe
    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    # Insertion en base
    user_doc = {
        "username":   username.strip(),
        "email":      email.lower().strip(),
        "password":   hashed_password,
        "created_at": datetime.utcnow(),
        "preferences": {
            "zones_favorites":    [],
            "budget_min":         None,
            "budget_max":         None,
            "surface_min":        None,
            "nb_pieces_prefere":  None
        }
    }

    result = cols["users"].insert_one(user_doc)
    return {"success": True, "user_id": str(result.inserted_id)}


def login_user_auth(email: str, password: str) -> dict:
    """
    Vérifie les identifiants d'un utilisateur.

    Returns:
        dict avec 'success' (bool) et 'error' ou 'user' (User)
    """
    user_data = User.get_by_email(email)

    if not user_data:
        return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

    if not bcrypt.check_password_hash(user_data["password"], password):
        return {"success": False, "error": "Adresse email ou mot de passe incorrect."}

    return {"success": True, "user": User(user_data)}


def update_user_preferences(user_id: str, preferences: dict) -> bool:
    """
    Met à jour les préférences d'un utilisateur.

    Returns:
        True si la mise à jour a réussi, False sinon.
    """
    cols = get_collections()
    result = cols["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"preferences": preferences}}
    )
    return result.modified_count > 0

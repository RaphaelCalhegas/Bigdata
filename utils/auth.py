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
    """Modèle utilisateur compatible avec Flask-Login."""

    def __init__(self, user_data: dict):
        self.id          = str(user_data["_id"])
        self.username    = user_data["username"]
        self.email       = user_data["email"]
        self.created_at  = user_data.get("created_at")
        self.preferences = user_data.get("preferences", {})

    @staticmethod
    def get_by_id(user_id: str):
        """Récupère un utilisateur par son identifiant."""
        cols      = get_collections()
        user_data = cols["users"].find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_email(email: str):
        """Récupère un utilisateur par son adresse email."""
        cols = get_collections()
        return cols["users"].find_one({"email": email.lower().strip()})

    @staticmethod
    def get_by_username(username: str):
        """Récupère un utilisateur par son nom d'utilisateur."""
        cols = get_collections()
        return cols["users"].find_one({"username": username.strip()})


def register_user(username: str, email: str, password: str) -> dict:
    """
    Enregistre un nouvel utilisateur en base.

    Returns:
        dict avec 'success' (bool) et 'error' ou 'user_id' (str)
    """
    cols = get_collections()

    if cols["users"].find_one({"email": email.lower().strip()}):
        return {"success": False, "error": "Cette adresse email est déjà utilisée."}

    if cols["users"].find_one({"username": username.strip()}):
        return {"success": False, "error": "Ce nom d'utilisateur est déjà pris."}

    if len(password) < 8:
        return {"success": False, "error": "Le mot de passe doit contenir au moins 8 caractères."}

    if len(username) < 3:
        return {"success": False, "error": "Le nom d'utilisateur doit contenir au moins 3 caractères."}

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    user_doc = {
        "username":   username.strip(),
        "email":      email.lower().strip(),
        "password":   hashed_password,
        "created_at": datetime.utcnow(),
        "preferences": {
            "zones_favorites":   [],
            "budget_min":        None,
            "budget_max":        None,
            "surface_min":       None,
            "nb_pieces_prefere": None
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
    """Met à jour les préférences d'un utilisateur."""
    cols   = get_collections()
    result = cols["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"preferences": preferences}}
    )
    return result.modified_count > 0


def update_user_profile(user_id: str, username: str = None, email: str = None,
                        current_password: str = None, new_password: str = None) -> dict:
    """
    Met à jour le profil d'un utilisateur (nom, email, mot de passe).

    Validations :
    - Unicité du nouveau username et du nouvel email
    - Vérification du mot de passe actuel avant changement de mot de passe
    - Nouveau mot de passe >= 8 caractères

    Returns:
        dict avec 'success' (bool) et 'error' (str) ou 'message' (str)
    """
    cols      = get_collections()
    user_data = cols["users"].find_one({"_id": ObjectId(user_id)})

    if not user_data:
        return {"success": False, "error": "Utilisateur introuvable."}

    updates = {}
    errors  = []

    # --- Mise à jour du nom d'utilisateur ---
    if username and username.strip() != user_data["username"]:
        username = username.strip()

        if len(username) < 3:
            errors.append("Le nom d'utilisateur doit contenir au moins 3 caractères.")
        elif cols["users"].find_one({"username": username, "_id": {"$ne": ObjectId(user_id)}}):
            errors.append("Ce nom d'utilisateur est déjà pris.")
        else:
            updates["username"] = username

    # --- Mise à jour de l'email ---
    if email and email.lower().strip() != user_data["email"]:
        email = email.lower().strip()

        if "@" not in email or "." not in email:
            errors.append("L'adresse email n'est pas valide.")
        elif cols["users"].find_one({"email": email, "_id": {"$ne": ObjectId(user_id)}}):
            errors.append("Cette adresse email est déjà utilisée.")
        else:
            updates["email"] = email

    # --- Mise à jour du mot de passe ---
    if new_password:
        if not current_password:
            errors.append("Le mot de passe actuel est requis pour en définir un nouveau.")
        elif not bcrypt.check_password_hash(user_data["password"], current_password):
            errors.append("Le mot de passe actuel est incorrect.")
        elif len(new_password) < 8:
            errors.append("Le nouveau mot de passe doit contenir au moins 8 caractères.")
        else:
            updates["password"] = bcrypt.generate_password_hash(new_password).decode("utf-8")

    if errors:
        return {"success": False, "error": " ".join(errors)}

    if not updates:
        return {"success": False, "error": "Aucune modification détectée."}

    updates["updated_at"] = datetime.utcnow()

    cols["users"].update_one(
        {"_id": ObjectId(user_id)},
        {"$set": updates}
    )

    return {"success": True, "message": "Profil mis à jour avec succès.", "updates": list(updates.keys())}

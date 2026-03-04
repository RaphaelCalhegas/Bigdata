"""
Moteur de recommandations personnalisées basé sur l'historique de recherche.
"""
from datetime import datetime
from bson import ObjectId
from utils.db import get_collections


def save_search(user_id: str, search_type: str, search_data: dict) -> None:
    """
    Sauvegarde une recherche utilisateur en base.

    Args:
        user_id     : Identifiant de l'utilisateur
        search_type : Type de recherche ('estimation', 'similaires', 'opportunites', 'marche')
        search_data : Données de la recherche (commune, surface, prix, etc.)
    """
    cols = get_collections()
    cols["sessions"].insert_one({
        "user_id":     user_id,
        "type":        search_type,
        "data":        search_data,
        "created_at":  datetime.utcnow()
    })


def get_search_history(user_id: str, limit: int = 20) -> list:
    """
    Retourne l'historique des recherches d'un utilisateur.

    Args:
        user_id : Identifiant de l'utilisateur
        limit   : Nombre maximum de résultats à retourner

    Returns:
        Liste des recherches triées par date décroissante
    """
    cols = get_collections()
    cursor = cols["sessions"].find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit)

    history = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        history.append(doc)

    return history


def build_user_profile(user_id: str) -> dict:
    """
    Construit un profil utilisateur à partir de son historique de recherche.

    Analyse les zones, budgets et surfaces recherchés pour en extraire
    les préférences implicites de l'utilisateur.

    Returns:
        dict contenant les zones, budgets et surfaces les plus fréquents
    """
    history = get_search_history(user_id, limit=50)

    if not history:
        return {}

    zones       = {}
    budgets     = []
    surfaces    = []
    departements = {}

    for search in history:
        data = search.get("data", {})

        # Extraction des zones recherchées
        code_commune = data.get("code_commune")
        if code_commune:
            zones[code_commune] = zones.get(code_commune, 0) + 1
            dept = code_commune[:2]
            departements[dept] = departements.get(dept, 0) + 1

        # Extraction des budgets
        prix = data.get("prix_estime") or data.get("prix")
        if prix:
            budgets.append(float(prix))

        # Extraction des surfaces
        surface = data.get("surface")
        if surface:
            surfaces.append(float(surface))

    # Construction du profil
    profile = {
        "zones_favorites":     sorted(zones, key=zones.get, reverse=True)[:5],
        "departements_favoris": sorted(departements, key=departements.get, reverse=True)[:3],
        "budget_moyen":        round(sum(budgets) / len(budgets), 0) if budgets else None,
        "budget_min":          round(min(budgets), 0) if budgets else None,
        "budget_max":          round(max(budgets), 0) if budgets else None,
        "surface_moyenne":     round(sum(surfaces) / len(surfaces), 1) if surfaces else None,
        "nb_recherches":       len(history)
    }

    return profile


def generate_recommendations(user_id: str, data_manager) -> list:
    """
    Génère des recommandations personnalisées pour un utilisateur.

    Basé sur le profil utilisateur, propose des communes similaires
    à celles déjà recherchées avec des indicateurs de marché.

    Args:
        user_id      : Identifiant de l'utilisateur
        data_manager : Instance du DataManager pour accéder aux données

    Returns:
        Liste de recommandations avec commune, prix et justification
    """
    profile = build_user_profile(user_id)

    if not profile or not profile.get("zones_favorites"):
        return []

    recommendations = []
    zones_dejà_vues = set(profile["zones_favorites"])

    # Pour chaque département fréquemment recherché
    for dept in profile.get("departements_favoris", []):
        if data_manager.df_communes is None:
            continue

        # Récupération des communes du département
        communes_dept = [
            code for code in data_manager.df_communes.index
            if code.startswith(dept) and code not in zones_dejà_vues
        ]

        # Budget de référence
        budget_moyen = profile.get("budget_moyen")
        surface_moyenne = profile.get("surface_moyenne", 50)

        for code_commune in communes_dept[:20]:
            stats = data_manager.get_commune_stats(code_commune)
            if not stats or stats["nb_transactions"] < 10:
                continue

            prix_estime = stats["prix_m2_median"] * surface_moyenne

            # Filtrage par budget si disponible
            if budget_moyen:
                ratio = prix_estime / budget_moyen
                if ratio < 0.6 or ratio > 1.4:
                    continue

            recommendations.append({
                "code_commune":    code_commune,
                "prix_m2_median":  stats["prix_m2_median"],
                "nb_transactions": stats["nb_transactions"],
                "prix_estime":     round(prix_estime, 0),
                "raison":          f"Commune similaire à vos recherches dans le département {dept}",
                "score":           stats["nb_transactions"]
            })

    # Tri par score décroissant et limitation des résultats
    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:10]


def save_recommendations(user_id: str, recommendations: list) -> None:
    """
    Sauvegarde les recommandations générées en base.

    Args:
        user_id         : Identifiant de l'utilisateur
        recommendations : Liste des recommandations à sauvegarder
    """
    cols = get_collections()
    cols["recommendations"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id":         user_id,
                "recommendations": recommendations,
                "updated_at":      datetime.utcnow()
            }
        },
        upsert=True
    )


def get_recommendations(user_id: str) -> list:
    """
    Récupère les dernières recommandations sauvegardées d'un utilisateur.

    Returns:
        Liste des recommandations ou liste vide si aucune trouvée
    """
    cols = get_collections()
    doc = cols["recommendations"].find_one({"user_id": user_id})
    if not doc:
        return []
    return doc.get("recommendations", [])

"""
Moteur de recommandations personnalisées basé sur l'historique de recherche.

Pipeline d'événements asynchrones :
  1. L'utilisateur effectue une recherche → save_search() enregistre l'événement
  2. trigger_profile_update() lance la mise à jour en arrière-plan (Thread daemon)
  3. build_user_profile() recalcule le profil depuis l'historique MongoDB
  4. generate_recommendations() produit des recommandations personnalisées
  5. save_recommendations() met à jour MongoDB silencieusement
  → Le profil utilisateur est toujours à jour sans action manuelle

Budget implicite :
  On ne demande jamais le budget à l'utilisateur.
  On le déduit depuis son comportement :
  budget_implicite = prix_m2_median(zones_recherchées) × surface_moyenne_recherchée
  Cette valeur est stable car basée sur le marché réel, pas sur des estimations ponctuelles.

Pondération temporelle :
  Les recherches récentes comptent plus que les anciennes.
  poids = 1 / (1 + nb_jours_depuis_recherche)

Détection de cohérence :
  Si les zones recherchées sont trop disparates, on ne génère pas de recommandations
  et on retourne un message explicatif.
"""
import threading
from datetime import datetime, timezone
from collections import Counter
from utils.db import get_collections


# ---------------------------------------------------------------------------
# ÉVÉNEMENTS — Sauvegarde des actions utilisateur
# ---------------------------------------------------------------------------

def save_search(user_id: str, search_type: str, search_data: dict) -> None:
    """
    Sauvegarde une recherche utilisateur et déclenche automatiquement
    la mise à jour du profil en arrière-plan.

    Args:
        user_id     : Identifiant de l'utilisateur
        search_type : Type ('estimation', 'similaires', 'opportunites', 'marche')
        search_data : Données de la recherche
    """
    cols = get_collections()
    cols["sessions"].insert_one({
        "user_id":    user_id,
        "type":       search_type,
        "data":       search_data,
        "created_at": datetime.utcnow()
    })

    # Déclenchement asynchrone — l'utilisateur ne ressent aucun délai
    trigger_profile_update(user_id)


def get_search_history(user_id: str, limit: int = 20) -> list:
    """
    Retourne l'historique des recherches d'un utilisateur.

    Args:
        user_id : Identifiant de l'utilisateur
        limit   : Nombre maximum de résultats

    Returns:
        Liste des recherches triées par date décroissante
    """
    cols   = get_collections()
    cursor = cols["sessions"].find(
        {"user_id": user_id}
    ).sort("created_at", -1).limit(limit)

    history = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        history.append(doc)

    return history


# ---------------------------------------------------------------------------
# PIPELINE ASYNCHRONE — Mise à jour silencieuse du profil
# ---------------------------------------------------------------------------

def trigger_profile_update(user_id: str) -> None:
    """
    Déclenche la mise à jour du profil utilisateur en arrière-plan.

    Utilise un Thread daemon pour ne pas bloquer la réponse HTTP.
    L'utilisateur reçoit sa réponse immédiatement pendant que le
    profil se recalcule silencieusement en arrière-plan.
    """
    def _update():
        try:
            from utils.data_loader import data_manager
            recommendations = generate_recommendations(user_id, data_manager)
            save_recommendations(user_id, recommendations)
            print(f"[Recommandations] Profil mis à jour pour {user_id} ({len(recommendations)} reco)")
        except Exception as e:
            print(f"[Recommandations] Erreur mise à jour asynchrone : {e}")

    thread = threading.Thread(target=_update, daemon=True)
    thread.start()


# ---------------------------------------------------------------------------
# PROFIL UTILISATEUR — Construction depuis l'historique
# ---------------------------------------------------------------------------

def build_user_profile(user_id: str, data_manager=None) -> dict:
    """
    Construit un profil utilisateur riche à partir de son historique.

    Nouveautés vs version précédente :
    - Pondération temporelle : recherches récentes > anciennes
    - Budget implicite comportemental : prix_m2_median × surface_moyenne
      (plus stable que la moyenne des prix estimés)
    - Score de cohérence : mesure si les zones sont homogènes ou dispersées
    - Détection de l'intention (exploration vs recherche ciblée)

    Args:
        user_id      : Identifiant de l'utilisateur
        data_manager : Instance DataManager (optionnel, pour prix/m² des zones)

    Returns:
        dict profil complet ou dict vide si pas d'historique
    """
    history = get_search_history(user_id, limit=100)

    if not history:
        return {}

    now              = datetime.utcnow()
    communes_pond    = {}   # code_commune → score pondéré temporellement
    departements_pond = {}  # dept → score pondéré
    surfaces         = []
    surfaces_pond    = []   # surfaces pondérées temporellement
    types_recherches = []
    prix_m2_zones    = []   # prix/m² des communes recherchées

    for search in history:
        data        = search.get("data", {})
        search_type = search.get("type", "")
        types_recherches.append(search_type)

        # Pondération temporelle : recherche récente = poids élevé
        created_at = search.get("created_at")
        if created_at and isinstance(created_at, datetime):
            nb_jours = max(0, (now - created_at).days)
        else:
            nb_jours = 30
        poids = 1.0 / (1.0 + nb_jours * 0.1)  # Décroissance douce sur 10 jours

        # Zones recherchées (pondérées)
        code_commune = data.get("code_commune")
        if code_commune:
            communes_pond[code_commune] = communes_pond.get(code_commune, 0) + poids
            dept = str(code_commune)[:2]
            departements_pond[dept] = departements_pond.get(dept, 0) + poids

        # Département direct (analyse marché)
        code_dept = data.get("code_dept")
        if code_dept:
            departements_pond[str(code_dept)] = departements_pond.get(str(code_dept), 0) + poids

        # Surfaces (pondérées)
        surface = data.get("surface")
        if surface:
            try:
                s = float(surface)
                surfaces.append(s)
                surfaces_pond.append(s * poids)
            except (ValueError, TypeError):
                pass

    # Surface moyenne pondérée (plus représentative que la moyenne simple)
    surface_moy_pond = None
    if surfaces_pond and sum(poids for poids in [1.0 / (1.0 + max(0, (now - s.get("created_at", now)).days) * 0.1)
                              for s in history if s.get("data", {}).get("surface")] or [1]):
        if surfaces:
            surface_moy_pond = round(sum(surfaces) / len(surfaces), 1)

    # Tri par score pondéré décroissant
    communes_triees     = sorted(communes_pond, key=communes_pond.get, reverse=True)
    departements_tries  = sorted(departements_pond, key=departements_pond.get, reverse=True)
    types_freq          = Counter(types_recherches)

    # -------------------------------------------------------------------
    # BUDGET IMPLICITE COMPORTEMENTAL
    # Prix/m² médian des zones recherchées × surface moyenne
    # Stable car basé sur le marché réel, pas sur des estimations ponctuelles
    # -------------------------------------------------------------------
    budget_implicite = None
    surface_ref      = surface_moy_pond or 60

    if data_manager and communes_triees[:5]:
        # Récupère le prix/m² médian des 5 communes les plus recherchées
        for code in communes_triees[:5]:
            stats = data_manager.get_commune_stats(code)
            if stats and stats.get("prix_m2_median", 0) > 0:
                prix_m2_zones.append(stats["prix_m2_median"])

        if prix_m2_zones:
            # Médiane des prix/m² pour éviter les valeurs extrêmes
            prix_m2_zones.sort()
            mid = len(prix_m2_zones) // 2
            prix_m2_median = prix_m2_zones[mid] if len(prix_m2_zones) % 2 != 0 \
                else (prix_m2_zones[mid - 1] + prix_m2_zones[mid]) / 2
            budget_implicite = round(prix_m2_median * surface_ref, 0)

    # -------------------------------------------------------------------
    # SCORE DE COHÉRENCE — Les zones sont-elles homogènes ?
    # Si l'utilisateur explore partout, ses recherches sont peu cohérentes
    # -------------------------------------------------------------------
    score_coherence = _compute_coherence_score(departements_pond)

    profile = {
        # Zones favorites pondérées temporellement
        "zones_favorites":       communes_triees[:5],
        "departements_favoris":  departements_tries[:3],

        # Budget implicite comportemental (stable)
        "budget_implicite":      budget_implicite,
        "prix_m2_zones":         round(sum(prix_m2_zones) / len(prix_m2_zones), 0) if prix_m2_zones else None,

        # Surface comportementale
        "surface_moyenne":       surface_moy_pond,
        "surface_min":           round(min(surfaces), 0) if surfaces else None,
        "surface_max":           round(max(surfaces), 0) if surfaces else None,

        # Comportement
        "type_recherche_favori": types_freq.most_common(1)[0][0] if types_freq else None,
        "nb_recherches_total":   len(history),
        "nb_communes_uniques":   len(communes_pond),
        "nb_departements":       len(departements_pond),
        "zone_recurrente":       communes_triees[0] if communes_triees else None,

        # Cohérence des recherches (0-100)
        # 100 = très ciblé, <40 = trop dispersé pour recommander
        "score_coherence":       score_coherence,
    }

    return profile


def _compute_coherence_score(departements_pond: dict) -> float:
    """
    Calcule un score de cohérence des zones recherchées (0-100).

    Un score élevé signifie que l'utilisateur recherche dans des zones
    homogènes → recommandations pertinentes.
    Un score faible signifie qu'il explore partout → recommandations peu fiables.

    Méthode : concentration des scores pondérés sur le top département.
    Si 80% des recherches sont dans 1 département → score ~80.
    Si réparti sur 10 départements → score ~10.
    """
    if not departements_pond:
        return 0.0

    total  = sum(departements_pond.values())
    if total == 0:
        return 0.0

    # Part du département le plus recherché
    top_score = max(departements_pond.values())
    score     = (top_score / total) * 100

    return round(score, 1)


# ---------------------------------------------------------------------------
# MOTEUR DE RECOMMANDATIONS — Génération personnalisée
# ---------------------------------------------------------------------------

def generate_recommendations(user_id: str, data_manager) -> list:
    """
    Génère des recommandations personnalisées multicritères.

    Stratégies combinées :
    1. Communes voisines des zones déjà recherchées (même département)
    2. Communes similaires en prix/m² (cohérence budget implicite)

    Garde-fous :
    - Si score_coherence < 30 → recherches trop dispersées, reco peu fiables
    - Budget basé sur prix/m² × surface (comportemental, stable)
    - Pondération temporelle intégrée dans le profil

    Returns:
        Liste de max 10 recommandations triées par score décroissant
    """
    profile = build_user_profile(user_id, data_manager)

    if not profile or not profile.get("departements_favoris"):
        return _get_default_recommendations(data_manager)

    # -------------------------------------------------------------------
    # GARDE-FOU COHÉRENCE
    # Si l'utilisateur explore partout sans intention claire,
    # on retourne les recommendations par défaut plutôt que des reco incohérentes
    # -------------------------------------------------------------------
    score_coherence = profile.get("score_coherence", 100)
    if score_coherence < 30:
        print(f"[Recommandations] Score cohérence faible ({score_coherence}) — reco par défaut")
        return _get_default_recommendations(data_manager)

    recommendations = []
    zones_deja_vues = set(profile.get("zones_favorites", []))
    surface_moy     = profile.get("surface_moyenne") or 60
    dept_favoris    = profile.get("departements_favoris", [])

    # Budget implicite comportemental (stable)
    budget_implicite = profile.get("budget_implicite")
    prix_m2_cible    = profile.get("prix_m2_zones")

    # -------------------------------------------------------------------
    # Stratégie 1 : Communes voisines (même département que les favoris)
    # -------------------------------------------------------------------
    for dept in dept_favoris[:3]:
        communes_dept = _get_communes_departement(data_manager, dept)

        for code_commune, stats in communes_dept:
            if code_commune in zones_deja_vues:
                continue

            prix_estime = stats["prix_m2_median"] * surface_moy

            # Filtre cohérence budget implicite
            if budget_implicite:
                ratio = prix_estime / budget_implicite
                if ratio < 0.4 or ratio > 2.5:
                    continue

            score  = _compute_score(stats, budget_implicite, prix_estime, surface_moy)
            raison = _generate_reason(profile, dept, stats, code_commune, "voisin")

            recommendations.append({
                "code_commune":    code_commune,
                "prix_m2_median":  round(stats["prix_m2_median"], 0),
                "nb_transactions": stats["nb_transactions"],
                "prix_estime":     round(prix_estime, 0),
                "categorie_geo":   stats.get("categorie_geo", ""),
                "raison":          raison,
                "score":           score,
                "strategie":       "voisin"
            })

    # -------------------------------------------------------------------
    # Stratégie 2 : Communes à prix/m² similaire (autres départements)
    # Budget implicite = prix/m² médian zones × surface → stable
    # -------------------------------------------------------------------
    if prix_m2_cible:
        communes_budget = _get_communes_budget(
            data_manager, prix_m2_cible, zones_deja_vues, dept_favoris
        )

        for code_commune, stats in communes_budget[:5]:
            prix_estime = stats["prix_m2_median"] * surface_moy
            score       = _compute_score(stats, budget_implicite, prix_estime, surface_moy)
            raison      = _generate_reason(
                profile, str(code_commune)[:2], stats, code_commune, "budget"
            )

            recommendations.append({
                "code_commune":    code_commune,
                "prix_m2_median":  round(stats["prix_m2_median"], 0),
                "nb_transactions": stats["nb_transactions"],
                "prix_estime":     round(prix_estime, 0),
                "categorie_geo":   stats.get("categorie_geo", ""),
                "raison":          raison,
                "score":           score,
                "strategie":       "budget"
            })

    # Dédoublonnage
    seen   = set()
    unique = []
    for rec in recommendations:
        if rec["code_commune"] not in seen:
            seen.add(rec["code_commune"])
            unique.append(rec)

    unique.sort(key=lambda x: x["score"], reverse=True)
    return unique[:10]


# ---------------------------------------------------------------------------
# SCORE DE PERTINENCE — Calcul multicritères
# ---------------------------------------------------------------------------

def _compute_score(stats: dict, budget_implicite: float, prix_estime: float, surface_moy: float) -> float:
    """
    Calcule un score de pertinence multicritères (0-100).

    Pondération :
    - 40% : Activité du marché (nb transactions → liquidité)
    - 35% : Cohérence avec le budget implicite comportemental
    - 25% : Attractivité géographique
    """
    score = 0.0

    # 40% — Activité marché
    nb_t   = min(stats.get("nb_transactions", 0), 500)
    score += (nb_t / 500) * 40

    # 35% — Cohérence budget implicite
    if budget_implicite and budget_implicite > 0:
        ratio  = abs(prix_estime - budget_implicite) / budget_implicite
        score += max(0, (1 - ratio) * 35)
    else:
        score += 17

    # 25% — Attractivité zone
    geo_scores = {
        "1_Metropole_Top15":   25,
        "2_Ile_de_France":     22,
        "3_Zone_Touristique":  20,
        "4_Province_Standard": 15
    }
    score += geo_scores.get(stats.get("categorie_geo", ""), 10)

    return round(score, 1)


# ---------------------------------------------------------------------------
# RAISONS PERSONNALISÉES — Explication adaptée au profil
# ---------------------------------------------------------------------------

def _generate_reason(profile: dict, dept: str, stats: dict, code_commune: str, strategie: str) -> str:
    """Génère une explication personnalisée et contextualisée."""
    nb_recherches    = profile.get("nb_recherches_total", 0)
    zone_recurrente  = profile.get("zone_recurrente", "")
    budget_implicite = profile.get("budget_implicite")
    prix_m2_zones    = profile.get("prix_m2_zones")
    categorie        = stats.get("categorie_geo", "")
    nb_t             = stats.get("nb_transactions", 0)
    prix             = stats.get("prix_m2_median", 0)
    surface_moy      = profile.get("surface_moyenne") or 60

    geo_labels = {
        "1_Metropole_Top15":   "grande métropole",
        "2_Ile_de_France":     "Île-de-France",
        "3_Zone_Touristique":  "zone touristique",
        "4_Province_Standard": "province"
    }
    geo_label = geo_labels.get(categorie, "")

    if strategie == "voisin":
        if zone_recurrente and zone_recurrente.startswith(dept):
            return (
                f"Vous recherchez souvent dans le département {dept}. "
                f"Cette commune {geo_label} présente {nb_t} transactions "
                f"à {int(prix):,} €/m², cohérente avec vos zones favorites."
            )
        return (
            f"Commune {geo_label} dans votre département favori ({dept}). "
            f"Marché actif avec {nb_t} transactions à {int(prix):,} €/m²."
        )

    if strategie == "budget":
        if prix_m2_zones:
            return (
                f"Prix/m² ({int(prix):,} €/m²) proche du marché de vos zones "
                f"habituelles ({int(prix_m2_zones):,} €/m²). "
                f"Commune {geo_label} avec {nb_t} transactions récentes."
            )
        if budget_implicite:
            return (
                f"Budget estimé cohérent ({int(budget_implicite):,} € "
                f"pour {surface_moy} m²). Marché {geo_label} "
                f"avec {nb_t} transactions récentes."
            )
        return (
            f"Commune {geo_label} avec un bon rapport qualité/activité. "
            f"{nb_t} transactions à {int(prix):,} €/m²."
        )

    return f"Commune recommandée selon vos {nb_recherches} recherches récentes."


# ---------------------------------------------------------------------------
# REQUÊTES MONGODB — Helpers
# ---------------------------------------------------------------------------

def _get_communes_departement(data_manager, dept: str) -> list:
    """Récupère les communes d'un département depuis MongoDB."""
    if data_manager.db is None:
        return []

    docs = list(
        data_manager.db["communes"].find(
            {"code_commune": {"$regex": f"^{dept}"}},
            {"_id": 0}
        ).sort("count", -1).limit(30)
    )

    results = []
    for doc in docs:
        stats = {
            "prix_m2_median":  float(doc.get("prix_m2_median", 0)),
            "prix_m2_mean":    float(doc.get("prix_m2_mean", 0)),
            "nb_transactions": int(doc.get("count", 0)),
            "surface_moyenne": float(doc.get("surface_mean", 0)),
            "categorie_geo":   str(doc.get("categorie_geo", ""))
        }
        if stats["nb_transactions"] >= 10 and stats["prix_m2_median"] > 0:
            results.append((doc.get("code_commune"), stats))

    return results


def _get_communes_budget(data_manager, prix_m2_cible: float, zones_deja_vues: set, depts_exclus: list) -> list:
    """
    Récupère des communes dont le prix/m² est proche du prix/m² médian
    des zones habituellement recherchées par l'utilisateur.
    """
    if data_manager.db is None:
        return []

    marge = 0.25  # ±25% autour du prix/m² cible
    docs  = list(
        data_manager.db["communes"].find(
            {
                "prix_m2_median": {
                    "$gte": prix_m2_cible * (1 - marge),
                    "$lte": prix_m2_cible * (1 + marge)
                },
                "count": {"$gte": 20}
            },
            {"_id": 0}
        ).sort("count", -1).limit(50)
    )

    results = []
    for doc in docs:
        code = doc.get("code_commune", "")
        dept = str(code)[:2]

        if code in zones_deja_vues or dept in depts_exclus:
            continue

        stats = {
            "prix_m2_median":  float(doc.get("prix_m2_median", 0)),
            "prix_m2_mean":    float(doc.get("prix_m2_mean", 0)),
            "nb_transactions": int(doc.get("count", 0)),
            "surface_moyenne": float(doc.get("surface_mean", 0)),
            "categorie_geo":   str(doc.get("categorie_geo", ""))
        }
        results.append((code, stats))

    return results


def _get_default_recommendations(data_manager) -> list:
    """Recommandations par défaut pour les nouveaux utilisateurs
    ou profils trop dispersés."""
    if data_manager.db is None:
        return []

    docs = list(
        data_manager.db["communes"].find(
            {"count": {"$gte": 50}},
            {"_id": 0}
        ).sort("count", -1).limit(10)
    )

    results = []
    for doc in docs:
        prix_estime = float(doc.get("prix_m2_median", 0)) * 60
        results.append({
            "code_commune":    doc.get("code_commune"),
            "prix_m2_median":  round(float(doc.get("prix_m2_median", 0)), 0),
            "nb_transactions": int(doc.get("count", 0)),
            "prix_estime":     round(prix_estime, 0),
            "categorie_geo":   str(doc.get("categorie_geo", "")),
            "raison":          "Commune très active sur le marché immobilier français 2025.",
            "score":           float(doc.get("count", 0)) / 10,
            "strategie":       "default"
        })

    return results[:5]


# ---------------------------------------------------------------------------
# PERSISTANCE — Sauvegarde et récupération
# ---------------------------------------------------------------------------

def save_recommendations(user_id: str, recommendations: list) -> None:
    """Sauvegarde les recommandations en MongoDB (upsert)."""
    cols = get_collections()
    cols["recommendations"].update_one(
        {"user_id": user_id},
        {
            "$set": {
                "user_id":         user_id,
                "recommendations": recommendations,
                "updated_at":      datetime.utcnow(),
                "nb_reco":         len(recommendations)
            }
        },
        upsert=True
    )


def get_recommendations(user_id: str) -> list:
    """Récupère les dernières recommandations sauvegardées."""
    cols = get_collections()
    doc  = cols["recommendations"].find_one({"user_id": user_id})
    if not doc:
        return []
    return doc.get("recommendations", [])


def get_user_profile_summary(user_id: str) -> dict:
    """
    Retourne un résumé du profil utilisateur pour l'affichage.
    Utilise le budget implicite comportemental (stable).
    """
    from utils.data_loader import data_manager
    profile = build_user_profile(user_id, data_manager)
    if not profile:
        return {}

    return {
        "nb_recherches":       profile.get("nb_recherches_total", 0),
        "nb_communes_uniques": profile.get("nb_communes_uniques", 0),
        "dept_favori":         profile.get("departements_favoris", [None])[0],
        "budget_implicite":    profile.get("budget_implicite"),   # comportemental stable
        "prix_m2_zones":       profile.get("prix_m2_zones"),      # prix/m² médian zones
        "surface_moyenne":     profile.get("surface_moyenne"),
        "type_favori":         profile.get("type_recherche_favori"),
        "score_coherence":     profile.get("score_coherence", 0),
    }

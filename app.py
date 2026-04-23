"""
Application Flask principale pour l'analyse immobilière.
"""
import os
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from bson import ObjectId

from utils import data_manager, PriceEstimator
from utils.clustering import (
    analyze_departement, get_cluster_profiles, get_cluster_name,
    get_cluster_description, get_cluster_explanation, get_cluster_stats
)
from utils.opportunities import detect_opportunities
from utils.db import get_db, init_indexes
from utils.auth import User, register_user, login_user_auth, bcrypt, update_user_preferences
from utils.recommendations import (
    save_search, get_search_history,
    generate_recommendations, save_recommendations, get_recommendations
)

# ---------------------------------------------------------------------------
# Initialisation de l'application
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

# Initialisation des extensions
bcrypt.init_app(app)

login_manager = LoginManager(app)


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


login_manager.login_view = "login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


# ---------------------------------------------------------------------------
# Chargement des données et initialisation MongoDB
# ---------------------------------------------------------------------------

print("[App] Démarrage de l'application...")
get_db()
init_indexes()
data_manager.load_all()
estimator = PriceEstimator(data_manager)
print("[App] Application prête")


# ---------------------------------------------------------------------------
# Routes d'authentification
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """Page d'inscription."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        result = register_user(username, email, password)

        if not result["success"]:
            flash(result["error"], "danger")
            return render_template("register.html")

        flash("Compte créé avec succès. Vous pouvez vous connecter.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Page de connexion."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        result = login_user_auth(email, password)

        if not result["success"]:
            flash(result["error"], "danger")
            return render_template("login.html")

        login_user(result["user"])
        next_page = request.args.get("next")
        return redirect(next_page or url_for("index"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    """Déconnexion de l'utilisateur."""
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    """Page de profil utilisateur avec historique et recommandations."""
    history = get_search_history(current_user.id, limit=20)
    recommendations = get_recommendations(current_user.id)
    return render_template(
        "profile.html",
        user=current_user,
        history=history,
        recommendations=recommendations
    )


@app.route("/api/profile/preferences", methods=["POST"])
@login_required
def api_update_preferences():
    """API pour mettre à jour les préférences utilisateur."""
    try:
        data = request.get_json()
        preferences = {
            "zones_favorites": data.get("zones_favorites", []),
            "budget_min": data.get("budget_min"),
            "budget_max": data.get("budget_max"),
            "surface_min": data.get("surface_min"),
            "nb_pieces_prefere": data.get("nb_pieces_prefere")
        }
        success = update_user_preferences(current_user.id, preferences)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/recommendations/refresh", methods=["POST"])
@login_required
def api_refresh_recommendations():
    """Régénère les recommandations pour l'utilisateur connecté."""
    try:
        recommendations = generate_recommendations(current_user.id, data_manager)
        save_recommendations(current_user.id, recommendations)
        return jsonify({"success": True, "recommendations": recommendations})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Routes principales
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    """Landing si non connecté, dashboard si connecté."""
    if current_user.is_authenticated:
        return render_template("index.html")
    return render_template("landing.html")


@app.route("/clusters")
@login_required
def clusters():
    """Page des profils de clusters."""
    return render_template("clusters.html")


@app.route("/estimation")
@login_required
def estimation():
    """Onglet 1 : Estimation de bien."""
    return render_template("estimation.html")


@app.route("/analyse-marche")
@login_required
def analyse_marche():
    """Onglet 2 : Analyse de marché par zone."""
    return render_template("analyse_marche.html")


@app.route("/cartographie")
@login_required
def cartographie():
    """Onglet 3 : Cartographie interactive."""
    return render_template("cartographie.html")


@app.route("/similaires")
@login_required
def similaires():
    """Onglet 4 : Biens similaires."""
    return render_template("similaires.html")


@app.route("/opportunites")
@login_required
def opportunites():
    """Onglet 5 : Détection d'opportunités avec Isolation Forest."""
    return render_template("opportunites.html")


# ---------------------------------------------------------------------------
# API immobilières
# ---------------------------------------------------------------------------

@app.route("/api/estimate", methods=["POST"])
def api_estimate():
    """API pour l'estimation de prix."""
    try:
        data = request.get_json()
        surface = float(data.get("surface", 0))
        nb_pieces = float(data.get("nb_pieces", 0))
        code_commune = data.get("code_commune", "").strip()

        if not code_commune or surface <= 0:
            return jsonify({"success": False, "error": "Données invalides"}), 400

        result = estimator.estimate_price(surface, nb_pieces, code_commune)

        if current_user.is_authenticated and result.get("success"):
            save_search(current_user.id, "estimation", {
                "code_commune": code_commune,
                "surface": surface,
                "nb_pieces": nb_pieces,
                "prix_estime": result.get("prix_estime")
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analyse-departement/<code_dept>")
def api_analyse_departement(code_dept):
    """API pour l'analyse d'un département."""
    try:
        dept_df = data_manager.get_departement_stats(code_dept)
        if dept_df.empty:
            return jsonify({"error": "Aucune donnée trouvée pour ce département"}), 404

        stats = analyze_departement(dept_df, code_dept)

        if current_user.is_authenticated:
            save_search(current_user.id, "marche", {"code_dept": code_dept})

        return jsonify(stats)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/top-communes/<code_dept>")
def api_top_communes(code_dept):
    """API pour les communes les plus actives d'un département."""
    try:
        dept_data = data_manager.get_departement_stats(code_dept)

        if dept_data.empty:
            return jsonify([]), 200

        top_communes = dept_data["code_commune"].value_counts().head(20)

        results = []
        for code_commune, count in top_communes.items():
            commune_data = dept_data[dept_data["code_commune"] == code_commune]
            results.append({
                "code_commune": str(code_commune),
                "nb_transactions": int(count),
                "prix_m2_median": float(round(commune_data["prix_m2"].median(), 0)),
                "surface_moyenne": float(round(commune_data["surface_reelle_bati"].mean(), 1))
            })

        return jsonify(results)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/cluster-info/<int:cluster_id>")
def api_cluster_info(cluster_id):
    """API pour obtenir les informations détaillées d'un cluster."""
    try:
        return jsonify({
            "name": get_cluster_name(cluster_id),
            "description": get_cluster_description(cluster_id),
            "stats": get_cluster_stats(cluster_id),
            "general_explanation": get_cluster_explanation()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/map-data")
def api_map_data():
    """API pour les données de la carte (échantillon)."""
    try:
        docs = list(data_manager.db["properties"].aggregate([
            {
                "$sample": {
                    "size": 5000
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "latitude": 1,
                    "longitude": 1,
                    "prix_m2": 1,
                    "cluster_kmeans": 1,
                    "code_commune": 1
                }
            }
        ]))

        if not docs:
            return jsonify({"error": "Données non chargées"}), 500

        sample = pd.DataFrame(docs)

        data = {
            "latitudes": sample["latitude"].tolist(),
            "longitudes": sample["longitude"].tolist(),
            "prix_m2": sample["prix_m2"].tolist(),
            "clusters": sample["cluster_kmeans"].tolist() if "cluster_kmeans" in sample.columns else [],
            "communes": sample["code_commune"].tolist()
        }

        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/find-similar", methods=["POST"])
def api_find_similar():
    """API pour trouver des biens similaires."""
    try:
        data = request.get_json()
        surface = float(data.get("surface", 0))
        nb_pieces = float(data.get("nb_pieces", 0))
        code_commune = data.get("code_commune", "").strip()

        if not code_commune or surface <= 0:
            return jsonify({"success": False, "error": "Données invalides"}), 400

        similar_df = estimator.find_similar_properties(
            surface, nb_pieces, code_commune, max_results=20
        )

        results = []
        for _, row in similar_df.iterrows():
            results.append({
                "code_commune": row.get("code_commune", ""),
                "prix": float(row.get("valeur_fonciere", 0)),
                "surface": float(row.get("surface_reelle_bati", 0)),
                "nb_pieces": float(row.get("nombre_pieces_principales", 0)),
                "prix_m2": float(row.get("prix_m2", 0)),
                "standing": row.get("standing_relative", "N/A"),
                "latitude": float(row.get("latitude", 0)),
                "longitude": float(row.get("longitude", 0))
            })

        if current_user.is_authenticated:
            save_search(current_user.id, "similaires", {
                "code_commune": code_commune,
                "surface": surface,
                "nb_pieces": nb_pieces
            })

        return jsonify({"success": True, "results": results})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/opportunities", methods=["POST"])
def api_opportunities():
    """API pour détecter les opportunités d'investissement."""
    try:
        data = request.get_json()
        contamination = float(data.get("contamination", 0.02))
        max_ratio = float(data.get("max_ratio", 0.85))
        zone_filter = data.get("zone_filter", "all")

        if not (0.01 <= contamination <= 0.10):
            return jsonify({
                "success": False,
                "error": "La contamination doit être comprise entre 0.01 et 0.10"
            }), 400

        docs = list(data_manager.db["properties"].find({}, {"_id": 0}))
        df_reference = pd.DataFrame(docs)

        result = detect_opportunities(
            df_reference,
            contamination=contamination,
            max_ratio=max_ratio,
            zone_filter=zone_filter,
            top_n=50
        )

        if current_user.is_authenticated:
            save_search(current_user.id, "opportunites", {
                "contamination": contamination,
                "zone_filter": zone_filter
            })

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search-communes")
def api_search_communes():
    """API pour la recherche de communes."""
    query = request.args.get("q", "")

    if len(query) < 2:
        return jsonify([])

    results = data_manager.search_communes(query, limit=15)
    return jsonify(results)


@app.route("/api/departements")
def api_departements():
    """API pour la liste des départements."""
    departements = [
        {"code": "01", "nom": "Ain"},
        {"code": "02", "nom": "Aisne"},
        {"code": "06", "nom": "Alpes-Maritimes"},
        {"code": "13", "nom": "Bouches-du-Rhône"},
        {"code": "33", "nom": "Gironde"},
        {"code": "34", "nom": "Hérault"},
        {"code": "35", "nom": "Ille-et-Vilaine"},
        {"code": "38", "nom": "Isère"},
        {"code": "44", "nom": "Loire-Atlantique"},
        {"code": "59", "nom": "Nord"},
        {"code": "69", "nom": "Rhône"},
        {"code": "75", "nom": "Paris"},
        {"code": "76", "nom": "Seine-Maritime"},
        {"code": "83", "nom": "Var"},
        {"code": "92", "nom": "Hauts-de-Seine"},
        {"code": "93", "nom": "Seine-Saint-Denis"},
        {"code": "94", "nom": "Val-de-Marne"},
    ]
    return jsonify(departements)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
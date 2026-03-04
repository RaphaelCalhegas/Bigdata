"""
Application Flask principale pour l'analyse immobilière.
"""
from flask import Flask, render_template, request, jsonify
import json
from utils import data_manager, PriceEstimator
from utils.clustering import analyze_departement, get_cluster_profiles, get_cluster_name, get_cluster_description, get_cluster_explanation, get_cluster_stats
from utils.opportunities import detect_opportunities

app = Flask(__name__)
app.config['SECRET_KEY'] = 'votre-cle-secrete-ici'

# Chargement des données au démarrage
print("🚀 Démarrage de l'application...")
data_manager.load_all()
estimator = PriceEstimator(data_manager)
print("✅ Application prête!")


@app.route('/')
def index():
    """Page d'accueil principale."""
    return render_template('index.html')


@app.route('/clusters')
def clusters():
    """Page des profils de clusters."""
    return render_template('clusters.html')


@app.route('/estimation')
def estimation():
    """Onglet 1 : Estimation de bien."""
    return render_template('estimation.html')


@app.route('/api/estimate', methods=['POST'])
def api_estimate():
    """API pour l'estimation de prix."""
    try:
        data = request.get_json()
        
        surface = float(data.get('surface', 0))
        nb_pieces = float(data.get('nb_pieces', 0))
        code_commune = data.get('code_commune', '').strip()
        
        if not code_commune or surface <= 0:
            return jsonify({'success': False, 'error': 'Données invalides'}), 400
        
        result = estimator.estimate_price(surface, nb_pieces, code_commune)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/analyse-marche')
def analyse_marche():
    """Onglet 2 : Analyse de marché par zone."""
    return render_template('analyse_marche.html')


@app.route('/api/analyse-departement/<code_dept>')
def api_analyse_departement(code_dept):
    """API pour l'analyse d'un département."""
    try:
        if data_manager.df_reference is None:
            return jsonify({'error': 'Données non chargées'}), 500
        
        stats = analyze_departement(data_manager.df_reference, code_dept)
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/top-communes/<code_dept>')
def api_top_communes(code_dept):
    """API pour les communes les plus actives d'un département."""
    try:
        if data_manager.df_reference is None:
            return jsonify([]), 500
        
        dept_data = data_manager.df_reference[
            data_manager.df_reference['code_commune'].str.startswith(code_dept)
        ]
        
        # Top 10 communes par nb de transactions
        top_communes = dept_data['code_commune'].value_counts().head(10)
        
        results = []
        for code_commune, count in top_communes.items():
            commune_data = dept_data[dept_data['code_commune'] == code_commune]
            results.append({
                'code_commune': str(code_commune),
                'nb_transactions': int(count),
                'prix_m2_median': float(round(commune_data['prix_m2'].median(), 0)),
                'surface_moyenne': float(round(commune_data['surface_reelle_bati'].mean(), 1))
            })
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/cluster-info/<int:cluster_id>')
def api_cluster_info(cluster_id):
    """API pour obtenir les informations détaillées d'un cluster."""
    try:
        return jsonify({
            'name': get_cluster_name(cluster_id),
            'description': get_cluster_description(cluster_id),
            'stats': get_cluster_stats(cluster_id),
            'general_explanation': get_cluster_explanation()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/cartographie')
def cartographie():
    """Onglet 3 : Cartographie interactive."""
    return render_template('cartographie.html')


@app.route('/api/map-data')
def api_map_data():
    """API pour les données de la carte (échantillon)."""
    try:
        if data_manager.df_reference is None:
            return jsonify({'error': 'Données non chargées'}), 500
        
        # On prend un échantillon pour ne pas surcharger
        sample = data_manager.df_reference.sample(min(5000, len(data_manager.df_reference)))
        
        data = {
            'latitudes': sample['latitude'].tolist(),
            'longitudes': sample['longitude'].tolist(),
            'prix_m2': sample['prix_m2'].tolist(),
            'clusters': sample['cluster_kmeans'].tolist() if 'cluster_kmeans' in sample.columns else [],
            'communes': sample['code_commune'].tolist()
        }
        
        return jsonify(data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/similaires')
def similaires():
    """Onglet 4 : Biens similaires."""
    return render_template('similaires.html')


@app.route('/opportunites')
def opportunites():
    """Onglet 5 : Détection d'opportunités avec Isolation Forest."""
    return render_template('opportunites.html')


@app.route('/api/find-similar', methods=['POST'])
def api_find_similar():
    """API pour trouver des biens similaires."""
    try:
        data = request.get_json()
        
        surface = float(data.get('surface', 0))
        nb_pieces = float(data.get('nb_pieces', 0))
        code_commune = data.get('code_commune', '').strip()
        
        if not code_commune or surface <= 0:
            return jsonify({'success': False, 'error': 'Données invalides'}), 400
        
        similar_df = estimator.find_similar_properties(
            surface, nb_pieces, code_commune, max_results=10
        )
        
        # Conversion en dict pour JSON
        results = []
        for idx, row in similar_df.iterrows():
            results.append({
                'code_commune': row.get('code_commune', ''),
                'prix': float(row.get('valeur_fonciere', 0)),
                'surface': float(row.get('surface_reelle_bati', 0)),
                'nb_pieces': float(row.get('nombre_pieces_principales', 0)),
                'prix_m2': float(row.get('prix_m2', 0)),
                'standing': row.get('standing_relative', 'N/A'),
                'latitude': float(row.get('latitude', 0)),
                'longitude': float(row.get('longitude', 0))
            })
        
        return jsonify({'success': True, 'results': results})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/opportunities', methods=['POST'])
def api_opportunities():
    """API pour détecter les opportunités d'investissement."""
    try:
        data = request.get_json()
        
        contamination = float(data.get('contamination', 0.02))
        max_ratio = float(data.get('max_ratio', 0.85))
        zone_filter = data.get('zone_filter', 'all')
        
        # Validation
        if not (0.01 <= contamination <= 0.10):
            return jsonify({'success': False, 'error': 'Contamination doit être entre 0.01 et 0.10'}), 400
        
        # Détection
        result = detect_opportunities(
            data_manager.df_reference,
            contamination=contamination,
            max_ratio=max_ratio,
            zone_filter=zone_filter,
            top_n=50
        )
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Erreur opportunités: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/search-communes')
def api_search_communes():
    """API pour la recherche de communes."""
    query = request.args.get('q', '')
    
    if len(query) < 2:
        return jsonify([])
    
    results = data_manager.search_communes(query, limit=15)
    return jsonify(results)


@app.route('/api/departements')
def api_departements():
    """API pour la liste des départements."""
    # Liste des départements français
    departements = [
        {'code': '01', 'nom': 'Ain'},
        {'code': '02', 'nom': 'Aisne'},
        {'code': '06', 'nom': 'Alpes-Maritimes'},
        {'code': '13', 'nom': 'Bouches-du-Rhône'},
        {'code': '33', 'nom': 'Gironde'},
        {'code': '34', 'nom': 'Hérault'},
        {'code': '35', 'nom': 'Ille-et-Vilaine'},
        {'code': '38', 'nom': 'Isère'},
        {'code': '44', 'nom': 'Loire-Atlantique'},
        {'code': '59', 'nom': 'Nord'},
        {'code': '69', 'nom': 'Rhône'},
        {'code': '75', 'nom': 'Paris'},
        {'code': '76', 'nom': 'Seine-Maritime'},
        {'code': '83', 'nom': 'Var'},
        {'code': '92', 'nom': 'Hauts-de-Seine'},
        {'code': '93', 'nom': 'Seine-Saint-Denis'},
        {'code': '94', 'nom': 'Val-de-Marne'},
        # Ajouter les autres si besoins
    ]
    return jsonify(departements)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

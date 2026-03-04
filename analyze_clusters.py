"""
Script pour analyser et caractériser les 6 clusters du modèle K-Means.
"""
import pandas as pd
import pickle
import numpy as np

# Charger les données
print("📂 Chargement des données...")
with open('models/df_reference.pkl', 'rb') as f:
    df = pickle.load(f)

print(f"✅ {len(df):,} transactions chargées")
print(f"✅ {df['cluster_kmeans'].nunique()} clusters détectés\n")

# Analyser chaque cluster
for cluster_id in sorted(df['cluster_kmeans'].unique()):
    cluster_data = df[df['cluster_kmeans'] == cluster_id]
    n_biens = len(cluster_data)
    pct = (n_biens / len(df)) * 100
    
    print(f"\n{'='*80}")
    print(f"🔹 CLUSTER {cluster_id} - {n_biens:,} biens ({pct:.1f}% du total)")
    print(f"{'='*80}")
    
    # Caractéristiques numériques
    print("\n📊 Caractéristiques Numériques (moyennes):")
    print(f"  • Prix m²:           {cluster_data['prix_m2'].mean():,.0f} € (médiane: {cluster_data['prix_m2'].median():,.0f} €)")
    print(f"  • Surface:           {cluster_data['surface_reelle_bati'].mean():.1f} m² (médiane: {cluster_data['surface_reelle_bati'].median():.1f} m²)")
    print(f"  • Nombre de pièces:  {cluster_data['nombre_pieces_principales'].mean():.1f} (médiane: {cluster_data['nombre_pieces_principales'].median():.1f})")
    print(f"  • Valeur foncière:   {cluster_data['valeur_fonciere'].mean():,.0f} € (médiane: {cluster_data['valeur_fonciere'].median():,.0f} €)")
    
    # Géographie
    print("\n🗺️ Localisation:")
    print(f"  • Latitude moy.:     {cluster_data['latitude'].mean():.4f}")
    print(f"  • Longitude moy.:    {cluster_data['longitude'].mean():.4f}")
    
    # Standing dominant
    if 'standing_relative' in cluster_data.columns:
        standing_counts = cluster_data['standing_relative'].value_counts()
        standing_dominant = standing_counts.index[0]
        standing_pct = (standing_counts.iloc[0] / n_biens) * 100
        print(f"\n⭐ Standing dominant: {standing_dominant} ({standing_pct:.1f}%)")
        print("  Répartition:")
        for standing, count in standing_counts.head(3).items():
            pct_s = (count / n_biens) * 100
            print(f"    - {standing}: {count:,} ({pct_s:.1f}%)")
    
    # Zone géographique dominante
    if 'categorie_geo' in cluster_data.columns:
        geo_counts = cluster_data['categorie_geo'].value_counts()
        geo_dominant = geo_counts.index[0]
        geo_pct = (geo_counts.iloc[0] / n_biens) * 100
        print(f"\n🌍 Zone dominante: {geo_dominant} ({geo_pct:.1f}%)")
    
    # Top 5 départements
    if 'code_commune' in cluster_data.columns:
        cluster_data['dept'] = cluster_data['code_commune'].astype(str).str[:2]
        top_depts = cluster_data['dept'].value_counts().head(5)
        print("\n📍 Top 5 Départements:")
        for dept, count in top_depts.items():
            pct_d = (count / n_biens) * 100
            print(f"    - {dept}: {count:,} ({pct_d:.1f}%)")
    
    # Quartiles prix
    print("\n💰 Distribution Prix m²:")
    q25 = cluster_data['prix_m2'].quantile(0.25)
    q50 = cluster_data['prix_m2'].quantile(0.50)
    q75 = cluster_data['prix_m2'].quantile(0.75)
    print(f"    Q1 (25%): {q25:,.0f} €")
    print(f"    Q2 (50%): {q50:,.0f} €")
    print(f"    Q3 (75%): {q75:,.0f} €")

print("\n\n" + "="*80)
print("✅ Analyse terminée !")
print("="*80)

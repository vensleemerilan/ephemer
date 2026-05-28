import pandas as pd
import psycopg2 #lib pour les operations en bd sql
from psycopg2.extras import execute_values #pour aller vite selon gemini
from tqdm import tqdm
import subprocess #pour l'enregistrement en gpkg
import os
import time

#CONFIGURATION
#input_csv = r"/home/vmerilan/Documents/VMerilan/scripts/algo_traitement_v1/test_echantillon/donnees_normalisees.csv"
input_csv = r"./individus_normalises.csv"
output_path_artist = "./correspondances_artist.gpkg"
#output_path_artist = r"/home/vmerilan/Documents/VMerilan/scripts/algo_traitement_v1/test_echantillon/correspondances_artist.gpkg"
output_path_printer = "./correspondances_printer.gpkg"
#output_path_printer = r"/home/vmerilan/Documents/VMerilan/scripts/algo_traitement_v1/test_echantillon/correspondances_printer.gpkg"

#paramètres de la base de donnée
db_params = {
    "host": "localhost",
    "dbname": "testing_adresses",
    "port": 5434,
    "user": "postgres",
    "password": "postgres"
}

#Ligne universelle d'appel de la base de donnée
db_config_ogr = f"PG:host={db_params['host']} dbname={db_params['dbname']} port={db_params['port']} user={db_params['user']} password={db_params['password']} active_schema=testing"

def safe_int(value, default):
    """Convertit en int en gérant les chaînes vides ou NaN."""
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return default

#Debut du script
start_time = time.perf_counter()

try:
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    print("Nettoyage des tables de travail:")
    #Liste des tables à nettoyer 
    tables_to_clear = [
        "testing.candidates_artist", 
        "testing.candidates_printer",
        "testing.candidates_spatial_cluster_points_artist", 
        "testing.candidates_spatial_cluster_points_printer",
        "testing.ranked_candidates_artist", 
        "testing.ranked_candidates_printer",
        "testing.points_table_artist",
        "testing.points_table_printer" 
    ]
    for table in tables_to_clear:
        try:
            # On utilise TRUNCATE pour vider sans supprimer la structure pour eviter les erreurs la table unetelle n'exite pas
            cur.execute(f"TRUNCATE TABLE {table} CASCADE;")
        except psycopg2.errors.UndefinedTable:
            # Si la table n'existe pas (car la fonction n'a jamais tourné), on l'ignore
            conn.rollback() # Important : on reset la transaction après une erreur
            print(f"Note : {table} n'existe pas encore, elle sera créée par les fonctions.")
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors du nettoyage de {table} : {e}")
    
    conn.commit()
    #CHARGEMENT CSV
    df = pd.read_csv(input_csv).fillna('') #Remplacer toutes les cellules vides par un str vide, notemment pour les cas ou il n'y aurait pas de prenom

    def clean_date_to_year(value):
        # On convertit en string pour manipuler uniformément
        val_str = str(value).strip()
        
        if not val_str or val_str.lower() == 'nan':
            return None # Sera géré par safe_int plus tard (ex: 1800)

        # Cas 1 : C'est déjà une année seule (4 chiffres exactement)
        if len(val_str) == 4 and val_str.isdigit():
            return int(val_str)
        
        # Cas 2 : C'est une date longue (ex: 1848-06-28)
        try:
            # pd.to_datetime est intelligent et extraira l'année
            return pd.to_datetime(val_str, errors='coerce').year
        except:
            return None

    # Application du nettoyage
    df['debut'] = df['debut'].apply(clean_date_to_year)
    df['fin'] = df['fin'].apply(clean_date_to_year)
    #TRAITEMENT fractionné PAR TYPE
    process_config = [
        {
            "type": "dessinateur",
            "func_data": "testing.getCandidatesData_artist",
            "func_cluster_pts": "testing.get_candidates_data_spatial_cluster_artist",
            "func_summary": "testing.get_candidates_clusters_artist",
            "func_classify": "testing.classify_candidates_artist",
            "func_rank": "testing.rank_candidates_artist",
            "func_pts_in_clustr" : "testing.create_points_table_artist",
            "table_init": "testing.candidates_artist",
            "table_pts": "testing.candidates_spatial_cluster_points_artist"
        },
        {
            "type": "imprimeur",
            "func_data": "testing.getCandidatesData_printer",
            "func_cluster_pts": "testing.get_candidates_data_spatial_cluster_printer",
            "func_summary": "testing.get_candidates_clusters_printer",
            "func_classify": "testing.classify_candidates_printer",
            "func_rank": "testing.rank_candidates_printer",
            "func_pts_in_clustr" : "testing.create_points_table_printer",
            "table_init": "testing.candidates_printer",
            "table_pts": "testing.candidates_spatial_cluster_points_printer"
        }
    ]
#Traite les individus selon leur type, en reference a chaque cfg il traite 2 groupes differents
    for cfg in process_config:
        df_sub = df[df['type'].str.lower() == cfg['type']]
        if df_sub.empty:
            continue

        print(f"\n>>> Traitement des {cfg['type']}s ({len(df_sub)} individus)...")
        
        #Étape A: Extraction initiale
        print("Extraction initiale en cours (Batch)...")
        for _, row in tqdm(df_sub.iterrows(), total=len(df_sub), desc="Extraction"):
            debut = safe_int(row['debut'], 1800)
            fin = safe_int(row['fin'], 1950)
            cur.execute(
                f"INSERT INTO {cfg['table_init']} SELECT * FROM {cfg['func_data']}(%s, %s, %s, %s, %s)", 
                (row['uri'], row['nom'], row.get('prenom', ''), debut, fin)
            )
        conn.commit()

        #Étape B: Clustering spatial des points
        cur.execute(f"SELECT DISTINCT surname_searched, first_name_searched FROM {cfg['table_init']}")
        noms_extraits = cur.fetchall()
        for nom, prenom in tqdm(noms_extraits, desc="Clustering Spatial"):
            cur.execute(f"INSERT INTO {cfg['table_pts']} SELECT * FROM {cfg['func_cluster_pts']}(%s, %s)", (nom, prenom))
        
        #Étape C: Synthèse, Classification et Ranking
        print(f"Finalisation (Synthèse, Classification, Ranking)...")
        cur.execute(f"SELECT {cfg['func_summary']}();")
        cur.execute(f"SELECT {cfg['func_classify']}();")
        cur.execute(f"SELECT {cfg['func_rank']}();")
        cur.execute(f"SELECT {cfg['func_pts_in_clustr']}();")
        conn.commit()
    #EXPORT CSV (PANDAS)
    print("\nExportation des résultats en CSV...")

    csv_exports = [
        {
            "label": "Points in clustrs Artistes",
            "table": "testing.points_table_artist",
            "filename": "./points_artist.csv"
        },
        {
            "label": "Points in clustrs Imprimeurs",
            "table": "testing.points_table_printer",
            "filename": "./points_printer.csv"
        }
    ]
         
    for item in csv_exports:
        try:
            print(f"Export de {item['label']}...")
            query = f"SELECT *, ST_AsText(geom) as geom_wkt FROM {item['table']}"
            df_export = pd.read_sql_query(query, conn)
            if not df_export.empty:
                df_export.to_csv(item['filename'], index=False, sep=',', encoding='utf-8')
                print(f"Succès : {item['filename']} créé.")
            else:
                print(f"Info : {item['label']} - La table est vide, aucun fichier généré.")
        except Exception as csv_e:
            print(f"Erreur lors de l'export de {item['label']} : {csv_e}")

    #FUSION DES TABLES POUR R2RML
    print("\nFusion des tables artistes et imprimeurs pour le mapping...")
    try:
        #On appelle la fonction de fusion
        cur.execute("SELECT testing.merge_tables();")
        #CRUCIAL : On valide la transaction pour que le Parser R2RML puisse voir les données
        conn.commit() 
        print("Succès : Table finale fusionnée et prête pour R2RML.")
    except Exception as merge_e:
        print(f"Erreur lors de la fusion des tables : {merge_e}")
        conn.rollback()

except Exception as e:
    print(f"\nERREUR CRITIQUE SQL : {e}")
    if 'conn' in locals(): conn.rollback()
    exit()
finally:
    if 'conn' in locals():
        cur.close()
        conn.close()

#EXPORT GEOPACKAGE (OGR2OGR)
print("\nExportation vers GeoPackage...")

exports = [
    {
        "label": "Artistes",
        "file": output_path_artist,
        "t_ranked": "testing.ranked_candidates_artist",
        "t_points": "testing.candidates_spatial_cluster_points_artist",
        "l_ranked": "clusters_classes_artist",
        "l_points": "points_bruts_artist"
    },
    {
        "label": "Imprimeurs",
        "file": output_path_printer,
        "t_ranked": "testing.ranked_candidates_printer",
        "t_points": "testing.candidates_spatial_cluster_points_printer",
        "l_ranked": "clusters_classes_printer",
        "l_points": "points_bruts_printer"
    }
]

for item in exports:
    try:
        if os.path.exists(item["file"]):
            os.remove(item["file"])

        #Couche 1 : Les Clusters (Création du fichier)
        subprocess.run([
            "ogr2ogr", "-f", "GPKG", item["file"], db_config_ogr, item["t_ranked"],
            "-nln", item["l_ranked"], "-nlt", "MULTIPOINT", "-geomfield", "geom_multipoint"
        ], check=True, capture_output=True)

        #Couche 2 : Les points bruts (Ajout au fichier existant)
        subprocess.run([
            "ogr2ogr", item["file"], db_config_ogr, item["t_points"],
            "-nln", item["l_points"], "-update"
        ], check=True, capture_output=True)

        print(f"Succès : {item['label']} exportés dans {os.path.basename(item['file'])}")
    except subprocess.CalledProcessError as e:
        print(f"Erreur export {item['label']} : {e.stderr.decode()}")



#FIN du script
duration = time.perf_counter() - start_time
print(f"\n{'='*40}\nTERMINÉ en {duration/60:.1f} minutes\n{'='*40}")
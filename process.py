#Importer les librairies necessaires
import pandas as pd
import psycopg2 #lib pour les operations en bd sql
from psycopg2.extras import execute_values #pour aller vite selon gemini
from tqdm import tqdm
import subprocess #pour l'enregistrement en gpkg
import os
import time

#CONFIGURATION
input_csv = r"./individus_normalises.csv"
#input_csv = r"/home/vmerilan/Documents/VMerilan/scripts/algo_traitement_v1/test_echantillon/donnees_normalisees.csv"
output_path_artist = "./correspondances_artist.gpkg"
output_path_printer = "./correspondances_printer.gpkg"

#CHARGEMENT CSV
df = pd.read_csv(input_csv).fillna('') #Remplacer toutes les cellules vides par un str vide, notemment pour les cas ou il n'y aurait pas de prenom

def clean_date_to_year(value):
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
    
tables_to_clear = [
        "testing.candidates", 
        "testing.candidates_cluster_points",
        "testing.candidates_clusters",  
        "testing.ranked_candidates"        
    ]


#Clear all tables
def clear_tables(cur, conn):
    for table in tables_to_clear:
        try:
            print(f"clearing {table}")
            cur.execute(f"TRUNCATE TABLE {table};")
            print(f"{table} cleared")
        except psycopg2.errors.UndefinedTable:
            conn.rollback()
            print(f"Note : {table} n'existe pas encore, elle sera créée par les fonctions.")
        except Exception as e:
            conn.rollback()
            print(f"Erreur lors du nettoyage de {table} : {e}")
    conn.commit()
    
cfg = {
            "func_data": "testing.filter_candidates",
            "func_cluster": "testing.clustering",
            "func_summary": "testing.cluster_metadata",
            "func_rank": "testing.rank_candidates",
            "func_fnl_pts" : "testing.keep_results",
            "table_init": "testing.candidates",
            "table_pts": "testing.candidates_cluster_points"
}

#filter les entrees selon le nom pour recuperer les candidats
def get_candidates(df, filter_act, cur, conn):
    data_list = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Extraction"):
        debut = safe_int(row['debut'], 1800)
        fin = safe_int(row['fin'], 1950)
        cur.execute( f"INSERT INTO {cfg['table_init']} SELECT * FROM {cfg['func_data']}(%s, %s, %s, %s, %s, %s)",
                     (row['uri'], row['nom'], row.get('prenom', ''), debut, fin, filter_act))
        
    conn.commit()

#Construction des clusters

def get_clusters(cur, conn):
    cur.execute(f"SELECT DISTINCT surname_searched, first_name_searched FROM {cfg['table_init']}")
    noms_extraits = cur.fetchall()
    for nom, prenom in tqdm(noms_extraits, desc="Clustering Spatial"):
        cur.execute(f"INSERT INTO {cfg['table_pts']} SELECT * FROM {cfg['func_cluster']}(%s, %s)", (nom, prenom))
    conn.commit()

#Construire metadonnees clusters
def get_summary(cur, conn):
    cur.execute(f"SELECT {cfg['func_summary']}();")
    conn.commit()

#Faire le ranking des clusters
def get_ranks(cur, conn):
    cur.execute(f"SELECT {cfg['func_rank']}();")
    conn.commit()

#Verser resultats dans une table generale
def get_fnl_pts(cur, conn):
    cur.execute(f"SELECT {cfg['func_fnl_pts']}();")
    conn.commit()


#Fonction qui lance tout
def full_process(cur, conn, df, filter_act):
    clear_tables(cur, conn)
    get_candidates(df, filter_act, cur, conn)
    get_clusters(cur, conn)
    get_summary(cur, conn)
    get_ranks(cur, conn)
    get_fnl_pts(cur, conn)

#Debut du script
start_time = time.perf_counter()

try:
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    full_process(cur, conn, df, "dessin|artiste|peintre|affich")
    full_process(cur, conn, df, "impr|lithogr|libr|bibli|grav|dominot|press|typo")
except Exception as e:
    print(f"\nERREUR CRITIQUE SQL : {e}")
    if 'conn' in locals(): conn.rollback()
    exit()
finally:
    if 'conn' in locals():
        cur.close()
        conn.close()


#FIN du script
duration = time.perf_counter() - start_time
print(f"\n{'='*40}\nTERMINÉ en {duration/60:.1f} minutes\n{'='*40}")
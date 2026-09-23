import pandas as pd
import psycopg2 
from psycopg2.extras import execute_values 
from tqdm import tqdm
import subprocess #pour l'enregistrement en gpkg
import os
import time

db_params = {
    "host": " ",
    "dbname": " ",
    "port": ,
    "user": " ",
    "password": " "
}

db_config_ogr = f"PG:host={db_params['host']} dbname={db_params['dbname']} port={db_params['port']} user={db_params['user']} password={db_params['password']} active_schema=testing"

output_dir = "sorties_gpkg"
os.makedirs(output_dir, exist_ok=True)

start_time = time.perf_counter()

try:
    conn = psycopg2.connect(**db_params)
    cur = conn.cursor()

    requete_likely="""
                    SELECT DISTINCT surname_searched
                    FROM testing.final_points_table
                    """

    cur.execute(requete_likely)
    noms_agents = [row[0] for row in cur.fetchall()]

    print(f"{len(noms_agents)} candidats trouvés")

    for nom in tqdm(noms_agents, desc="Génération des GeoPackages"):
        nom_fichier = f"export_gpkg_{nom}.gpkg"
        chemin_gpkg = os.path.join(output_dir, nom_fichier)

        requete_ogr = f"SELECT * FROM testing.final_points_table WHERE surname_searched = '{nom}' AND cluster_type = 'likely'"
        subprocess_params= [
            "ogr2ogr",
            "-overwrite",
            "-f", "GPKG",
            "-sql", requete_ogr,
            "-nln", f"points_candidat_{nom}",
            chemin_gpkg,
            db_config_ogr,   
        ]

        try:
            subprocess.run(subprocess_params,
                            check=True,
                            text=True,
                            capture_output=True)

        except subprocess.CalledProcessError as e:
            print(f"Error with {nom} when exporting gpkg")
            print(e.stderr)

    cur.close()
    conn.close()
except psycopg2.Error as e:
    print(f"Database Error: {e}")

end_time = time.perf_counter()
print(f"SCRIPT TERMINE, TEMPS: {end_time - start_time:.2f} secondes")
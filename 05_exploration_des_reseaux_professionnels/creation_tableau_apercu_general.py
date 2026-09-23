import os
import time
import csv
from tqdm import tqdm
import pandas as pd
from rdflib import Graph
import xml.etree.ElementTree as ET
import re

FILE_PATH_graph = r" "
FILE_PATH_xml = r" "

# Initialisation du graphe
g = Graph()

# Charge ton fichier (ajuste le format "xml" ou "turtle" selon ton fichier)
g.parse(FILE_PATH_graph, format="turtle")

requete_graphe = """
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT (?s AS ?uriAffiche) 
       ?uriAgent 
       ?typeAgent 
       (SAMPLE(?nomAgent) AS ?nomAgent)
       (SAMPLE(?t) AS ?titre)
       (STR(MIN(?d)) AS ?debutAffiche) 
       (STR(MAX(?f)) AS ?finAffiche) 
WHERE {
  ?s a rico:Record .
  
  # 1. Match Agent Relations
  ?rel rico:relationHasSource ?s .
  ?rel rico:withCreationRole ?role .
  ?role skos:prefLabel ?typeAgent .
  ?rel rico:relationHasTarget ?uriAgent .
  ?uriAgent rico:name ?nomAgent .
  FILTER(LCASE(STR(?typeAgent)) NOT IN ("commanditaire"))

  # 2. Extract Title
  OPTIONAL { ?s rico:title ?t }

  # 3. Extract Dates
  OPTIONAL {
    ?s rico:hasCreationDate ?date .
    OPTIONAL { ?date rico:beginningDate ?d }
    OPTIONAL { ?date rico:endDate ?f }
  }
}
GROUP BY ?s ?uriAgent ?typeAgent
"""

# 2. INTERROGATION DU graphe RDF
results = g.query(requete_graphe)


data = []
for row in results:
    # On transforme chaque élément de la ligne en string s'il n'est pas nul
    data.append([str(val) if val is not None else None for val in row])

colonnes = [str(var) for var in results.vars]
# Si les variables générées contiennent un "?", on le retire pour correspondre à notre DataFrame :
colonnes = [col.lstrip('?') for col in colonnes]

df = pd.DataFrame(data, columns=colonnes)

print(df)

# --- NETTOYAGE DE L'URI DE L'AFFICHE ---
def extraire_code_affiche(uri):
    return uri.split('/')[-1]

df['idAffiche'] = df['uriAffiche'].apply(extraire_code_affiche)

# INTERROGATION DU XML ADLIB 
tree = ET.parse(FILE_PATH_xml)
root = tree.getroot()

xml_data = []

for record in root.findall(".//record"):
    
    obj_num_elem = record.find("object_number")
    id_affiche_xml = obj_num_elem.text.strip() if obj_num_elem is not None else None
    
    if not id_affiche_xml:
        continue
        
    for production in record.findall("Production"):
        
        nom_agent_elem = production.find("creator")
        nom_agent = nom_agent_elem.text.strip() if (nom_agent_elem is not None and nom_agent_elem.text is not None) else None
        
        role_elem = production.find("creator.role")
        role_xml = role_elem.text.strip() if (role_elem is not None and role_elem.text is not None) else None
        
        naissance_elem = production.find("creator.birth.date")
        mort_elem = production.find("creator.death.date")
        
        naissance_val = naissance_elem.text.strip() if (naissance_elem is not None and naissance_elem.text) else None
        mort_val = mort_elem.text.strip() if (mort_elem is not None and mort_elem.text) else None
        
        xml_data.append({
            "idAffiche": id_affiche_xml, 
            "roleAgentXML": role_xml,           
            "nomAgentXML": nom_agent,           
            "dateNaissance": naissance_val,
            "dateMort": mort_val
        })

# Conversion en DataFrame Pandas des données d'agents issues du XML
df_xml = pd.DataFrame(xml_data)

# 4. FUSION PAR DOUBLE CLÉ (AFFICHE + ROLE)
df['typeAgent'] = df['typeAgent'].astype(str).str.lower().str.strip()
df_xml['roleAgentXML'] = df_xml['roleAgentXML'].astype(str).str.lower().str.strip()

df_final = pd.merge(
    df, 
    df_xml, 
    left_on=["idAffiche", "typeAgent", "nomAgent"], 
    right_on=["idAffiche", "roleAgentXML", "nomAgentXML"], # Corrigé ici
    how="left"
)
df_final = df_final[df_final['nomAgentXML'].str.lower().str.strip() != 'anonyme']

nouvel_ordre = [
    "idAffiche",
    "uriAffiche", 
    "uriAgent", 
    "typeAgent", 
    "nomAgentXML", 
    "dateNaissance", 
    "dateMort",
    "titre",
    "debutAffiche", 
    "finAffiche"
]

df_final = df_final[nouvel_ordre]

# VÉRIFICATION DU RÉSULTAT FINAL


print(f"Nombre de lignes d'affiches issues du Graphe : {len(df)}")
print(f"Nombre de lignes après fusion : {len(df_final)}")
print("\nAperçu du tableau final avec les dates de naissance/mort associées :")
print(df_final.head())

# 6. ENREGISTREMENT DU DF EN CSV

os.makedirs(" ", exist_ok=True)
df_final.to_csv(" ", index=False)
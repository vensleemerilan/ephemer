import os
import re
import pandas as pd
import xml.etree.ElementTree as ET
from rdflib import Graph
import networkx as nx
import utils
from utils import generate_ego_graph_html
from utils import save_ego_graph_html, save_global_graph_html
import hashlib
from utils import show_graph
from itertools import combinations

FILE_PATH_graph = r" "
FILE_PATH_xml = r" "

g = Graph()
g.parse(FILE_PATH_graph, format="turtle") 

requete_graphe = """
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT (?s AS ?uriAffiche) 
       ?uriAgent 
       ?typeAgent 
       ?titre 
       (STR(?d) AS ?debutAffiche) 
       (STR(?f) AS ?finAffiche) 
       ?nomAgent
WHERE {
  ?s a rico:Record .
  
  # 1. Match Agent Relations
  ?rel rico:relationHasSource ?s .
  ?rel rico:withCreationRole ?role .
  ?role skos:prefLabel ?typeAgent .
  ?rel rico:relationHasTarget ?uriAgent .
  ?uriAgent rico:name ?nomAgent .
  FILTER(LCASE(STR(?typeAgent)) NOT IN ("commanditaire"))


  # 2. Single title per record (prevents duplicates when multiple titles exist)
  {
    SELECT ?s (GROUP_CONCAT(DISTINCT ?t; separator=" | ") AS ?titre)
    WHERE {
        ?s rico:title ?t .
    }
    GROUP BY ?s
  }

  # 3. Direct optional match for the date object and bounds
  OPTIONAL {
    ?s rico:hasCreationDate ?date .
    OPTIONAL { ?date rico:beginningDate ?d }
    OPTIONAL { ?date rico:endDate ?f }
  }
}
"""

results = g.query(requete_graphe)
data_graphe = []
for row in results:
    data_graphe.append([str(val) if val is not None else None for val in row])

colonnes_g = [str(var).lstrip('?') for var in results.vars]
df_graphe = pd.DataFrame(data_graphe, columns=colonnes_g)

def extraire_code_affiche(uri):
    return uri.split('/')[-1]

df_graphe['idAffiche'] = df_graphe['uriAffiche'].apply(extraire_code_affiche)

# Suppression des agents anonymes côté Graphe
df_graphe = df_graphe[~df_graphe['uriAgent'].str.lower().str.contains('anonyme', na=False)].copy()

print("FIN ETAPE 1")

print("ÉTAPE 2 : INTERROGATION ET SÉCURISATION DU XML")
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
        
        # Filtre anti-anonyme dans le XML
        if nom_agent and "anonyme" in nom_agent.lower():
            continue
            
        role_elem = production.find("creator.role")
        role_xml = role_elem.text.strip() if (role_elem is not None and role_elem.text is not None) else None
        
        # Dates de l'agent
        naissance_elem = production.find("creator.birth.date")
        mort_elem = production.find("creator.death.date")
        
        naissance_val = naissance_elem.text.strip() if (naissance_elem is not None and naissance_elem.text) else None
        mort_val = mort_elem.text.strip() if (mort_elem is not None and mort_elem.text) else None
        
        if nom_agent:
            xml_data.append({
                "idAffiche": id_affiche_xml,
                "nomAgentXML": nom_agent,
                "roleAgentXML": role_xml,
                "dateNaissance": naissance_val,
                "dateMort": mort_val
            })

df_xml = pd.DataFrame(xml_data)

print("FIN ETAPE 2")
print("ÉTAPE 3 : CROISEMENT ET CALCUL DES MÉTRIQUES")
# Normalisation temporaire des rôles pour garantir une fusion parfaite
df_graphe['typeAgent_clean'] = df_graphe['typeAgent'].astype(str).str.lower().str.strip()
df_xml['roleAgentXML_clean'] = df_xml['roleAgentXML'].astype(str).str.lower().str.strip()

df_merged = pd.merge(
    df_graphe,
    df_xml,
    left_on=["idAffiche", "typeAgent_clean", "nomAgent"],
    right_on=["idAffiche", "roleAgentXML_clean", "nomAgentXML"],
    how="left"
)

def extraire_annee_numerique(date_str):
    if not date_str or pd.isna(date_str):
        return None

    try:
        return int(date_str)
    except ValueError as e:
        return int(date_str[:4])

df_merged['anneeDebut'] = df_merged['debutAffiche'].apply(extraire_annee_numerique)
df_merged['anneeFin'] = df_merged['finAffiche'].apply(extraire_annee_numerique)

synthese_agents = []

for (uri_agent, type_agent), group in df_merged.groupby(['uriAgent', 'typeAgent']):
  
    nom_agent = group['nomAgent'].dropna().unique()[0]
    
    # 1. Analyse de la cohérence des dates de naissance et mort (on ignore les cellules vides)
    dates_naissance_uniques = list(group['dateNaissance'].dropna().unique())
    dates_mort_uniques = list(group['dateMort'].dropna().unique())
    
    n_dates_de_naissances = len(dates_naissance_uniques)
    n_dates_de_morts = len(dates_mort_uniques)
    
    # 2. Nombre d'affiches associées
    nb_affiches = group['idAffiche'].nunique()
    
    # 3. Bornes temporelles d'activité (min / max)
    annee_min = group['anneeDebut'].min()
    annee_max = group['anneeFin'].max()
        
    # Validation des NaN via pd.isna()
    has_min = not pd.isna(annee_min)
    has_max = not pd.isna(annee_max)

    # 4. Calcul de l'intervalle uniquement si les deux bornes sont présentement valides
    intervalle_production = int(annee_max - annee_min) if (has_min and has_max) else None
    
    synthese_agents.append({
        "uriAgent": uri_agent,
        "nomAgent": nom_agent,
        "typeAgent": type_agent,
        "n_dates_de_naissances": n_dates_de_naissances,
        "n_dates_de_mort": n_dates_de_morts,
        "dates_naissance": ';'.join(dates_naissance_uniques),
        "dates_mort": ';'.join(dates_mort_uniques),
        "nb_affiches": nb_affiches,
        "date_min_affiches": str(int(annee_min)) if has_min else '',
        "date_max_affiches": str(int(annee_max)) if has_max else '',
        "intervalle_production_max": str(intervalle_production) or ''
    })


df_synthese = pd.DataFrame(synthese_agents)
df_synthese[['A inspecter', 'Commentaires']] = None

print("FIN ETAPE 3")

print("ÉTAPE 4 : CRÉATION DU GRAPHE D'AGENTS PONDÉRÉ")
collaborations_par_affiche = df_merged.groupby('idAffiche')['uriAgent'].apply(lambda x: list(set(x))).to_dict()

# Initialisation du graphe monopartie non orienté
graph = nx.Graph()

for id_affiche, agents in collaborations_par_affiche.items():
    if len(agents) < 2:
        if len(agents) == 1:
            graph.add_node(agents[0])
        continue
    
    # combinations(agents, 2) génère toutes les paires uniques d'agents (A, B) sur cette affiche
    for agent_A, agent_B in combinations(agents, 2):
        if graph.has_edge(agent_A, agent_B):
            # Si le lien existe déjà, on augmente son poids de 1 (une collaboration de plus)
            graph[agent_A][agent_B]['weight'] += 1
        else:
            # Sinon, on crée le lien avec un poids de départ de 1
            graph.add_edge(agent_A, agent_B, weight=1)

print(f"--> Graphe d'agents créé avec {graph.number_of_nodes()} nœuds (Agents) et {graph.number_of_edges()} liens (Collaborations).")

liens_forts = [(u, v, d['weight']) for u, v, d in graph.edges(data=True) if d['weight'] > 1]
liens_forts_tries = sorted(liens_forts, key=lambda x: x[2], reverse=True)

if liens_forts_tries:
    print("\nTop 5 des plus fortes collaborations détectées :")
    for u, v, poids in liens_forts_tries[:5]:
        print(f" - Agent A: {u}\n   Agent B: {v}\n   Nombre d'affiches communes : {poids}\n")
else:
    print("Aucune collaboration multi-affiches (poids > 1) détectée pour le moment.")
dict_roles = df_synthese.set_index('uriAgent')['typeAgent'].to_dict()
nx.set_node_attributes(graph, dict_roles, name='typeAgent')
print("FIN ETAPE 4")

print("\nGénération automatique des ego graphes HTML...")

output_ego_dir = "./evaluation_carnavalet/ego_graphes"
os.makedirs(output_ego_dir, exist_ok=True)

agents_du_graphe = list(graph.nodes())
total_agents = len(agents_du_graphe)
print(f"--> {total_agents} graphes d'agents à générer.")

def clean_filename(uri):
    # Simplifie l'URI pour en faire un nom de fichier propre
    return uri.split("/")[-1].split("#")[-1].replace("_", " ")

for idx, agent_uri in enumerate(agents_du_graphe):
    # Génération d'un nom de fichier unique et propre pour cet agent
    nom_fichier = f"ego_{hashlib.md5(agent_uri.encode('utf-8')).hexdigest()[:8]}_{clean_filename(agent_uri)}.html"
    chemin_complet = os.path.join(output_ego_dir, nom_fichier)

    save_ego_graph_html(
        graph,
        agent_uri,
        chemin_complet,
        "100%",
        "900px"
    )
    
    # Suivi de progression
    if (idx + 1) % 50 == 0 or (idx + 1) == total_agents:
        print(f"   [Progression] {idx + 1}/{total_agents} graphes sauvegardés...")

print(f"\nTous les graphes ont été enregistrés avec succès dans : {output_ego_dir}")

print("\nGénération du graphe de collaboration complet...")

chemin_graphe_global = "./evaluation_carnavalet/reseau_global_agents.html"

save_global_graph_html(
    graph=graph,
    output_filename=chemin_graphe_global,
    width="100%",
    height="900px"
)

print("\n7. Recherche et enregistrement des composantes connexes en HTML...")

output_comp_dir = "./evaluation_carnavalet/composantes_connexes"
os.makedirs(output_comp_dir, exist_ok=True)

composantes = sorted(nx.connected_components(graph), key=len, reverse=True)
total_composantes = len(composantes)

print(f"--> {total_composantes} composantes connexes détectées.")

mapping_agent_composante = {}

for idx, comp in enumerate(composantes):
    id_composante = idx + 1  # 1 pour la plus grande, 2 pour la deuxième, etc.
    taille_composante = len(comp)
    
    # On enregistre l'ID de la composante pour chaque agent présent dans ce groupe
    for agent_uri in comp:
        mapping_agent_composante[agent_uri] = id_composante
        
    if taille_composante > 1:
        # Extraire le sous-graphe de cette composante
        sous_graphe = graph.subgraph(comp)
       
        nom_fichier_comp = f"composante_{id_composante}_taille_{taille_composante}.html"
        chemin_complet_comp = os.path.join(output_comp_dir, nom_fichier_comp)
        
        # Enregistrement HTML via votre fonction globale
        save_global_graph_html(
            graph=sous_graphe,
            output_filename=chemin_complet_comp,
            width="100%",
            height="900px"
        )

# 4. Remplissage de votre colonne existante 'composante connexe' dans le DataFrame de synthèse
df_synthese['composante connexe'] = df_synthese['uriAgent'].map(mapping_agent_composante)

df_synthese = df_synthese.sort_values(by=["composante connexe", "nb_affiches"], ascending=[True, False])

chemin_synthese_final = "./evaluation_carnavalet/synthese_verification_agents.csv"
df_synthese.to_csv(chemin_synthese_final, index=False, encoding="utf-8")

print(f"\n--> Traitement terminé avec succès !")
print(f"    - Dossier des graphes HTML : {output_comp_dir}")
print(f"    - Colonne 'composante connexe' mise à jour dans : {chemin_synthese_final}")
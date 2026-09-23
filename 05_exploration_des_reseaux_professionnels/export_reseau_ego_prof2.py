# Script d'exportation de graphe egocentré profondeur 2 pour chaque individu du graphe en utilisant sparqlwrqpper
from SPARQLWrapper import SPARQLWrapper
from SPARQLWrapper import JSON
import matplotlib.pyplot as plt
from SPARQLWrapper import TURTLE
from rdflib import Graph
from utils import show_graph
from utils import save_graph_with_dates_html
import os
import importlib
import utils 
importlib.reload(utils)
import time
import networkx as nx
import csv
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

# set it uppppppp
endpoint = SPARQLWrapper(" ")
endpoint.setReturnFormat(JSON)
output_dir = "./graphes_html"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

#csv files for metrics
metrics_output_dir = " "
metrics_filepath = f"{metrics_output_dir}/metrics.csv"
if not os.path.exists(metrics_output_dir):
    os.makedirs(metrics_output_dir)
colonnes = ["agent_uri", "agent_name", "role", "centralite_ego", "nb_oeuvres", "nb_collaborateurs"]
with open(metrics_filepath, mode="w", newline="", encoding="utf-8") as f_init:
    writer = csv.DictWriter(f_init, fieldnames=colonnes)
    writer.writeheader()

#requete pour avoir la liste d'agents
query_liste_agents = """
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT DISTINCT ?agent ?roleLabel
WHERE {
    ?s a rico:Record .
    ?rel rico:relationHasSource ?s .  
    ?rel rico:relationHasTarget ?agent .
    OPTIONAL { 
        ?rel rico:withCreationRole ?role . 
        ?role skos:prefLabel ?roleLabel .
    }
}
"""

endpoint.setQuery(query_liste_agents)
# Exécution de la première requête et extraction de la liste des URIs
resultats_json = endpoint.queryAndConvert()
liste_agents = []
for row in resultats_json["results"]["bindings"]:
    agent_uri = row["agent"]["value"]
    # Gestion du cas où le rôle n'est pas renseigné (valeur par défaut : "Inconnu")
    role_label = row["roleLabel"]["value"] if "roleLabel" in row else "Inconnu"
    liste_agents.append({"uri": agent_uri, "role": role_label})

print(f"{len(liste_agents)} agents à traiter.\n")

print("Lancement du traitement")

def analyze_and_export_components(nx_global, dict_subgraphs_rdf, portion="all"):
    """
    Calcule le nombre de composantes connexes, génère l'histogramme de leurs tailles,
    exporte les 10 plus grosses individuellement en HTML, et crée un gros graphe HTML 
    qui fusionne ces 10 composantes.
    """

    noeuds_anonymes = [node for node in nx_global.nodes() if "anonyme" in node.lower()]
    
    if noeuds_anonymes:
        print(f"--> [Filtrage] Suppression de {len(noeuds_anonymes)} nœud(s) anonyme(s) du réseau global.")
        nx_global.remove_nodes_from(noeuds_anonymes)

    composantes = sorted(list(nx.connected_components(nx_global)), key=len, reverse=True)
    nb_composantes = len(composantes)
    print(f"[Analyse Globale] Nombre total de composantes connexes : {nb_composantes}")
    if nb_composantes == 0:
        print("Le graphe global est vide. Annulation de l'analyse.")
        return 0

    tailles = [len(c) for c in composantes]
    
    plt.figure(figsize=(10, 6))
    plt.hist(tailles, bins=50, color='purple', alpha=0.7, edgecolor='black', log=True) 
    plt.xlabel('Taille de la composante (Nb nœuds : Agents + Œuvres)', fontsize=12)
    plt.ylabel('Fréquence (Échelle Logarithmique)', fontsize=12)
    plt.title(f'Distribution de la taille des Composantes Connexes ({portion})', fontsize=14, fontweight='bold')
    plt.grid(True, which="both", linestyle=':', alpha=0.5)
    plt.tight_layout()
    
    os.makedirs(metrics_output_dir, exist_ok=True)
    plt.savefig(f"{metrics_output_dir}/histogramme_composantes_{portion}.png", dpi=300)
    plt.close()
    print(f"--> Histogramme sauvegardé : {metrics_output_dir}/histogramme_composantes_{portion}.png")

    output_dir_html = "./graphes_composantes_html"
    os.makedirs(output_dir_html, exist_ok=True)
    
    g_super_graphe = Graph()
    top_10_composantes = composantes[:10]
    print(f"\n--> Extraction et export HTML du Top {len(top_10_composantes)} des composantes...")

    for idx, comp in enumerate(top_10_composantes):
        g_comp_individuelle = Graph()
        for node in comp:
            if node in dict_subgraphs_rdf:
                for triplet in dict_subgraphs_rdf[node]:
                    s, p, o = triplet
                    
                   
                    # On rejette le triplet si "anonyme" est présent dans le Sujet, le Prédicat ou l'Objet
                    if "anonyme" in str(s).lower() or "anonyme" in str(p).lower() or "anonyme" in str(o).lower():
                        continue
                        
                    g_comp_individuelle.add(triplet)
                    g_super_graphe.add(triplet)
        
        file_individuel = f"{output_dir_html}/composante_top_{idx+1}_taille_{len(comp)}.html"
        save_graph_with_dates_html(g_comp_individuelle, output_filename=file_individuel, width="100%", height="900px", notebook=False)
        print(f"   [Top {idx+1}] Graphe individuel (Taille : {len(comp)}) -> {file_individuel}")

    # B. Sortie du gros graphe HTML contenant les 10 composantes réunies
    file_super_graphe = f"{output_dir_html}/super_graphe_top_10_{portion}.html"
    save_graph_with_dates_html(g_super_graphe, output_filename=file_super_graphe, width="100%", height="900px", notebook=False)
    print(f"\n--> [Super Graphe] Les 10 plus grosses composantes réunies dans : {file_super_graphe}")

    return nb_composantes

def process_ego_2(liste_a_traiter, role_cible=None):
    endpoint.setReturnFormat(TURTLE)

    nx_global = nx.Graph()
    dict_subgraphs_rdf = {}

    for agent_data in liste_a_traiter:
        agent_uri = agent_data["uri"]
        role_label = agent_data["role"]
                
        if role_cible is not None and role_label.lower() != role_cible.lower():
            continue
        
        nom_court = agent_uri.split('/')[-1]
        if nom_court.lower() == "anonyme":
            continue

        print(f"\n--> Traitement de l'agent : {nom_court}, URI : {agent_uri}")
        query_ego_2 = f"""
            PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
            PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

            CONSTRUCT {{
            # NIVEAU 1 : Liens pour l'Agent principal (Ego)
            ?s ?labelRoleUri <{agent_uri}> .
            ?s rico:isRelatedTo <{agent_uri}> .
            <{agent_uri}> rico:name ?nomAgent .

            ?s ?labelOtherRoleUri ?otherAgent .
            ?s rico:isRelatedTo ?otherAgent .
            ?otherAgent rico:name ?otherNom .
            
            ?s <http://localhost/dateDebut> ?dateDebut .
            ?s <http://localhost/dateFin> ?dateFin .
            }}
            WHERE {{
            <{agent_uri}> rico:name ?nomAgent .
            ?rel rico:relationHasTarget <{agent_uri}> .
            ?rel rico:relationHasSource ?s .
            ?s a rico:Record .
            
            OPTIONAL {{ 
                ?s rico:hasCreationDate ?dateNode . 
                OPTIONAL {{ ?dateNode rico:beginningDate ?dateDebut . }}
                OPTIONAL {{ ?dateNode rico:endDate ?dateFin . }}
            }}
            OPTIONAL {{ 
                ?rel rico:withCreationRole ?role . 
                OPTIONAL {{ ?role skos:prefLabel ?roleLabel . }}
            }}
            BIND(IF(BOUND(?roleLabel), IRI(CONCAT("http://localhost/role/", ?roleLabel)), ?role) AS ?labelRoleUri)

            OPTIONAL {{
                ?otherRel rico:relationHasSource ?s .
                ?otherRel rico:relationHasTarget ?otherAgent .
                ?otherAgent rico:name ?otherNom .
                
                OPTIONAL {{ 
                    ?otherRel rico:withCreationRole ?otherRole . 
                    OPTIONAL {{ ?otherRole skos:prefLabel ?otherRoleLabel . }}
                }}
                
                BIND(IF(BOUND(?otherRoleLabel), IRI(CONCAT("http://localhost/role/", ?otherRoleLabel)), ?otherRole) AS ?labelOtherRoleUri)
                
                FILTER(?otherAgent != <{agent_uri}>)
                }}
            }}  
        """
        endpoint.setQuery(query_ego_2)
        result: bytes = endpoint.queryAndConvert()
        
        g = Graph()
        g.parse(data=result, format="turtle")
        
        save_graph_with_dates_html(g, output_filename=f"./graphes_html/graph_{nom_court}.html", width="100%", height="900px", notebook=False)
        
        nx_g = nx.DiGraph()
        
        liste_documents = set()
        liste_agents = {str(agent_uri)}

        for s, p, o in g:
            str_s, str_p, str_o = str(s), str(p), str(o)
            dict_subgraphs_rdf.setdefault(str_s, []).append((s, p, o))
            dict_subgraphs_rdf.setdefault(str_o, []).append((s, p, o))
            
            if "date" in str_p or "role" in str_p or str_p == "https://www.ica.org/standards/RiC/ontology#name":
                continue
                
            nx_g.add_edge(str_s, str_o, predicate=str_p)
            nx_global.add_edge(str_s, str_o)
            
            if str_p == "https://www.ica.org/standards/RiC/ontology#isRelatedTo":
                liste_documents.add(str_s)
                liste_agents.add(str_o)

        agent_node = str(agent_uri)
        
        if agent_node in nx_g:
            centralite_dict = nx.degree_centrality(nx_g)
            centralite_ego = round(centralite_dict[agent_node], 4)
            
            nx_g_undirected = nx_g.to_undirected()
            voisins_directs = set(nx_g_undirected.neighbors(agent_node))
            nb_oeuvres = len(voisins_directs & liste_documents)
            
            distances = nx.single_source_shortest_path_length(nx_g_undirected, agent_node, cutoff=2)
            
            nb_collaborateurs = sum(
                1 for node, dist in distances.items() 
                if dist == 2 and node in liste_agents and node != agent_node
            )
        else:
            centralite_ego = 0.0
            nb_oeuvres = 0
            nb_collaborateurs = 0
        with open(metrics_filepath, mode="a", newline="", encoding="utf-8") as f_append:
            writer = csv.DictWriter(f_append, fieldnames=colonnes)
            writer.writerow({
                "agent_uri": agent_uri,
                "agent_name": nom_court,
                "role": role_label,
                "centralite_ego": centralite_ego,
                "nb_oeuvres": nb_oeuvres,
                "nb_collaborateurs": nb_collaborateurs
            })

        time.sleep(0.2)
    analyze_and_export_components(nx_global, dict_subgraphs_rdf, portion=role_cible if role_cible else "all")


def launch_full_process(liste_a_traiter, portion =None):
    process_ego_2(liste_a_traiter, role_cible = portion )
    df = pd.read_csv(metrics_filepath)
    df = df[df["nb_collaborateurs"]>0]

    seuil_x = df['centralite_ego'].median()
    seuil_y = df['nb_collaborateurs'].median()
    seuil_z = df['nb_oeuvres'].median()

    plt.scatter(df['centralite_ego'], df['nb_collaborateurs'],
                color = '#ff8c00',
                alpha= 0.6,
                edgecolors = 'w',
                s = 10)

    plt.xlabel('Centralité de degré', fontsize = 12)
    plt.ylabel('Nombre de collaborateurs', fontsize = 12)
    plt.yscale('log')

    plt.axvline(x=seuil_x, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane Centralité ({seuil_x:.2f})')
    plt.axhline(y=seuil_y, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane Collab ({int(seuil_y)} col.)')

    plt.title(f'Paysage des réseaux professionnels_{portion}', fontsize = 14, fontweight = 'bold')
    plt.grid(True, which="both", linestyle=':', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{metrics_output_dir}/paysage_reseaux_professionnels_log_{portion}.png", dpi = 800)
    plt.close()

    plt.scatter(df['centralite_ego'], df['nb_collaborateurs'],
                color = '#ff8c00',
                alpha= 0.6,
                edgecolors = 'w',
                s = 10)

    plt.xlabel('Centralité de degré', fontsize = 12)
    plt.ylabel('Nombre de collaborateurs', fontsize = 12)

    plt.axvline(x=seuil_x, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane Centralité ({seuil_x:.2f})')
    plt.axhline(y=seuil_y, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane Collab ({int(seuil_y)} col.)')

    plt.title(f'Paysage des réseaux professionnels_{portion}', fontsize = 14, fontweight = 'bold')
    plt.grid(True, which="both", linestyle=':', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{metrics_output_dir}/paysage_reseaux_professionnels_{portion}.png", dpi = 800)
    plt.close()

    plt.scatter(df['nb_collaborateurs'], df['nb_oeuvres'],
                color = '#ff8c00',
                alpha= 0.6,
                edgecolors = 'w',
                s = 10)

    plt.xlabel('Nombre de collaborateurs', fontsize = 12)
    plt.ylabel('Nombre oeuvres', fontsize = 12)
    plt.yscale('log')

    plt.axvline(x=seuil_y, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane collaborateurs ({int(seuil_y)} col.)')
    plt.axhline(y=seuil_z, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane oeuvres ({int(seuil_z)} ouv.)')

    plt.title(f'collab/oeuvres_{portion}', fontsize = 14, fontweight = 'bold')
    plt.grid(True, which="both", linestyle=':', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{metrics_output_dir}/collab-oeuvres_log_{portion}.png", dpi = 800)
    plt.close()

    #no log
    plt.scatter(df['nb_collaborateurs'], df['nb_oeuvres'],
                color = '#ff8c00',
                alpha= 0.6,
                edgecolors = 'w',
                s = 10)

    plt.xlabel('Nombre de collaborateurs', fontsize = 12)
    plt.ylabel('Nombre oeuvres', fontsize = 12)
    

    plt.axvline(x=seuil_y, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane collaborateurs ({int(seuil_y)} col.)')
    plt.axhline(y=seuil_z, color='royalblue', linestyle='--', linewidth=1, alpha=0.6, 
                label=f'Médiane oeuvres ({int(seuil_z)} ouv.)')

    plt.title(f'collab/oeuvres_{portion}', fontsize = 14, fontweight = 'bold')
    plt.grid(True, which="both", linestyle=':', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{metrics_output_dir}/collab_oeuvres_{portion}.png", dpi = 800)
    plt.close()


start_time = time.perf_counter()

launch_full_process(liste_agents, portion="Dessinateur")
launch_full_process(liste_agents, portion="Imprimeur")




#FIN du script
duration = time.perf_counter() - start_time
print(f"\n{'='*40}\nTERMINÉ en {duration/60:.1f} minutes\n{'='*40}")

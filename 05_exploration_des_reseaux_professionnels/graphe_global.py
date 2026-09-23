import os
import networkx as nx
from SPARQLWrapper import SPARQLWrapper, JSON

from utils import save_global_graph_html, save_global_graph_geopackage


def main():

    output_dir = " "  
    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(output_dir, "graphe_complet.html")
    gpkg_path = os.path.join(output_dir, "graphe_complet.gpkg")

    # --- 1. CONNEXION GRAPHDB & REQUÊTES SPARQL ---
    endpoint = SPARQLWrapper(" ")
    endpoint.setReturnFormat(JSON)

    query_date_intervalle = """
        PREFIX adb: <http://data.soduco.fr/def/annuaire#>
        PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?uriAgent ?nomagent ?typeAgent (MIN(?debut) AS ?dateDebutMin) (MAX(?fin) AS ?dateFinMax) ?adresse ?geom
        WHERE {
            ?rel a rico:CreationRelation ;
                rico:withCreationRole ?role ;
                rico:relationHasTarget ?uriAgent ;
                rico:relationHasSource ?s .
                
            ?uriAgent rico:name ?nomagent .
            ?role skos:prefLabel ?typeAgent .
            ?cluster skos:exactMatch ?uriAgent .
            ?cluster adb:address ?adresse .
            ?cluster adb:hasAddressGeometry ?geom .
            
            ?s rico:hasCreationDate ?date .
            ?date rico:beginningDate ?debut ;
                rico:endDate ?fin .
            FILTER(!CONTAINS(LCASE(STR(?nomagent)), "anonyme"))
        }
        GROUP BY ?uriAgent ?nomagent ?typeAgent ?adresse ?geom
    """

    query_liens = """
        PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>

        SELECT ?agent1 ?agent2 (COUNT(DISTINCT ?s) AS ?weight)
        WHERE {
            ?rel1 a rico:CreationRelation ; rico:relationHasSource ?s ; rico:relationHasTarget ?agent1 .
            ?rel2 a rico:CreationRelation ; rico:relationHasSource ?s ; rico:relationHasTarget ?agent2 .
            FILTER(STR(?agent1) < STR(?agent2))
        }
        GROUP BY ?agent1 ?agent2
    """
    print("Extraction des données depuis GraphDB...")
    G_agents = nx.Graph()

    endpoint.setQuery(query_date_intervalle)
    res_nodes = endpoint.query().convert()
    
    for b in res_nodes["results"]["bindings"]:
        uri = b["uriAgent"]["value"]
        G_agents.add_node(
            uri,
            nomagent=b.get("nomagent", {}).get("value", ""),
            typeAgent=b.get("typeAgent", {}).get("value", ""),
            dateDebutMin=b.get("dateDebutMin", {}).get("value", ""),
            dateFinMax=b.get("dateFinMax", {}).get("value", ""),
            adresse=b.get("adresse", {}).get("value", ""),
            geom=b.get("geom", {}).get("value", "")
        )

    endpoint.setQuery(query_liens)
    res_edges = endpoint.query().convert()

    for b in res_edges["results"]["bindings"]:
        u = b["agent1"]["value"]
        v = b["agent2"]["value"]
        w = int(b["weight"]["value"])
        if u in G_agents and v in G_agents:
            G_agents.add_edge(u, v, weight=w)

    print(f"Graphe prêt : {G_agents.number_of_nodes()} nœuds et {G_agents.number_of_edges()} liens.")

    print(f"Génération du HTML dans : {html_path}")
    save_global_graph_html(G_agents, output_filename=html_path)

    print(f"Génération du GeoPackage dans : {gpkg_path}")
    save_global_graph_geopackage(G_agents, output_filename=gpkg_path)

    print(f"\nTraitement terminé. Les fichiers sont disponibles dans '{os.path.abspath(output_dir)}'.")


if __name__ == "__main__":
    main()
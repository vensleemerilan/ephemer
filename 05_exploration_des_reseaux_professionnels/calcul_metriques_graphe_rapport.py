import os
import re
import networkx as nx
from SPARQLWrapper import SPARQLWrapper, JSON
import numpy as np
from scipy.spatial import KDTree
from shapely.wkt import loads as wkt_loads
from shapely.geometry import Point, Polygon
import geopandas as gpd

# Import des fonctions d'export depuis utils.py
from utils import save_global_graph_html, save_global_graph_geopackage


def parse_wkt_point(wkt_str):
    """Extrait X (lon) et Y (lat) du WKT brut."""
    if not wkt_str:
        return None, None
    try:
        match = re.search(r"POINT\s*\(\s*([-\d\.]+)\s+([-\d\.]+)\s*\)", str(wkt_str), re.IGNORECASE)
        if match:
            v1, v2 = float(match.group(1)), float(match.group(2))
        else:
            geom = wkt_loads(wkt_str)
            if hasattr(geom, 'x') and hasattr(geom, 'y'):
                v1, v2 = geom.x, geom.y
            else:
                return None, None
        return v1, v2
    except Exception:
        return None, None


def main():
    # --- CONFIGURATION DU DOSSIER DE SORTIE ---
    output_dir = " "  
    os.makedirs(output_dir, exist_ok=True)

    html_path = os.path.join(output_dir, "metriques_graphe_complet.html")
    gpkg_path = os.path.join(output_dir, "metriques_graphe_complet.gpkg")
    txt_path = os.path.join(output_dir, "metriques_globales.txt")

    # --- 1. CONNEXION GRAPHDB & REQUÊTES SPARQL ---
    endpoint = SPARQLWrapper(" ")
    endpoint.setReturnFormat(JSON)

    excluded_uris = """
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerieflevee>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/typographiepanckoucke>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerieadindcbourgerie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/reullierj>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/clavela>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/henrysicard>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/delanchyimprimerie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerieadavy>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimeriehenon>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerieedupre>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/courmontfreres>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/panckouckecharleslouisfleury>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimeriegrandremyethenon>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerierthomascie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerielmichelcie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimeriegdemalherbeetcie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimeriebourgerieetcie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimeriebelfondcie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/imprimerieajanniotcie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/heliotypiebuirettecie>,
        <http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/agent/cussetetcieimprimerie>

    """

    query_date_intervalle = f"""
        PREFIX adb: <http://data.soduco.fr/def/annuaire#>
        PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

        SELECT DISTINCT ?uriAgent ?nomagent ?typeAgent (MIN(?debut) AS ?dateDebutMin) (MAX(?fin) AS ?dateFinMax) ?adresse ?geom
        WHERE {{
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
            FILTER(?uriAgent NOT IN ({excluded_uris}))
        }}
        GROUP BY ?uriAgent ?nomagent ?typeAgent ?adresse ?geom
    """

    query_liens = f"""
        PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>

        SELECT ?agent1 ?agent2 (COUNT(DISTINCT ?s) AS ?weight)
        WHERE {{
            ?rel1 a rico:CreationRelation ; rico:relationHasSource ?s ; rico:relationHasTarget ?agent1 .
            ?rel2 a rico:CreationRelation ; rico:relationHasSource ?s ; rico:relationHasTarget ?agent2 .
            FILTER(STR(?agent1) < STR(?agent2))
            FILTER(?agent1 NOT IN ({excluded_uris}))
            FILTER(?agent2 NOT IN ({excluded_uris}))
        }}
        GROUP BY ?agent1 ?agent2
    """

    # --- 2. EXÉCUTION DE LA REQUÊTE NŒUDS ---
    endpoint.setQuery(query_date_intervalle)
    res_nodes = endpoint.query().convert()["results"]["bindings"]

    G = nx.Graph()

    for row in res_nodes:
        uri = row["uriAgent"]["value"]
        raw_geom = row.get("geom", {}).get("value", "")
        lon, lat = parse_wkt_point(raw_geom)
        
        clean_wkt = f"POINT ({lon} {lat})" if lon is not None else ""

        if not G.has_node(uri):
            G.add_node(
                uri,
                label=row.get("nomagent", {}).get("value", ""),
                typeAgent=row.get("typeAgent", {}).get("value", ""),
                dateDebutMin=row.get("dateDebutMin", {}).get("value", ""),
                dateFinMax=row.get("dateFinMax", {}).get("value", ""),
                adresse=row.get("adresse", {}).get("value", ""),
                geom=clean_wkt
            )

    # --- 3. EXÉCUTION DE LA REQUÊTE LIENS ---
    endpoint.setQuery(query_liens)
    res_edges = endpoint.query().convert()["results"]["bindings"]

    for row in res_edges:
        u = row["agent1"]["value"]
        v = row["agent2"]["value"]
        weight = int(row["weight"]["value"])
        if G.has_node(u) and G.has_node(v):
            G.add_edge(u, v, weight=weight)

    print(f"Graphe chargé : {G.number_of_nodes()} nœuds et {G.number_of_edges()} relations.")

    # --- 4. CALCUL DES MÉTRIQUES RELATIONNELLES ---
    degrees = dict(G.degree())
    weighted_degrees = dict(G.degree(weight="weight"))
    nx.set_node_attributes(G, weighted_degrees, "weighted_degree")

    modularity_score = 0.0
    if G.number_of_edges() > 0:
        communities = nx.community.louvain_communities(G, weight="weight")
        modularity_score = nx.community.modularity(G, communities, weight="weight", resolution=1)
        
        community_dict = {}
        for comm_id, comm_nodes in enumerate(communities):
            for node in comm_nodes:
                community_dict[node] = comm_id
        nx.set_node_attributes(G, community_dict, "community")

    component_dict = {}
    accessibilite = {}
    distance_moyenne = {}
    dispersion_totale = 0
    dispersion_geante = 0
    n_giant = 0
    l_moyen_geante = 0.0

    if G.number_of_nodes() > 0:
        sorted_components = sorted(nx.connected_components(G), key=len, reverse=True)

        for comp_id, comp in enumerate(sorted_components):
            sub_g = G.subgraph(comp)
            all_paths = dict(nx.all_pairs_shortest_path_length(sub_g))
            n_comp = len(comp)

            if comp_id == 0:
                n_giant = n_comp

            for node, dists in all_paths.items():
                component_dict[node] = comp_id
                acc = sum(dists.values())
                accessibilite[node] = acc

                dist_moy = acc / (n_comp - 1) if n_comp > 1 else 0.0
                distance_moyenne[node] = dist_moy

                dispersion_totale += acc
                if comp_id == 0:
                    dispersion_geante += acc
                    
        if n_giant > 1:
            l_moyen_geante = dispersion_geante / (n_giant * (n_giant - 1))

    nx.set_node_attributes(G, component_dict, "component_id")
    nx.set_node_attributes(G, accessibilite, "accessibilite")
    nx.set_node_attributes(G, distance_moyenne, "distance_moyenne")

    giant_nodes = [node for node, c_id in component_dict.items() if c_id == 0]
    best_agent_node = min(giant_nodes, key=lambda n: accessibilite[n]) if giant_nodes else "N/A"
    best_agent_name = G.nodes[best_agent_node].get("label", best_agent_node) if giant_nodes else "N/A"
    best_agent_dist_moy = distance_moyenne.get(best_agent_node, 0.0) if giant_nodes else 0.0

    # --- 5. EXPORTS & CENTROGRAPHIE GLOBALE ET PAR PROFESSION ---
    save_global_graph_html(G, html_path)
    save_global_graph_geopackage(G, gpkg_path)

    coords_list = []
    types_list = []
    nodes_data = []

    for n, data in G.nodes(data=True):
        lon, lat = parse_wkt_point(data.get("geom", ""))
        if lon is not None and lat is not None:
            nodes_data.append({
                "uri": n,
                "label": data.get("label", ""),
                "typeAgent": data.get("typeAgent", "Inconnu"),
                "geometry": Point(lon, lat)
            })

    n_geo = len(nodes_data)
    print(f"DEBUG: Nombre de points géolocalisés valides trouvés : {n_geo}")

    mean_center = (0.0, 0.0)
    std_distance = 0.0
    semi_major = 0.0
    semi_minor = 0.0
    orientation_deg = 0.0
    clq_text_lines = []
    centro_records = []

    if n_geo >= 3:
        gdf_nodes = gpd.GeoDataFrame(nodes_data, crs="EPSG:4326")
        gdf_nodes_l93 = gdf_nodes.to_crs("EPSG:2154")

        for geom in gdf_nodes_l93.geometry:
            if geom is not None and not geom.is_empty:
                coords_list.append((geom.x, geom.y))
        
        for t_agent in gdf_nodes_l93["typeAgent"]:
            types_list.append(t_agent or "Inconnu")

        coords_arr = np.array(coords_list)
        x_coords = coords_arr[:, 0]
        y_coords = coords_arr[:, 1]

        # --- A. Centrographie Globale ---
        mean_x = np.mean(x_coords)
        mean_y = np.mean(y_coords)
        mean_center = (mean_x, mean_y)

        var_x = np.sum((x_coords - mean_x) ** 2) / n_geo
        var_y = np.sum((y_coords - mean_y) ** 2) / n_geo
        std_distance = np.sqrt(var_x + var_y)

        cov_matrix = np.cov(x_coords, y_coords)
        eigvals, eigvecs = np.linalg.eigh(cov_matrix)
        order = eigvals.argsort()[::-1]
        eigvals, eigvecs = eigvals[order], eigvecs[:, order]

        semi_major = np.sqrt(max(eigvals[0], 0))
        semi_minor = np.sqrt(max(eigvals[1], 0))
        theta = np.arctan2(eigvecs[1, 0], eigvecs[0, 0])
        orientation_deg = np.degrees(theta) % 360

        t_angles = np.linspace(0, 2 * np.pi, 100)
        cos_t, sin_t = np.cos(t_angles), np.sin(t_angles)
        rot_x = semi_major * cos_t * np.cos(theta) - semi_minor * sin_t * np.sin(theta)
        rot_y = semi_major * cos_t * np.sin(theta) + semi_minor * sin_t * np.cos(theta)
        
        global_ellipse_geom = Polygon(list(zip(rot_x + mean_x, rot_y + mean_y)))
        global_center_geom = Point(mean_x, mean_y)
        global_sd_circle = global_center_geom.buffer(std_distance)

        centro_records.append({"category": "Global", "label": "Centre moyen (Global)", "geometry": global_center_geom})
        centro_records.append({"category": "Global", "label": "Distance standard (Global)", "geometry": global_sd_circle})
        centro_records.append({"category": "Global", "label": "Ellipse de déviation standard (Global)", "geometry": global_ellipse_geom})

        # --- B. Centrographie par Type de Profession ---
        types_arr = np.array(types_list)
        unique_types, counts = np.unique(types_arr, return_counts=True)
        type_counts = dict(zip(unique_types, counts))
        valid_types = [t for t, c in type_counts.items() if c >= 3 and t != "Inconnu"]

        for tA in valid_types:
            idxA = np.where(types_arr == tA)[0]
            sub_coords = coords_arr[idxA]
            sub_n = len(sub_coords)

            sub_mean_x = np.mean(sub_coords[:, 0])
            sub_mean_y = np.mean(sub_coords[:, 1])
            sub_center_geom = Point(sub_mean_x, sub_mean_y)

            sub_var_x = np.sum((sub_coords[:, 0] - sub_mean_x) ** 2) / sub_n
            sub_var_y = np.sum((sub_coords[:, 1] - sub_mean_y) ** 2) / sub_n
            sub_std_dist = np.sqrt(sub_var_x + sub_var_y)
            sub_sd_circle = sub_center_geom.buffer(sub_std_dist)

            sub_cov = np.cov(sub_coords[:, 0], sub_coords[:, 1])
            sub_eigvals, sub_eigvecs = np.linalg.eigh(sub_cov)
            sub_order = sub_eigvals.argsort()[::-1]
            sub_eigvals = sub_eigvals[sub_order]
            sub_eigvecs = sub_eigvecs[:, sub_order]

            sub_semi_major = np.sqrt(max(sub_eigvals[0], 0))
            sub_semi_minor = np.sqrt(max(sub_eigvals[1], 0))
            sub_theta = np.arctan2(sub_eigvecs[1, 0], sub_eigvecs[0, 0])

            sub_rot_x = sub_semi_major * cos_t * np.cos(sub_theta) - sub_semi_minor * sin_t * np.sin(sub_theta)
            sub_rot_y = sub_semi_major * cos_t * np.sin(sub_theta) + sub_semi_minor * sin_t * np.cos(sub_theta)
            sub_ellipse_geom = Polygon(list(zip(sub_rot_x + sub_mean_x, sub_rot_y + sub_mean_y)))

            centro_records.append({"category": f"Profession: {tA}", "label": f"Centre moyen - {tA}", "geometry": sub_center_geom})
            centro_records.append({"category": f"Profession: {tA}", "label": f"Distance standard - {tA}", "geometry": sub_sd_circle})
            centro_records.append({"category": f"Profession: {tA}", "label": f"Ellipse - {tA}", "geometry": sub_ellipse_geom})

        # --- C. Calcul CLQ ---
        tree = KDTree(coords_arr)
        _, nn_indices = tree.query(coords_arr, k=2)
        nn_indices = nn_indices[:, 1]

        for tA in valid_types:
            idxA = np.where(types_arr == tA)[0]
            nA = len(idxA)
            nn_of_A = types_arr[nn_indices[idxA]]
            for tB in valid_types:
                n_A_to_B = np.sum(nn_of_A == tB)
                nB = type_counts[tB]
                denom = (nB - 1) / (n_geo - 1) if tA == tB else nB / (n_geo - 1)
                clq = (n_A_to_B / nA) / denom if denom > 0 else 0.0
                
                interpretation = "attraction" if clq > 1.1 else ("ségrégation" if clq < 0.9 else "neutre")
                clq_text_lines.append(f"  - CLQ ({tA} -> {tB}) : {clq:.2f} ({interpretation})")
    else:
        print("AVERTISSEMENT: Moins de 3 points géolocalisés valides.")

    if len(centro_records) > 0:
        gdf_centro = gpd.GeoDataFrame(centro_records, crs="EPSG:2154")
        gdf_centro.to_file(gpkg_path, layer="centrographie", driver="GPKG")
        print(f"Couche 'centrographie' (avec déclinaisons par profession) ajoutée avec succès à : {gpkg_path}")

    # --- 6. RÉSULTATS CONSOLE ET EXPORT TEXTE ---
    deg_vals = list(degrees.values())
    weight_vals = [d['weight'] for u, v, d in G.edges(data=True)]
    pct_giant = (n_giant / G.number_of_nodes() * 100) if G.number_of_nodes() > 0 else 0

    clq_section = "\n".join(clq_text_lines) if clq_text_lines else "  Aucune donnée suffisante pour le CLQ."

    summary_text = f"""=======================================================
         RÉSUMÉ DES MÉTRIQUES DU RÉSEAU
=======================================================
Nœuds totaux             : {G.number_of_nodes()}
Liens totaux             : {G.number_of_edges()}
Composante géante        : {n_giant} nœuds ({pct_giant:.1f}% du réseau)
-------------------------------------------------------
MÉTRIQUES RELATIONNELLES
-------------------------------------------------------
Degré Max                : {max(deg_vals) if deg_vals else 0} | Degré Moyen : {np.mean(deg_vals):.2f}
Poids Max                : {max(weight_vals) if weight_vals else 0} | Poids Moyen : {np.mean(weight_vals) if weight_vals else 0:.2f}
Modularité (Q)           : {modularity_score:.3f}
Dispersion totale (D)    : {dispersion_totale}
Longueur moy. chemins(L) : {l_moyen_geante:.2f} pas (composante géante)
Agent le plus central    : {best_agent_name} ({best_agent_dist_moy:.2f} pas en moyenne)
-------------------------------------------------------
MÉTRIQUES SPATIALES & CENTROGRAPHIE (EPSG:2154 - Lambert-93)
-------------------------------------------------------
Nœuds géolocalisés       : {n_geo} / {G.number_of_nodes()}
Centre moyen (X, Y)      : ({mean_center[0]:.2f}, {mean_center[1]:.2f})
Distance standard (SD)   : {std_distance:.2f} m
Ellipse - Demi-grand axe : {semi_major:.2f} m
Ellipse - Demi-petit axe : {semi_minor:.2f} m
Ellipse - Orientation    : {orientation_deg:.1f}°
-------------------------------------------------------
QUOTIENT DE CO-LOCALISATION (CLQ - Plus proche voisin)
-------------------------------------------------------
{clq_section}
=======================================================
"""

    print("\n" + summary_text)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(summary_text)

    print(f"Rapport texte enregistré dans : {txt_path}")
    print("Export global terminé avec succès.")


if __name__ == "__main__":
    main()
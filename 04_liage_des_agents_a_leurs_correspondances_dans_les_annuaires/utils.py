import base64
from enum import Enum
import hashlib
import json
from pyvis.network import Network
from rdflib import Literal, Graph
import networkx as nx
import math
from shapely.geometry import Point, LineString
import re
import geopandas as gpd
import shapely.wkt
from shapely.geometry import Point, LineString, Polygon, MultiPoint, MultiLineString, MultiPolygon
import os

def generate_graph_from_rdf(rdf_graph, width="100%", height="600px", notebook=False):
    # Palette Kawaii Soft épurée
    colors = {
        "bg": "#ffffff",         
        "text": "#6E665E",       
        "sakura": "#FFC1CC",     
        "sky": "#A2D2FF",        
        "matcha": "#C1E1C1",     
        "cream": "#FEE1A8",      
        "line": "#E8E8E8"        
    }

    net = Network(
        height=height, width=width,
        bgcolor=colors["bg"],
        font_color=colors["text"],
        notebook=notebook,
        cdn_resources='remote',
        select_menu=True, # <-- AJOUT : Menu de recherche par label
        filter_menu=True  # <-- AJOUT : Menu de filtrage avancé
    )

    added_nodes = set()

    def safe_id(value):
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    for s, p, o in rdf_graph:
        s_str, p_str, o_str = str(s), str(p), str(o)
        s_id = s_str
        o_id = safe_id(o_str) if isinstance(o, Literal) else o_str
        
        s_label = s_str.split("/")[-1]
        p_label = p_str.split("/")[-1].split("#")[-1]
        o_label = o_str.split("/")[-1].split("#")[-1]

        # --- Nœuds : Bulles colorées sans bordures ---
        if s_id not in added_nodes:
            is_expr = s_str.endswith("#Expression")
            net.add_node(
                s_id,
                label=s_label,
                title=s_str,
                color=colors["sakura"] if is_expr else colors["sky"],
                shape="dot",
                size=15,
                borderWidth=0,
                font={"size": 14, "face": "Arial Rounded MT Bold, sans-serif"}
            )
            added_nodes.add(s_id)

        if o_id not in added_nodes:
            is_lit = isinstance(o, Literal)
            net.add_node(
                o_id,
                label=o_label,
                color=colors["matcha"] if is_lit else colors["cream"],
                shape="dot",
                size=10 if is_lit else 13,
                borderWidth=0,
                font={"size": 12, "face": "Arial Rounded MT Bold, sans-serif"}
            )
            added_nodes.add(o_id)

        # --- Arêtes : Fines et claires ---
        net.add_edge(
            s_id, o_id,
            label=p_label,
            color={"color": colors["line"], "highlight": colors["sakura"]},
            width=2,
            arrows={"to": {"enabled": True, "scaleFactor": 0.3}},
            font={"size": 9, "color": "#B0B0B0", "strokeWidth": 0} 
        )

    options = {
        "nodes": {
            "font": {"strokeWidth": 0, "align": "top"}, 
            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.05)", "size": 7, "x": 3, "y": 3}
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.4},
            "font": {"strokeWidth": 0} 
        },
        "physics": {
            "forceAtlas2Based": {"gravitationalConstant": -100, "springLength": 120},
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 100}
        },
        "interaction": {
            "hover": True,
            "navigationButtons": False
        }
    }

    net.set_options(json.dumps(options))
    return net

def generate_graph_with_dates_from_rdf(rdf_graph, width="100%", height="600px", notebook=False):
    # Palette Kawaii Soft épurée
    colors = {
        "bg": "#ffffff",         
        "text": "#6E665E",       
        "sakura": "#FFC1CC",     
        "sky": "#A2D2FF",        
        "matcha": "#C1E1C1",     
        "cream": "#FEE1A8",      
        "line": "#E8E8E8"        
    }

    net = Network(
        height=height, width=width,
        bgcolor=colors["bg"],
        font_color=colors["text"],
        notebook=notebook,
        cdn_resources='remote',
        select_menu=True, # <-- AJOUT : Menu de recherche par label
        filter_menu=True  # <-- AJOUT : Menu de filtrage avancé
    )

    added_nodes = set()

    def safe_id(value):
        return hashlib.md5(value.encode("utf-8")).hexdigest()

    
    dates_debut = {}
    dates_fin = {}
    
    for s, p, o in rdf_graph:
        p_str = str(p)
        if "dateDebut" in p_str:
            dates_debut[str(s)] = str(o)
        elif "dateFin" in p_str:
            dates_fin[str(s)] = str(o)

    for s, p, o in rdf_graph:
        s_str, p_str, o_str = str(s), str(p), str(o)
        
        # Sécurité : On ignore les lignes de dates pour NE PAS créer de nœuds physiques (bulles)
        if "dateDebut" in p_str or "dateFin" in p_str:
            continue

        s_id = s_str
        o_id = safe_id(o_str) if isinstance(o, Literal) else o_str
        
        s_label = s_str.split("/")[-1]
        p_label = p_str.split("/")[-1].split("#")[-1]
        o_label = o_str.split("/")[-1].split("#")[-1]

        # --- Nœuds Sujets : Bulles avec infobulle enrichie des dates ---
        if s_id not in added_nodes:
            is_expr = s_str.endswith("#Expression")
            
            # Récupération des dates associées à ce sujet spécifique (ou "Inconnue" si absentes)
            d_deb = dates_debut.get(s_str, "Inconnue")
            d_fin = dates_fin.get(s_str, "Inconnue")
            
            # Utilisation des \n pour forcer des retours à la ligne propres dans PyVis
            sujet_tooltip = f"Document : {s_label}\nDébut : {d_deb}\nFin : {d_fin}\nURI : {s_str}"

            net.add_node(
                s_id,
                label=s_label,
                title=sujet_tooltip,  
                color=colors["sakura"] if is_expr else colors["sky"],
                shape="dot",
                size=15,
                borderWidth=0,
                font={"size": 14, "face": "Arial Rounded MT Bold, sans-serif"}
            )
            added_nodes.add(s_id)

        if o_id not in added_nodes:
            is_lit = isinstance(o, Literal)
            net.add_node(
                o_id,
                label=o_label,
                color=colors["matcha"] if is_lit else colors["cream"],
                shape="dot",
                size=10 if is_lit else 13,
                borderWidth=0,
                font={"size": 12, "face": "Arial Rounded MT Bold, sans-serif"}
            )
            added_nodes.add(o_id)

        # --- Arêtes ---
        net.add_edge(
            s_id, o_id,
            label=p_label,
            color={"color": colors["line"], "highlight": colors["sakura"]},
            width=2,
            arrows={"to": {"enabled": True, "scaleFactor": 0.3}},
            font={"size": 9, "color": "#B0B0B0", "strokeWidth": 0}
        )

    options = {
        "nodes": {
            "font": {"strokeWidth": 0, "align": "top"},
            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.05)", "size": 7, "x": 3, "y": 3}
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.4},
            "font": {"strokeWidth": 0}
        },
        "physics": {
            "forceAtlas2Based": {"gravitationalConstant": -100, "springLength": 120},
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 100}
        },
        "interaction": {
            "hover": True,
            "navigationButtons": False
        }
    }

    net.set_options(json.dumps(options))
    return net

def generate_ego_graph_html(graph, target_agent_uri, width="100%", height="600px", notebook=False):
    """
    Configure et retourne l'objet PyVis Network de l'ego graphe d'un agent.
    """
    # Palette Kawaii Soft épurée
    colors = {
        "bg": "#ffffff",
        "text": "#6E665E",
        "sakura": "#FFC1CC",     
        "sky": "#A2D2FF",        
        "line": "#E8E8E8"
    }

    net = Network(
        height=height, width=width,
        bgcolor=colors["bg"],
        font_color=colors["text"],
        notebook=notebook,
        cdn_resources='remote',
        select_menu=True, # <-- AJOUT : Menu de recherche par label
        filter_menu=True  # <-- AJOUT : Menu de filtrage avancé
    )

    if not graph.has_node(target_agent_uri):
        return net

    ego_net = nx.ego_graph(graph, target_agent_uri, radius=1)
    added_nodes = set()
    
    def clean_label(uri):
        return uri.split("/")[-1].split("#")[-1].replace("_", " ")

    # Ajout des nœuds
    for node in ego_net.nodes():
        node_label = clean_label(node)
        is_ego = (node == target_agent_uri)
        
        net.add_node(
            node,
            label=node_label,
            title=node,
            color=colors["sakura"] if is_ego else colors["sky"],
            shape="dot",
            size=25 if is_ego else 15,
            borderWidth=0,
            font={"size": 16 if is_ego else 12, "face": "Arial Rounded MT Bold, sans-serif"}
        )

    for u, v, data in ego_net.edges(data=True):
        weight = data.get('weight', 1)
        net.add_edge(
            u, v,
            label=f"{weight} coll.",
            color={"color": colors["line"], "highlight": colors["sakura"]},
            width=1 + math.sqrt(weight) * 1.5,
            arrows={"to": {"enabled": False}},
            font={"size": 10, "color": "#B0B0B0", "strokeWidth": 0}
        )

    options = {
        "nodes": {
            "font": {"strokeWidth": 0, "align": "top"},
            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.05)", "size": 7, "x": 3, "y": 3}
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.4},
            "font": {"strokeWidth": 0}
        },
        "physics": {
            "forceAtlas2Based": {"gravitationalConstant": -80, "springLength": 150},
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 80}
        },
        "interaction": {
            "hover": True,
            "navigationButtons": False
        }
    }
    net.set_options(json.dumps(options))
    return net

def generate_global_graph_html(G_agents, width="100%", height="800px", notebook=False):
    """
    Configure et retourne l'objet PyVis Network du graphe global de collaborations.
    Couleurs basées sur le rôle (imprimeur en bleu, dessinateur en rouge).
    """
    import math
    import json
    from pyvis.network import Network
    
    # Palette épurée
    colors = {
        "bg": "#ffffff",
        "text": "#6E665E",
        "imprimeur": "#4D96FF",  # Bleu
        "dessinateur": "#FF6B6B", # Rouge
        "default": "#A2D2FF",     # Bleu clair par défaut
        "line": "#E8E8E8"
    }

    net = Network(
        height=height, width=width,
        bgcolor=colors["bg"],
        font_color=colors["text"],
        notebook=notebook,
        cdn_resources='remote',
        select_menu=True,
        filter_menu=True
    )

    def clean_label(uri):
        return uri.split("/")[-1].split("#")[-1].replace("_", " ")

    degres = dict(G_agents.degree())

    for node in G_agents.nodes(data=True):
        node_id = node[0]
        node_attrs = node[1]

        node_label = clean_label(node_id)
        degre = degres.get(node_id, 0)
        taille = 10 + (math.sqrt(degre) * 4)

        # 1. Récupération du rôle de l'agent
        role = str(node_attrs.get('typeAgent', '')).lower()

        # 2. Attribution de la couleur selon le rôle
        if any(keyword in role for keyword in ['imprimeur', 'lithographe', 'gravure']):
            couleur = colors["imprimeur"]
        elif any(keyword in role for keyword in ['dessinateur', 'illustrateur', 'artiste', 'peintre']):
            couleur = colors["dessinateur"]
        else:
            couleur = colors["default"]

        # 3. Ajout du nœud
        net.add_node(
            node_id,
            label=node_label,
            title=f"{node_label}\nRôle : {role if role else 'Non renseigné'}\nCollaborateurs : {degre}\nURI : {node_id}",
            color=couleur,
            shape="dot",
            size=taille,
            borderWidth=0,
            font={"size": 11, "face": "Arial Rounded MT Bold, sans-serif"}
        )

    for u, v, data in G_agents.edges(data=True):
        weight = data.get('weight', 1)
        epaisseur = 0.8 + math.sqrt(weight) * 0.8
        
        net.add_edge(
            u, v,
            color={"color": colors["line"], "highlight": colors["dessinateur"]},
            width=epaisseur,
            arrows={"to": {"enabled": False}},
            title=f"{weight} collaboration(s)" 
        )

    options = {
        "nodes": {
            "font": {"strokeWidth": 0, "align": "top"},
            "shadow": {"enabled": True, "color": "rgba(0,0,0,0.03)", "size": 5, "x": 2, "y": 2}
        },
        "edges": {
            "smooth": {"type": "continuous", "roundness": 0.2},
            "font": {"strokeWidth": 0}
        },
        "physics": {
            "barnesHut": {
                "gravitationalConstant": -15000,
                "centralGravity": 0.3,
                "springLength": 95,
                "springConstant": 0.04,
                "damping": 0.09,
                "avoidOverlap": 1
            },
            "solver": "barnesHut",
            "stabilization": {"iterations": 150, "updateInterval": 25}
        },
        "interaction": {
            "hover": True,
            "navigationButtons": True, 
            "hideEdgesOnDrag": True 
        }
    }
    
    net.set_options(json.dumps(options))
    return net

def save_graph_html(graph, output_filename="graph.html", width="100%", height="400px", notebook=False):
    net = generate_graph_from_rdf(graph, width=width, height=height, notebook=notebook)
    net.write_html(output_filename)

def save_graph_with_dates_html(graph, output_filename="graph.html", width="100%", height="400px", notebook=False):
    net = generate_graph_with_dates_from_rdf(graph, width=width, height=height, notebook=notebook)
    net.write_html(output_filename)

def save_ego_graph_html(graph, target_agent_uri, output_filename="graph.html", width="100%", height="400px", notebook=False):
    net = generate_ego_graph_html(graph, target_agent_uri, width=width, height=height, notebook=notebook)
    net.write_html(output_filename)

def save_global_graph_html(graph, output_filename="graphe_complet.html", width="100%", height="800px", notebook=False):     
    net = generate_global_graph_html(graph, width=width, height=height, notebook=notebook)
    net.write_html(output_filename)
    
def show_graph(graph,  notebook=False, width="100%", height="400px"):
    net = generate_graph_from_rdf(graph, width=width, height=height, notebook=notebook)
    html_content = net.generate_html()
           
    data_uri = "data:text/html;base64," + base64.b64encode(html_content.encode()).decode()
    from IPython.display import display, IFrame
    display(IFrame(src=data_uri, width=width, height=height))

def parse_wkt_geometry(geom_val):
    """
    Parse les géométries WKT renvoyées par SPARQL / GeoSPARQL.
    Gère les préfixes du type <http://www.opengis.net/def/crs/EPSG/0/4326> POINT(...).
    """
    if isinstance(geom_val, (Point, LineString)):
        return geom_val
    if not isinstance(geom_val, str) or not geom_val.strip():
        return None
    
    # Suppression d'éventuels tags IRI GeoSPARQL
    clean_str = re.sub(r'<[^>]+>', '', geom_val).strip()
    try:
        return shapely.wkt.loads(clean_str)
    except Exception:
        # Recherche par regex si la chaîne contient d'autres informations
        match = re.search(r'POINT\s*\(\s*[-+]?\d*\.?\d+\s+[-+]?\d*\.?\d+\s*\)', clean_str, re.IGNORECASE)
        if match:
            return shapely.wkt.loads(match.group(0))
        return None


def export_graph_to_geopackage(G_agents, output_gpkg="graphe_complet.gpkg", crs="EPSG:4326"):
    """
    Exporte le graphe NetworkX G_agents en fichier GeoPackage (.gpkg) à deux couches :
    - Layer 'noeuds' : Points géolocalisés avec attributs des agents.
    - Layer 'liens'  : LineStrings entre agents avec le nombre de collaborations (weight).
    """
    def clean_label(uri):
        return str(uri).split("/")[-1].split("#")[-1].replace("_", " ")

    degres = dict(G_agents.degree())
    
    nodes_rows = []
    node_geometries = {}

    for node_id, attrs in G_agents.nodes(data=True):
        raw_geom = attrs.get('geom')
        geom_obj = parse_wkt_geometry(raw_geom)
        node_geometries[node_id] = geom_obj
        
        node_label = attrs.get('nomagent') or clean_label(node_id)
        role = attrs.get('typeAgent', '')
        
        row = {
            'uriAgent': str(node_id),
            'nomagent': str(node_label),
            'typeAgent': str(role),
            'dateDebutMin': str(attrs.get('dateDebutMin', '')),
            'dateFinMax': str(attrs.get('dateFinMax', '')),
            'adresse': str(attrs.get('adresse', '')),
            'degre': int(degres.get(node_id, 0)),
            'geometry': geom_obj
        }
        
        keys_to_skip = {'geom', 'nomagent', 'typeAgent', 'dateDebutMin', 'dateFinMax', 'adresse', 'uriAgent'}
        for k, v in attrs.items():
            if k not in keys_to_skip and k not in row:
                row[k] = str(v) if not isinstance(v, (int, float, bool)) else v
                
        nodes_rows.append(row)

    gdf_nodes = gpd.GeoDataFrame(nodes_rows, crs=crs)
    gdf_nodes_spatial = gdf_nodes[gdf_nodes['geometry'].notnull()].copy()

    # Nettoyage et typage de la couche NŒUDS
    for col in gdf_nodes_spatial.columns:
        if col == gdf_nodes_spatial.geometry.name:
            continue
        if col == 'degre':
            gdf_nodes_spatial[col] = gdf_nodes_spatial[col].astype('int64')
        else:
            gdf_nodes_spatial[col] = gdf_nodes_spatial[col].fillna("").astype(str)

    edges_rows = []
    
    for u, v, data in G_agents.edges(data=True):
        geom_u = node_geometries.get(u)
        geom_v = node_geometries.get(v)
        
        if geom_u is not None and geom_v is not None and not geom_u.is_empty and not geom_v.is_empty:
            line_geom = LineString([geom_u, geom_v])
            
            label_u = G_agents.nodes[u].get('nomagent') or clean_label(u)
            label_v = G_agents.nodes[v].get('nomagent') or clean_label(v)
            weight = int(data.get('weight', 1))
            
            edge_row = {
                'source_uri': str(u),
                'target_uri': str(v),
                'source_nom': str(label_u),
                'target_nom': str(label_v),
                'weight': weight,
                'geometry': line_geom
            }
            
            for k, val in data.items():
                if k not in edge_row:
                    edge_row[k] = str(val) if not isinstance(val, (int, float, bool)) else val
                    
            edges_rows.append(edge_row)

    gdf_edges = gpd.GeoDataFrame(edges_rows, crs=crs)

    # Nettoyage et typage de la couche LIENS
    if not gdf_edges.empty:
        for col in gdf_edges.columns:
            if col == gdf_edges.geometry.name:
                continue
            if col == 'weight':
                gdf_edges[col] = gdf_edges[col].astype('int64')
            else:
                gdf_edges[col] = gdf_edges[col].fillna("").astype(str)

    # Suppression du fichier existant pour forcer la regénération du schéma SQLite
    if os.path.exists(output_gpkg):
        os.remove(output_gpkg)
    
    # Écriture de la couche 'noeuds' (crée le nouveau GPKG)
    gdf_nodes_spatial.to_file(output_gpkg, layer="noeuds", driver="GPKG")
    
    # Ajout de la couche 'liens'
    if not gdf_edges.empty:
        gdf_edges.to_file(output_gpkg, layer="liens", driver="GPKG", mode="a")

    print(f"Export GeoPackage terminé avec succès : {output_gpkg}")
    print(f"  - Couche 'noeuds' : {len(gdf_nodes_spatial)} agents géolocalisés sur {len(gdf_nodes)} total")
    print(f"  - Couche 'liens'  : {len(gdf_edges)} liens géolocalisés (avec 'weight' en entier)")
    
    return gdf_nodes_spatial, gdf_edges


def save_global_graph_geopackage(graph, output_filename="graphe_complet.gpkg"):
    """
    Fonction wrapper équivalente à save_global_graph_html.
    """
    return export_graph_to_geopackage(graph, output_gpkg=output_filename)
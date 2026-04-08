import rdflib
from rdflib import RDF, RDFS, SKOS, DCTERMS
import networkx as nx

#chemins
input_file = "/home/vmerilan/Documents/VMerilan/rml/affiches.ttl"
output_file = "/home/vmerilan/Documents/VMerilan/rml/affiches.gexf"

#initialisation
g = rdflib.Graph()
g.parse(input_file, format="turtle")

G = nx.DiGraph()
rico = rdflib.Namespace("https://www.ica.org/standards/RiC/ontology#")

print(f"Traitement de {len(g)} triplets...")

#affiches
for record in g.subjects(RDF.type, rico.Record):
    #ids et labels
    identifier = str(g.value(record, rico.identifier)) or "Sans-ID"
    title = str(g.value(record, rico.title)) or "Sans titre"
    description = str(g.value(record, rico.generalDescription)) or ""
    
    #dates
    date_node = g.value(record, rico.hasCreationDate)
    d_start = ""
    d_end = ""
    if date_node:
        d_start = str(g.value(date_node, rico.beginningDate)) or ""
        d_end = str(g.value(date_node, rico.endDate)) or ""
    
    #reproduction
    reproduction = ", ".join([str(img) for img in g.objects(record, DCTERMS.relation)])

    #noeud avec les attributs
    G.add_node(str(record), 
               label=identifier, 
               type_entite="Affiche", 
               titre=title[:100], 
               description=description[:200],
               date_debut=d_start,
               date_fin=d_end,
               reproduction=reproduction)

#relations imprimeurs/dessinateurs
for rel in g.subjects(RDF.type, rico.CreationRelation):
    source = g.value(rel, rico.relationHasSource)
    target = g.value(rel, rico.relationHasTarget)
    role_uri = g.value(rel, rico.withCreationRole)
    
    #role (Label pour le lien)
    role_label = str(g.value(role_uri, SKOS.prefLabel)) if role_uri else "Inconnu"
    
    #nom de l'acteur (Label pour le nœud)
    person_name = str(g.value(target, rico.name)) or "Anonyme"
    
    #techniques de production (Papier, Lithographie, etc.)
    #on les cherche sur la relation de création
    techs = [str(t) for t in g.objects(rel, rico.productionTechnique)]
    tech_str = ", ".join(techs)

    if source and target:
        #determination de la catégorie (Partition)
        cat = "Dessinateur" if "Dessin" in role_label else "Imprimeur"
        
        #ajout du nœud Acteur
        G.add_node(str(target), label=person_name, type_entite=cat)
        
        #ajout du lien enrichi
        G.add_edge(str(source), str(target), 
                   label=role_label, 
                   type_lien=cat,
                   technique=tech_str)

#keywords
for record, _, subject in g.triples((None, rico.hasOrHadSubject, None)):
    G.add_node(str(subject), label=str(subject), type_entite="keyword")
    G.add_edge(str(record), str(subject), label="sujet", type_lien="Sémantique")

#exportation
nx.write_gexf(G, output_file)
print(f"File has been generated : {output_file}")
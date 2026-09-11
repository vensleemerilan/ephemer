import re
import morph_kgc
import json
import os
from rdflib import Graph, Namespace
import glob
from tqdm import tqdm
import unicodedata


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return normalized.encode("ascii", "ignore").decode("utf-8")


def main():
    base = " "
    master_graph = Graph()
    file_list = glob.glob(os.path.join(base, "*.json"))
    print(f"{len(file_list)} fichier(s) JSON trouvé(s) dans le dossier.")

    for file in tqdm (file_list, desc= "Traitement des fichiers", unit="fichier"):
        print(file)
        object_number = os.path.splitext(os.path.basename(file))[0]
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["object_number"] = object_number

        personnes = []
        organisations = []
        lieux = []
        produits = []
        autres = []

        liste_entites = data.get("entites") or data.get("commanditaires") or []
        for entite in liste_entites:
            
            entite["object_number"] = object_number
            entite["nom_norm"] = remove_accents((entite["nom"] or 'inconnu').replace(' ','-').lower())

            cat = entite.get("categorie")

            if cat == "Personne":
                personnes.append(entite)
            elif cat == "Organisation":
                organisations.append(entite)
            elif cat == "Lieu":
                lieux.append(entite)
            elif cat == "Produit":
                produits.append(entite)
            else:
                entite["categorie"]  ="Autre"
                entite["explication"] += ". Entité sans catégorie extraite, forcée à AUTRE."
                autres.append(entite)

        data["personnes"] = personnes
        data["organisations"] = organisations
        data["lieux"] = lieux
        data["produits"] = produits
        data["autres"] = autres

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        sub_graph = morph_kgc.materialize("config.ini")

        master_graph += sub_graph
    master_graph.bind("rico", Namespace("https://www.ica.org/standards/RiC/ontology#"))
    master_graph.bind("eph", Namespace("http://rdf.geohistoricaldata.org/id/museeCarnavalet/ephemeres/"))
    master_graph.bind("adb", Namespace("http://data.soduco.fr/def/annuaire#"))
    master_graph.bind("skos", Namespace("http://www.w3.org/2004/02/skos/core#"))
    master_graph.bind("rdfs", Namespace("http://www.w3.org/2000/01/rdf-schema#"))
    
    master_graph.serialize(destination="graphe_commanditaires.ttl", format="turtle")

    print(f"graphe global généré")

if __name__ == "__main__":
    main()
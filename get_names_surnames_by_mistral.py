#Imports
import os
from pydantic import BaseModel
from mistralai.client import Mistral
import time
from dotenv import load_dotenv
import csv
import json
from rdflib import Graph
from tqdm import tqdm

FILE_PATH = r"/home/vmerilan/Documents/VMerilan/scripts/algo_traitement_v1/v1_exec/graph_affiches.ttl" 

#Secure loading
load_dotenv()
api_key = os.environ["MISTRAL_API_KEY"]
model = "ministral-8b-latest"
client = Mistral(api_key=api_key)

#classes
class Individual(BaseModel):
    nom: str
    prenoms: list[str]

class ListOfIndividuals(BaseModel):
    individuals: list[Individual]


text_input: str = "Imprimerie H. Laas" #fIX THIS


instructions_system = """
                   Tu es un expert en traitement de données historiques et en généalogie commerciale
                   pour le projet EPHEMER.
Ta mission est d'extraire les individus des raisons sociales d'annuaires de commerce. Il faut aussi veiller 
à distinguer les individus uniques des associations de partenaires

### REGLES STRICTES :
1. Ne devine JAMAIS un prénom s'il n'est pas écrit.
2. Sépare bien le NOM de l'activité.
3. Si plusieurs personnes sont citées (ex: 'et fils'), crée un objet par personne.

###CAS PARTICULIERS A PRENDRE EN COMPTE
1. **CAS DE L'INDIVIDU UNIQUE (La Virgule) :**
   - Si tu vois "NOM, Prénom", c'est UNE SEULE personne. 
   - La virgule indique que le nom a été placé devant pour le classement alphabétique.
   - EXEMPLE : "Jean, Jacques" -> Nom: Jean, Prénom: Jacques.

2. **CAS DE L'ASSOCIATION (Le "et" ou "&") :**
   - Si tu vois "A et B" ou "A & B", ce sont DEUX personnes distinctes.
   - Si un seul prénom est présent (ex: "Benoit et fils"), crée deux objets avec le même nom.
   - EXEMPLE : "Benoit et Albert" -> 1. BENOIT (prénom ) / 2. ALBERT (nom ALBERT, prénom ).

3. **PRIORITÉ AU NOM DE FAMILLE :**
   - Dans un annuaire, le premier mot est presque TOUJOURS le nom de famille. 
   - Même si "Guillaume" peut être un prénom, s'il est en début de ligne avant une virgule, traite-le comme un NOM.

4. **DÉTECTION PAR INITIALE :**
   - Si un mot est réduit à une lettre suivie d'un point (ex: "G."), il est obligatoirement le PRÉNOM, peu importe sa position.

### RÈGLES DE SORTIE :
- Ne crée pas deux individus si le texte contient une virgule mais pas de "et/&".

### LOGIQUE DE DÉCISION (CRITIQUE) :
- SI l'entrée contient une VIRGULE sans "et/&" -> ALORS 1 seul individu (Ordre: NOM, Prénom).
- SI l'entrée contient "et", "&", "fils", "successeurs" -> ALORS Scission en plusieurs individus.
- SI l'entrée contient des PARENTHÈSES -> Ignore le contenu informatif pour ne garder que l'identité principale.

### EXEMPLE TYPE 1:
Entrée : "Imprimerie G. Benoit"
Sortie : {"individuals": [
                        {"nom": "Benoit", 
                        "prenoms": ["G."]
                        }
                        ]
        }

### EXEMPLE TYPE 2:
Entrée : "Imprimerie Gerard Auteuil"
Sortie : {"individuals": [
                        {"nom": "Auteuil", 
                        "prenoms": ["Gerard"]
                        }
                        ]
        }

### EXEMPLE TYPE 3:
Entrée : "Lithographie A. Rousseau"
Sortie : {"individuals": [
                        {"nom": "Rousseau", 
                        "prenoms": ["A."]
                        }
                        ]
        } 

### EXEMPLE TYPE 4:
Entrée : "Degranger ou de Granger, Jean-Francois"
Sortie : {"individuals": [
                        {"nom": "Degranger", 
                        "prenoms": ["Jean-Francois"]
                        }
                        ]
        } 

### EXEMPLE TYPE 5:
Entrée : "Vizzi (J. Vizzi da Pinto, dit)"
Sortie : {"individuals": [
                        {"nom": "Vizzi", 
                        "prenoms": ["J."]
                        }
                        ]
        } 

### EXEMPLE TYPE 6:
Entrée : "Typographie Morris père et fils"
Sortie : {"individuals": [
                        {"nom": "Morris", 
                        "prenoms": ["Père"]
                        },
                        {"nom": "Morris", 
                        "prenoms": ["Fils"]
                        }
                        ]
        } 

### EXEMPLE TYPE 7:
Entrée : "Leclerc et Juissien Lithographie"
Sortie : {"individuals": [
                        {"nom": "Leclerc", 
                        "prenoms": [""]
                        },
                        {"nom": "Juissien", 
                        "prenoms": [""]
                        }
                        ]

         } 

### EXEMPLE TYPE 8:
Entrée : "Justineau"
Sortie : {"individuals": [
                        {"nom": "Justineau", 
                        "prenoms": [""]
                        }]
        } 


"""

#Ce code doit aller voir dans le graphe indique et relever tous les dessinateurs et imprimeurs, cela peut e faire facilement avec rdflib qui permet d'ecrire du sparql dans python

# Initialisation du graphe
g = Graph()

# Charge ton fichier (ajuste le format "xml" ou "turtle" selon ton fichier)
g.parse(FILE_PATH, format="turtle") 

# Requête pour lier l'agent, son nom et les dates du document source
query = """
PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?agent ?nomagent ?rolelabel (MIN(?debut) AS ?dateDebutMin) (MAX(?fin) AS ?dateFinMax)
WHERE {
    ?rel a rico:CreationRelation ;
         rico:withCreationRole ?role ;
         rico:relationHasTarget ?agent ;
    	 rico:relationHasSource ?s .
         
    
    ?agent rico:name ?nomagent .
    ?role skos:prefLabel ?rolelabel .
    
    ?s rico:hasCreationDate ?date .
    ?date rico:beginningDate ?debut ;
          rico:endDate ?fin .
}
GROUP BY ?agent ?nomagent ?rolelabel
"""

# On exécute la requête
results = g.query(query)

# 1. On crée la liste complète (Dictionnaire pour chaque ligne)
resultats_complets = []
for row in results:
    resultats_complets.append({
        "uri": str(row.agent),
        "nom_agent": str(row.nomagent),
        "role": str(row.rolelabel),
        "debut": str(row.dateDebutMin),
        "fin": str(row.dateFinMax)
    })

# 2. On extrait la liste simple des noms à partir de cette liste
noms_brut = [agent["nom_agent"] for agent in resultats_complets]


result  = {}
print("Debut de l'extraction avec Mistral...")
#faire une boucle Pour chaque  individu dessinateur ou imprimeur
for item in tqdm(noms_brut, desc="Extraction des individus", unit="nom"):
    try:
        chat_response = client.chat.parse(
            model=model, #fix variable in the beginning
            messages=[
                {
                    "role": "system",
                    "content": instructions_system #Mes instructions la plus haut
                },
                #le content c'est ce que je lui dis de faire
                {
                    "role": "user",
                    "content": item #On traite chaque item
                },
            ],
            response_format=ListOfIndividuals,
            max_tokens=1024,
            temperature=0
    )
        
        response_object = chat_response.choices[0].message.content

        if response_object is not None:
                result[item] = response_object
                            
    except Exception as e:
            tqdm.write(f" Erreur sur '{item}': {e}")
        
    time.sleep(0)

# TEST RAPIDE SANS MISTRAL
#result = {"Imprimerie H. Laas": ListOfIndividuals(individuals=[Individual(nom="Laas", prenoms=["H."])])}

headers = ["entree", "nom", "prenoms"]

csv_file = "../individus_extraits.csv"
with open(csv_file, mode="w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    
    # On parcourt nos résultats
    for ligne_brute, response_object in result.items():
        if isinstance(response_object, str):
            try:
                # On transforme le texte JSON en dictionnaire
                data_dict = json.loads(response_object)
                # On force la conversion vers ta classe Pydantic
                response_object = ListOfIndividuals(**data_dict)
            except Exception:
                print(f"Impossible de parser le texte pour : {ligne_brute}")
                continue # On passe à la ligne suivante en cas d'échec critique

        # Maintenant, response_object est forcément un objet avec .individuals
        for individu in response_object.individuals:
            writer.writerow({
                "entree": ligne_brute,
                "nom": individu.nom,
                "prenoms": ", ".join(individu.prenoms)
            })

print(f"\n Exportation réussie ! Ton fichier est ici : {csv_file}")

#Maintenant, il faut creer un csv avec les colonnes suivantes:  nom, prenom, type, debut, fin

# 1. Définir d'abord le nom du fichier et les colonnes
final_csv = "./individus_normalises.csv"
headers = ["uri", "nom", "prenom", "type", "debut", "fin"]

print(f"Fusion des données et création de {final_csv}...")

with open(final_csv, mode="w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()

    # On parcourt la liste des données issues du RDF (qui contient dates et rôles)
    for agent_data in resultats_complets:
        # On récupère le nom brut (la clé de liaison)
        cle_nom = agent_data["nom_agent"] 
        
        # On regarde si Mistral a traité ce nom
        if cle_nom in result:
            response_object = result[cle_nom]
            
            # Gestion du cas où l'objet est encore une string JSON
            if isinstance(response_object, str):
                try:
                    data_dict = json.loads(response_object)
                    response_object = ListOfIndividuals(**data_dict)
                except:
                    continue

            # On crée une ligne pour chaque personne trouvée par l'IA dans cette entrée
            for persona in response_object.individuals:
                writer.writerow({
                    "uri": agent_data["uri"],
                    "nom": persona.nom,            # Nom nettoyé (Mistral)
                    "prenom": ", ".join(persona.prenoms), # Prénom nettoyé (Mistral)
                    "type": agent_data["role"],    # Rôle (RDF)
                    "debut": agent_data["debut"],  # Date début (RDF)
                    "fin": agent_data["fin"]       # Date fin (RDF)
                })

print(f"Exportation réussie ! {final_csv} contient toutes les données fusionnées.")
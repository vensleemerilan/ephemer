![Knowledge Graph](https://img.shields.io/badge/Knowledge%20Graph-005A9C?style=for-the-badge&logo=graphy&logoColor=white)
![Ontology](https://img.shields.io/badge/Ontology-333333?style=for-the-badge&logo=w3c&logoColor=white)
![RML](https://img.shields.io/badge/RML-Mapping-green?style=for-the-badge)
![CARML](https://img.shields.io/badge/CARML-Engine-orange?style=for-the-badge&logo=java&logoColor=white)
![Turtle](https://img.shields.io/badge/RDF-Turtle-yellow?style=for-the-badge&logo=w3c&logoColor=333333)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Jupyter Notebook](https://img.shields.io/badge/Jupyter-F37626?style=for-the-badge&logo=jupyter&logoColor=white)
![SPARQL](https://img.shields.io/badge/SPARQL-4285F4?style=for-the-badge&logo=semantic-web&logoColor=white)

# EPHEMER

**Auteur:** Venslee MERILAN  
**Institution:** EHESS (Ecole des Hautes Etudes en Sciences Sociales)  
**Partenaires:** Musée Carnavalet - Histoire de Paris, IGN  
**Role:** Stage en Géomatique et Graphe de connaissances(Mars – Septembre 2026)
-----

## 📌 Résumé du projet

Le projet **EPHEMER** vise à étudier les réseaux professionnels spatialisés qui ont concouru à la  création, l’impression et la diffusion des affiches éphémères du fonds du musée Carnavalet.

-----

## 🛠️ Sources et méthodes
### 1\. Sources de données 
a) [SODUCO](https://soduco.geohistoricaldata.org/)  

Ce projet utilise des données produites dans le cadre du projet **SODUCO** qui avait scanné, extrait et organisé en une base de données l'ensemble des entrées d'un corpus d'annuaires du commerces parisiens historiques.


b) Métadonnées du fonds d'affiches du musée Carnavalet 

Consistant en des informations sur les affiches et leurs producteurs

### 2\. Création du graphe de connaissances
Création d'un graphe de connaissances à partir des métadonées en format xml fournies par le musée. Ce graphe a été créé en utilisant le moteur de transformation déclarative [Carml](https://github.com/carml/carml) basé sur le langage RML. Cette transformation prend en entrée le fichier xml de métadonnées ainsi que le fichier de règles *mapping_affiches.ttl* . Le résultat est un graphe de connaissances en format turtle (.ttl)

### 3\. Extraction des types d'affiches et des commanditaires
Catégorisation des affiches selon leur sujet et extraction des commanditaires de ces affiches. Cette extraction (*extraction_commanditaires_categoriesAffiches_ollama.py*) a été réalisée à l'aide d'un LLM en l'occurence le modèle Gemma 4 et utilise les métadonnées sur les affiches.
Des catégories "fines" ont été déterminées par l'IA et ont été ensuites grossies pour en faire des plus générales. Le script *extraction_type_categories.py* relève tous les types déterminés par le LLM et les place dans un fichier csv.
Le script *integration_graphe_commanditaires.py* transforme les informations extraites sur les commanditaires en un graphe nommé qui doit être intégré au graphe géneral des affiches.

### 4\. Exploration des données
Exploration des données faite à l'aide de notebooks python et se penche sur la répartition temporelle de la production des affiches présentes dans ce fonds. Les notebooks *exploration_corpus.ipynb* et *exploration_production_agents.ipynb* interrogent le graphe de connaissances des affiches et ressortent des graphiques.
 
### 5\. Liage des agents du graphe des affiches avec le corpus numérique des entrées d’annuaire du commerce 
Le liage des agents du graphe de connaissances des affiches avec le corpus numérique des entrées d’annuaires du commerce consiste en la création de liens de correspondance entre les agents du graphe des affiches avec les entités leur correspondant dans le corpus des entrées d’annuaires.

Pour cette étape, notre extrait de [la base de données des entrées d'annuaires](https://nakala.fr/collection/10.34847/nkl.abe0gxah) est interrogée à l'aide des fonctions sql du fichier *process_functions.sql*.

Pour lancer le processus sur toutes les données, il a fallu au préalable, extraire certaines informations sur les agents tels que les noms et les prénoms en utilisant le du modèle ministral-8b dans le script *get_names_surnames_by_mistral.py*.

Une fois la liste des agents obtenue, le processus de recherche dans les données d'annuaires du commerce peut etre lancé. Ceci est réalisé avec le script python *process.py* et aboutit à la création de tables au niveau de la base de données contenant tous les résultats de la recherche.

Les résultats de la recherche ont ensuite été intégrés dans le graphe de connaissances. Chaque catégorie de résultat a été mappée en graphe de connaissances puis rattachée au graphe originel. Le mapping de ces résultats a été fait avec le moteur de transformation R2RML Parser.
Les fichiers de mapping utilisés: *mapping_entrees_annuaires_closematch.ttl, mapping_entrees_annuaires_exactmatch.ttl, mapping_entrees_annuaires_relatedmatch.ttl, mapping_entrees_annuaires_seealso.ttl*.

Dans ce travail, les résultats avec la notion seealso n'ont pas été considérés.
Le paramétrage se fait avec: *r2ml.properties*
*ttl2gexf* permet d'exporter le graphe en gexf, format lisible par gephi.
*utils.py* contient des fonctions utilisées dans les autres scripts.
*prefix.yaml* contient les préfixes utilisés pour le mapping des résultats.

### 6\. Exploration des réseaux professionnels
Cette étape permet d'explorer les réseaux professionnels localisés.

*   Le notebook *cartes_ego_profondeur2.ipynb* permet de générer une carte pour chaque réseau égocentré du graphe, il utilise le graphe de connaissances;
*   Le script *export_reseau_ego_prof2.py* permet d'exporter les composantes du graphe et de calculer des métriques, il interroge le graohe de connaissances;
*   *genaration_gpkgs.py* permet de générer des gpkgs à partir d'une table de résultats créée à l'étape précédente;
*   *generation_gpkg_pour_carto.ipynb* interroge le graphe de connaissances pour créer des gpkgs utiles à la cartographie du projet;
*   les 2 scripts *creation_tableau_apercu_general.py* et *creation_tableau_verification.py* permettent de générer des fichiers de vérification et validation utilisés par les experts du Musée Carnavalet Histoire de Paris dans la suite du projet;
*   *requete_evol_adresses_temps.sparql* est un script sparql permettant d'obtenir un tableau dans lequel on peut voir l'évolution des des adresses des agents dans le temps;

*   *utils.py* contient des fonctions utilisées dans certains des scripts;
*   *verification_coherence_graphe_des_affiches.md* contient un script sparql utilisée pour s'assurer de l'intégrité du graphe;
*   *graphe_global.py* permet d'avoir le graphe complet en version html et en gpkg en interrogeant le graphe de connaissances;
*   *calcul_metriques_graphe_rapport.py* permet de générer un geopackage avec les agents localisés et les liens de collaborations ainsi que des statistiques calculées;
*   *comparaison_liensreels_hasard.ipynb* et *rapport_distances.ipynb* permettent de faire des analyses sur le réseau de collaboration de production d'affiches de Paris.

-----

## 📁 Structure du dossier

```text
.
├── 01_creation_du_graphe_de_connaissances_des_affiches
│   ├── apply_rdfmapping.sh
│   ├── mapping_affiches.ttl
│   └── prefixes.yaml
├── 02_extraction_des_types_daffiches_et_des_commanditaires
│   ├── extraction_commanditaires_categoriesAffiches_ollama.py
│   ├── extraction_type_categories.py
│   ├── integration_graphe_commanditaires.py
│   ├── mapping_commanditaires.ttl
│   └── pyproject.toml
├── 03_exploration_des_donnees
│   ├── exploration_corpus.ipynb
│   └── exploration_production_agents.ipynb
├── 04_liage_des_agents_a_leurs_correspondances_dans_les_annuaires
│   ├── get_names_surnames_by_mistral.py
│   ├── mapping_entrees_annuaires_closematch.ttl
│   ├── mapping_entrees_annuaires_exactmatch.ttl
│   ├── mapping_entrees_annuaires_relatedmatch.ttl
│   ├── mapping_entrees_annuaires_seealso.ttl
│   ├── prefixes.yaml
│   ├── process_functions.sql
│   ├── process.py
│   ├── r2rml.properties
│   ├── ttl2gexf.py
│   └── utils.py
├── 05_exploration_des_reseaux_professionnels
│   ├── calcul_metriques_graphe_rapport.py
│   ├── cartes_ego_profondeur2.ipynb
│   ├── comparaison_liensreels_hasard.ipynb
│   ├── creation_tableau_apercu_general.py
│   ├── creation_tableau_verification.py
│   ├── export_reseau_ego_prof2.py
│   ├── generation_gpkg_pour_carto.ipynb
│   ├── generation_gpkgs.py
│   ├── graphe_global.py
│   ├── rapport_distances.ipynb
│   ├── requete_evol_adresses_temps.sparql
│   ├── utils.py
│   └── verification_coherence_graphe_des_affiches.md
├── README.md
└── requirements.txt
```

-----
## ⚙️ Spécifications techniques

### 🛠️ Environnement & Dépendances

| Composant | Technologie / Modèle | Usage / Rôle |
| :--- | :--- | :--- |
| **Langage principal** | Python `>= 3.10` | Traitements de données, notebooks d'analyse, scripts d'extraction |
| **Moteur RDF (XML)** | [CARML Engine](https://github.com/carml/carml) | Exécution des règles RML pour la transformation XML -> RDF |
| **Moteur RDF (SQL / RDB)** | R2RML Parser | Mapping R2RML pour intégrer les résultats SQL dans le graphe |
| **Moteur RDF** | [Morph](https://github.com/oeg-upm/morph-rdb)| Intégration des commanditaires dans le graphe |
| **SGBD Relationnel** | PostgreSQL / PostGIS | Stockage et requêtage SQL de la base des annuaires SODUCO |
| **LLM Locaux** | Ollama (`Gemma 4`), `Mistral-8B` | Extraction entités (commanditaires, catégories) & parsing des identités |
| **Analyse Spatiale & SIG** | GeoPandas, QGIS | Génération de couches GeoPackage (`.gpkg`) et représentations cartographiques |
| **Analyse Réseau** | NetworkX, Gephi | Calcul de métriques de graphe et export des réseaux (`.gexf`, HTML) |

---


### 📦 Dépendances Python principales

| Domaines | Bibliothèques clés |
| :--- | :--- |
| **Web Sémantique & RDF** | `rdflib` (`7.6.0`), `morph-kgc` (`2.3.1`), `sparqlwrapper` (`2.0.0`), `pyoxigraph` (`0.5.9`) |
| **Géo-Spatial & SIG** | `geopandas` (`1.1.3`), `osmnx` (`2.1.1`), `shapely` (`2.1.2`), `rasterio` (`1.5.0`), `pyproj` (`3.7.2`), `fiona` / `pyogrio` (`0.12.1`) |
| **Analyse Réseau & Graphes** | `networkx` (`3.6.1`), `pyvis` (`0.3.2`) |
| **IA & LLM API** | `mistralai` (`2.4.4`), `httpx` (`0.28.1`) |
| **Bases de données SQL** | `sqlalchemy` (`2.0.51`), `psycopg2` (`2.9.12`), `duckdb` (`1.5.5`) |
| **Data Science & Stats** | `pandas` (`3.0.2`), `numpy` (`2.4.4`), `scikit-learn` (`1.9.0`), `scipy` (`1.18.1`), `pointpats` (`2.6.0`), `libpysal` (`4.15.0`) |
| **Visualisation** | `matplotlib` (`3.11.0`), `seaborn` (`0.13.2`), `folium` (`0.20.0`), `contextily` (`1.7.0`) |

> 💡 *La liste complète et exacte de toutes les sous-dépendances est disponible dans le fichier [`requirements.txt`](./requirements.txt).*

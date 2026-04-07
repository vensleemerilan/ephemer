# EPHEMER

**Author:** Venslee MERILAN  
**Institution:** EHESS (Ecole des Hautes Etudes en Sciences Sociales)  
**Partner:** Musée Carnavalet - Histoire de Paris, IGN  
**Role:** Geomatics and Knowledge graphs Engineer Internship (March – September 2026)
-----

## 📌 Project Overview

The **EPHEMER** project focuses on the study of historical "ephemera" (posters, notices, trade cards) from the Musée Carnavalet collection.

The core mission is to **propose a methodology** based on the creation, population, and analysis of a **Knowledge Graph**. This structured approach allows researchers to study the **professional networks** involved in the creation, printing, and distribution of these documents in historical Paris.

-----

## 🛠️ Methodology & Data Sources

The project implements a full Semantic Web stack to transition from flat museum records to a relational network analysis:

### 1\. Data Integration 
a) SODUCO Project  

This project leverages data produced by the **SODUCO project**, which digitized and processed historical Parisian directories (the ancestors of the "Yellow Pages") from **1798 to 1914**.

  * **Source:** Historical trade directories (Annuaires du commerce) from Parisian Libraries.
  * **Usage:** Cross-referencing names, addresses, and professions of printers and distributors found in the ephemera with the SODUCO spatialized database.
The ultimate output of the soDUCO project is a Web-based GIS Application designed for the spatial discovery of historical trade data.
  * **Interactive Mapping:** Enables users to visualize and filter directory entries directly on a historical map of Paris.
  * **Spatiotemporal Analysis:** Tracks the evolution and geographic distribution of professional networks (printers, publishers, artists) from 1798 to 1914.

b) The metadata on the historical ephemeras from the Musée Carnavalet collection  

Which consists on identity information on creators of the ephemeras (drawers and printers), date of creation, places and more.

### 2\. Modeling & Population

  * Developing a methodology to create and populate a Knowledge Graph from heterogeneous XML records. 
 
### 3\. Network Analysis
* Analyzing the graph to identify the key stakeholders and central actors in the production of ephemera;
* Professional Networks: Studying the connections between printers, illustrators, and publishers through graph-based queries (SPARQL).
* Spatial Logic: Leveraging geolocated data to highlight the spatial organization and distribution patterns of professional networks related to "ephemera" in 19th-century Paris.
* Pattern Identification: Identifying hidden connections and socio-geographic clusters in the production and diffusion of historical documents throughout the 19th and early 20th centuries.

-----

## 📁 Repository Structure

```text
.
├── xml2rdf/
│   ├── example/             # Sandbox / Ready-to-use Trial
│   │   ├── echantillon.xml  # Sample source data (Musée Carnavalet)
│   │   ├── mapping.ttl      # Test RML mapping rules
│   │   ├── prefixes.yaml    # Namespace management
│   │   └── apply_rdfmapping.sh # Execution script
│   └── mapping/             # Production / Final Mappings
│       ├── mapping_affiches.ttl # Final mapping for "Affiches" (Posters)
│       ├── prefixes.yaml    # Production namespaces
│       └── apply_rdfmapping.sh  # Batch transformation script
├── link_to_carml_software.txt # Documentation/Links for the Carml engine
└── README.md
```

-----

## 🚀 Getting Started & Trial

### Quick Start (Trial Mapping)

The `xml2rdf/example/` directory contains a **complete standalone sample**. Everything needed to test the mapping is included in the folder:

1.  Navigate to the example folder:
    ```bash
    cd xml2rdf/example
    ```
2.  Ensure the script has execution permissions:
    ```bash
    chmod +x apply_rdfmapping.sh
    ```
3.  Run the trial mapping:
    ```bash
    ./apply_rdfmapping.sh
    ```

*This will process the `echantillon.xml` file using the provided `mapping.ttl` rules and output the resulting RDF triples.*

-----

## ⚙️ Technical Specifications

  * **Mapping Language:** RML (RDF Mapping Language).
  * **Engine:** [Carml](https://github.com/carml/carml).
  * **Output Formats:** RDF (Turtle, N-Triples).
  * **Key Context:** Spatial and temporal data from SODUCO (1798-1914).

-----

## ⚖️ License & Confidentiality

The raw XML source files belong to the **Musée Carnavalet**. This repository only contains transformation scripts and ontologies.

# Lister les affiches avec plusieurs titres ou plusieurs hasCreationDate

PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>

SELECT ?s (COUNT(DISTINCT ?titre) AS ?countTitles) (COUNT(DISTINCT ?date) AS ?countDates)
WHERE {
  ?s a rico:Record .
  OPTIONAL { ?s rico:title ?titre }
  OPTIONAL { ?s rico:hasCreationDate ?date }
}
GROUP BY ?s
HAVING (?countTitles > 1 || ?countDates > 1)

# Afficher le nombre de titres, de dates de création et d'agents Imprimeurs et Dessinateurs pour chaque affiche

PREFIX rico: <https://www.ica.org/standards/RiC/ontology#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT (?s AS ?uriAffiche) 
       (COUNT(DISTINCT ?titre) AS ?nbTitles) 
       (COUNT(DISTINCT ?date) AS ?nbCreationDates) 
       (COUNT(DISTINCT ?uriAgent) AS ?nbAgents)
WHERE {
  ?s a rico:Record .
  
  # Optional title count
  OPTIONAL { ?s rico:title ?titre }
  
  # Optional creation date count
  OPTIONAL { ?s rico:hasCreationDate ?date }
  
  # Optional matching agent count
  OPTIONAL {
    ?rel rico:relationHasSource ?s .
    ?rel rico:withCreationRole ?role .
    ?role skos:prefLabel ?typeAgent .
    ?rel rico:relationHasTarget ?uriAgent .
    ?uriAgent rico:name ?nomAgent .
    FILTER(LCASE(STR(?typeAgent)) IN ("imprimeur", "dessinateur"))
  }
}
GROUP BY ?s
ORDER BY DESC(?nbTitles) DESC(?nbCreationDates)

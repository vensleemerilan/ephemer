import os
from ollama import chat
from pydantic import BaseModel, Field
import json
import loguru 
from tqdm import tqdm

import xml.etree.ElementTree as ET

logger = loguru.logger
logger.add("extraction_commanditaires_ollama.log", rotation="10 MB", retention="10 days", level="DEBUG", backtrace=True, diagnose=True)


class Entité(BaseModel):
	nom: str | None = Field(description="Nom de l'entité (personne, lieu ou organisation) tel qu'il apparaît dans le XML, ou null si absent.")
	categorie: str = Field(description="Type d'entité, à choisir strictement parmi : Lieu, Personne, Organisation, Produit, Autre.")
	adresse: str | None = Field(description="Adresse liée à cette entité si elle est mentionnée dans le XML, ou null si absent.")
	explication: str = Field(description="Justification courte (1 phrase) démontrant pourquoi cette entité est au centre du message de l'affiche.")
	
class Affiche(BaseModel):
	type_affiche: str = Field(description="Type d'affiche")
	entites: list[Entité] = Field(description="Liste des entités mises en avant par l'affiche, avec leur nom, catégorie, adresse et explication.")


SYSTEM_PROMPT = """Tu es un expert en extraction d'information à partir de métadonnées XML d'affiches anciennes.
Ton rôle est d'analyser le XML fourni au prochain input et d'extraire les données sous forme de JSON strict.

# Contraintes strictes :
1. Suis exactement le schéma JSON donné.
2. Si une information est absente, utilise `null` (pour les chaînes) ou une liste vide `[]` (si aucune entité n'est trouvée).

# Définitions des champs :
* **`type_affiche`** : Description très courte (max 5 mots) du type d'affiche, déduit du titre, de la description et des notes (ex: "Affiche de spectacle de cirque", "Affiche publicitaire pour boisson", etc.). Propose ta propre typologie.
* **`entites`** (liste) : Les sujets clés mis en avant, promus ou célébrés par l'affiche. Il peut s'agir d'un lieu (théâtre, hippodrome, cabaret), d'une personne (artiste, interprète, auteur) ou d'une organisation/marque.

## Chaque objet de la liste `entites` doit contenir :
  - `nom` : Le nom de l'entité tel qu'il apparaît (ou `null`).
  - `categorie` : Le type d'entité, à choisir strictement parmi : `Lieu`, `Personne`, `Organisation`, `Produit`, `Autre`.
  - `adresse` : L'adresse liée à cette entité si elle est mentionnée (ou `null`).
  - `explication` : Justification courte (1 phrase) démontrant pourquoi cette entité est au centre du message de l'affiche, en citant les balises XML utilisées pour l'identifier.


## Règles importantes :
- **Ignore tous les acteurs liés à la production de l'affiche elle-même** : imprimeur, éditeur, dessinateur, lithographe, etc. SAUF s'ils sont explicitement l'objet de la promotion de l'affiche.
- Conserve la casse exacte des noms et titres tels qu'ils apparaissent dans le XML.
"""

EXAMPLE_XML = """<record><object_number>CARAFF00145</object_number><title>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</title><description.iconographical_description>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier, Diverses vignettes: Personnage de Cendrillon et sa marraine près d'un carrosse, bal, triomphe de Cendrillon avec danseuses, fée posant sa baguette sur deux jeunes filles: l'une en haillons, l'autre en robe de bal, sur un escalier, homme tenant une lanterne, au sol chaussure, groupe de gardes tenant des lanternes</description.iconographical_description><inscription.transliteration>" THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7h 1/2/ THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON/ 100/ DANSEUSES "</inscription.transliteration><inscription.transliteration>Sur tout le bas: " IMP. H. LAAS 16, R. PIERRE-LEVEE PARIS "</inscription.transliteration><inscription.transliteration>B.D.: " CARNAVALET "</inscription.transliteration><inscription.transliteration>H.D. timbre fiscal 20 centimes</inscription.transliteration><inscription.transliteration>H.D.: " [?] 1 OCTOBRE 1879 "</inscription.transliteration><temp.title_text>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</temp.title_text><themes_sujets.theme_commentaire>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Cendrillon, Acteur, Actrice, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier</themes_sujets.theme_commentaire><opac_word_index>Affiche</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier, Diverses vignettes: Personnage de Cendrillon et sa marraine près d'un carrosse, bal, triomphe de Cendrillon avec danseuses, fée posant sa baguette sur deux jeunes filles: l'une en haillons, l'autre en robe de bal, sur un escalier, homme tenant une lanterne, au sol chaussure, groupe de gardes tenant des lanternes</opac_word_index><opac_word_index>Théâtre de la Porte Saint-Martin (Paris)</opac_word_index><opac_word_index>Affiche</opac_word_index><opac_word_index>Arts graphiques</opac_word_index><opac_word_index>Estampe</opac_word_index><opac_word_index>Publicité</opac_word_index><opac_word_index>Lithographie couleur sur papier</opac_word_index><opac_word_index>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</opac_word_index><opac_word_index>Papier</opac_word_index><opac_word_index>Lithographie</opac_word_index><opac_word_index>Anonyme</opac_word_index><opac_word_index>Imprimerie H. Laas</opac_word_index></record>"""

EXAMPLE_JSON = """{
  "type_affiche": "Affiche de spectacle de ballet",
  "entites": [
    {
      "nom": "THEATRE DE LA PORTE ST. MARTIN",
      "categorie": "Lieu",
      "adresse": "Paris, 10è arrondissement",
      "explication": "Le lieu est identifié dans les balises <title>, <inscription.transliteration> et <description.iconographical_description>. Il s'agit du théâtre parisien accueillant la représentation promue par l'affiche."
    },
    {
      "nom": "CENDRILLON",
      "categorie": "Produit",
      "adresse": null,
      "explication": "Le titre de l'œuvre apparaît de manière centrale dans <title> et <inscription.transliteration>. Le champ <description.iconographical_description> montre de nombreuses vignettes illustrant directement des scènes de ce grand ballet."
    },
    {
      "nom": "THEO VAN-GHELL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionné comme interprète principal dans <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Sa présence en tête d'affiche démontre son importance centrale pour la promotion du spectacle."
    },
    {
      "nom": "ALINE DUVAL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionnée parmi les vedettes du spectacle dans <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Elle figure en haut de l'affiche pour attirer le public au théâtre."
    },
    {
      "nom": "RAVEL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionné sous forme de nom de scène ou patronyme dans <title>, <inscription.transliteration> et <description.iconographical_description>. Il fait partie des comédiens ou danseurs principaux mis en valeur pour cette production."
    },
    {
      "nom": "ALEXANDRE",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Nom de l'artiste présent dans les balises <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Il fait partie de la troupe d'acteurs clés mis en avant par la publicité."
    },
    {
      "nom": "GOBIN",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Nom présent dans les balises de titre (<title>) et de transcription (<inscription.transliteration>). Cet interprète contribue à la notoriété et à l'attrait de la distribution du ballet."
    },
    {
      "nom": "TISSIER",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Dernier artiste nommé de la distribution principale dans <title> et <inscription.transliteration>. Il complète la liste des interprètes notables dont le nom sert d'argument publicitaire."
    }
  ]
}"""


def query_ollama(user_input, model='gemma4:31b') -> Affiche:
	response = chat(
	  model=model,
	  messages=[
		{'role': 'system', 'content': SYSTEM_PROMPT},
		
		{'role': 'user', 'content': EXAMPLE_XML},
		
		{'role': 'assistant', 'content': EXAMPLE_JSON},
		
		{'role': 'user', 'content': user_input}
	  ],
	  format=Affiche.model_json_schema(),
	  options={
        "temperature": 0.0,      
        "num_predict": 10_000,    
      }
	)

	affiche = Affiche.model_validate_json(response.message.content)
	return affiche


def remove_unused_xml_fields(record: ET.Element) -> ET.Element:
	unwanted_tags = [
		"identification.record_type",
		"identification.situation_objet",
		"object.number_type",
		"WorkRef",
		"related_object",
		"institution.name",
		"current_owner",
		"Reproduction",
		"web_display",
		"marking",
		"acquisition",
		"Constat",
		"ConstatSupport",
		"add",
		"Dimension",
		"Rights",
		"management",
		"Frame",
		"Production"
	]

	for tag in unwanted_tags:
		for elem in record.findall(tag):
			record.remove(elem)

	return record
import xml.etree.ElementTree as ET

def keep_only_relevant_xml_fields(record: ET.Element) -> ET.Element:
    """
    Filtre un XML pour ne garder que les champs pertinents sous forme de clés/valeurs simples,
    sans attributs et aplatit la structure.
    """
    new_record = ET.Element(record.tag)
    
    relevant_tags = [
        ["object_number"],
        ["Title", "title"],
        ["Content_icon", "description.iconographical_description"],
        ["Inscription", "inscription.transliteration"],
        ["temp.title_text"],
        ["themes_sujets.theme_commentaire"],
        ["opac_word_index"]
    ]

    for path in relevant_tags:
        xpath_str = "/".join(path)
        for found_elem in record.findall(f".//{xpath_str}"):
            tag_name = path[-1] 
            new_elem = ET.SubElement(new_record, tag_name)
            new_elem.text = found_elem.text
    return new_record
	


def remove_attributes(record: ET.Element) -> ET.Element:
	for elem in record.iter():
		elem.attrib.clear()
	return record

	


def main():
	system_prompt= """

---

### Exemple de structure attendue

**Input :**
```xml
<record><object_number>CARAFF00145</object_number><title>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</title><description.iconographical_description>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier, Diverses vignettes: Personnage de Cendrillon et sa marraine près d'un carrosse, bal, triomphe de Cendrillon avec danseuses, fée posant sa baguette sur deux jeunes filles: l'une en haillons, l'autre en robe de bal, sur un escalier, homme tenant une lanterne, au sol chaussure, groupe de gardes tenant des lanternes</description.iconographical_description><inscription.transliteration>" THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7h 1/2/ THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON/ 100/ DANSEUSES "</inscription.transliteration><inscription.transliteration>Sur tout le bas: " IMP. H. LAAS 16, R. PIERRE-LEVEE PARIS "</inscription.transliteration><inscription.transliteration>B.D.: " CARNAVALET "</inscription.transliteration><inscription.transliteration>H.D. timbre fiscal 20 centimes</inscription.transliteration><inscription.transliteration>H.D.: " [?] 1 OCTOBRE 1879 "</inscription.transliteration><temp.title_text>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</temp.title_text><themes_sujets.theme_commentaire>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Cendrillon, Acteur, Actrice, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier</themes_sujets.theme_commentaire><opac_word_index>Affiche</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>1879</opac_word_index><opac_word_index>Publicité, Théâtre, Paris, 10è arrondissement, Ballet, Littérature, Conte de fées, Théo Van-Ghell, Aline Duval (1824-1903), Pierre-Alfred Ravel (1811-1881), Alexandre, Gobin, Tissier, Diverses vignettes: Personnage de Cendrillon et sa marraine près d'un carrosse, bal, triomphe de Cendrillon avec danseuses, fée posant sa baguette sur deux jeunes filles: l'une en haillons, l'autre en robe de bal, sur un escalier, homme tenant une lanterne, au sol chaussure, groupe de gardes tenant des lanternes</opac_word_index><opac_word_index>Théâtre de la Porte Saint-Martin (Paris)</opac_word_index><opac_word_index>Affiche</opac_word_index><opac_word_index>Arts graphiques</opac_word_index><opac_word_index>Estampe</opac_word_index><opac_word_index>Publicité</opac_word_index><opac_word_index>Lithographie couleur sur papier</opac_word_index><opac_word_index>THEATRE DE LA PORTE ST. MARTIN/ TOUS LES SOIRS A 7 h 1/2/THEO/ VAN-GHELL/ ALINE DUVAL/ RAVEL/ ALEXANDRE, GOBIN/ TISSIER/ GRAND/ BALLET/ CENDRILLON</opac_word_index><opac_word_index>Papier</opac_word_index><opac_word_index>Lithographie</opac_word_index><opac_word_index>Anonyme</opac_word_index><opac_word_index>Imprimerie H. Laas</opac_word_index></record>
```

**Output**
```json
{
  "type_affiche": "Affiche de spectacle de ballet",
  "entites": [
    {
      "nom": "THEATRE DE LA PORTE ST. MARTIN",
      "categorie": "Lieu",
      "adresse": "Paris, 10è arrondissement",
      "explication": "Le lieu est identifié dans les balises <title>, <inscription.transliteration> et <description.iconographical_description>. Il s'agit du théâtre parisien accueillant la représentation promue par l'affiche."
    },
    {
      "nom": "CENDRILLON",
      "categorie": "Produit",
      "adresse": null,
      "explication": "Le titre de l'œuvre apparaît de manière centrale dans <title> et <inscription.transliteration>. Le champ <description.iconographical_description> montre de nombreuses vignettes illustrant directement des scènes de ce grand ballet."
    },
    {
      "nom": "THEO VAN-GHELL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionné comme interprète principal dans <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Sa présence en tête d'affiche démontre son importance centrale pour la promotion du spectacle."
    },
    {
      "nom": "ALINE DUVAL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionnée parmi les vedettes du spectacle dans <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Elle figure en haut de l'affiche pour attirer le public au théâtre."
    },
    {
      "nom": "RAVEL",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Mentionné sous forme de nom de scène ou patronyme dans <title>, <inscription.transliteration> et <description.iconographical_description>. Il fait partie des comédiens ou danseurs principaux mis en valeur pour cette production."
    },
    {
      "nom": "ALEXANDRE",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Nom de l'artiste présent dans les balises <title>, <inscription.transliteration> et <themes_sujets.theme_commentaire>. Il fait partie de la troupe d'acteurs clés mis en avant par la publicité."
    },
    {
      "nom": "GOBIN",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Nom présent dans les balises de titre (<title>) et de transcription (<inscription.transliteration>). Cet interprète contribue à la notoriété et à l'attrait de la distribution du ballet."
    },
    {
      "nom": "TISSIER",
      "categorie": "Personne",
      "adresse": null,
      "explication": "Dernier artiste nommé de la distribution principale dans <title> et <inscription.transliteration>. Il complète la liste des interprètes notables dont le nom sert d'argument publicitaire."
    }
  ]
}
```
"""

	xml = f" "
	tree = ET.parse(xml)
	root = tree.getroot()
	all_elements = root.findall('.//record')
	dossier_cible = " "
	os.makedirs(dossier_cible, exist_ok=True)

	loguru.logger.info(f"Extraction des commanditaires à partir du fichier XML {xml} vers le dossier {dossier_cible}")

	for i, record in enumerate(tqdm(all_elements, desc="Extraction des commanditaires", unit="affiche")):
		record = keep_only_relevant_xml_fields(record)
		print(ET.tostring(record, encoding="utf-8").decode("utf-8"))  # Affiche le XML transformé pour vérification

		id_element = record.find("object_number")
		id_affiche = id_element.text.strip() if id_element is not None else "inconnu"
		xml_str = ET.tostring(record, encoding="utf-8").decode("utf-8") 

		try:
			affiche = query_ollama(user_input=xml_str, model='gemma4:12b')
			output_file = f"{dossier_cible}/{id_affiche}.json"
			with open(output_file, "w", encoding="utf-8") as of:
				json.dump(affiche.model_dump(), of, indent=2, ensure_ascii=False)

			logger.info(f"{i}\t✅\t{id_affiche}\t")
		except Exception as e:
			# Si Pydantic crash ou Ollama coupe, on affiche l'erreur et on continue
			tqdm.write(f"⚠️ Erreur ignorée sur l'affiche {id_affiche}: {e}")
			logger.error(f"{i}\t❌\t{id_affiche}\t{e}")	

			

if __name__ == "__main__":
    main()
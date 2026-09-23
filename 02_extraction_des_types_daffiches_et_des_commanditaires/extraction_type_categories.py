import json
import os
from pathlib import Path
import csv

base = Path(" ")
output_csv = Path(" ")

def extract_type_category (datafile):
    types_affiche = set()
    categories = set()
    with open(datafile, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if data.get("type_affiche"):
            types_affiche.add(data["type_affiche"])
        for entity in data.get("entites", []):
            if entity.get("categorie"):
                categories.add(entity["categorie"])
                
    return types_affiche, categories

def main():
    all_types = set()
    all_categories = set()

    for datafile in base.glob("*.json"):
        types, categories = extract_type_category(datafile)
        all_types.update(types)
        all_categories.update(categories)

    data_to_write = []
    for t in sorted(all_types):
        data_to_write.append({"type": "type_affiche", "valeur": t})

    for c in sorted(all_categories):
        data_to_write.append({"type": "categorie_entite", "valeur": c})

    with open(output_csv, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["type", "valeur"])
        
        writer.writeheader()
        
        writer.writerows(data_to_write)

    print(f"Fichier CSV généré avec succès : {output_csv}")

if __name__ == "__main__":
    main()
# KÓD JE URČENÝ PRO STRÁNKU https://commons.wikimedia.org/wiki/Data:ECB_euro_foreign_exchange_reference_rates.tab
# KÓD SE SPUSTÍ VE WINDOWS A VLOŽÍ SE DO NĚJ SOUBOR STAŽENÝ Z WEBU https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml
# DO SCHRÁNKY JE NÁSLEDNĚ ZKOPÍROVÁN OBSAH STRÁNKY, KTERÝ JE NUTNO VLOŽIT NA COMMONS

import xml.etree.ElementTree as ET
import pyperclip
import json
from tkinter import Tk, filedialog

# Funkce pro zpracování XML souboru a vytvoření výstupu
def process_xml(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    namespace = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01', '': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}

    # Získání data a kurzů
    time_element = root.find(".//Cube[@time]", namespace)
    date = time_element.attrib['time'] if time_element is not None else None

    data = []
    for cube in root.findall(".//Cube[@currency]", namespace):
        currency = cube.attrib['currency']
        rate = cube.attrib['rate']
        data.append([currency, rate, date])

    # Vytvoření JSON výstupu
    output = {
        "license": "CC0-1.0",
        "description": {
            "de": "Euro-Referenzkurse",
            "en": "Euro foreign exchange reference rates"
        },
        "sources": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
        "schema": {
            "fields": [
                {"name": "currency", "type": "string"},
                {"name": "EUR", "type": "string"},
                {"name": "date", "type": "string"}
            ]
        },
        "data": data
    }

    # Převod do JSON a kopírování do schránky
    json_output = json.dumps(output, indent=4)
    pyperclip.copy(json_output)
    print("Data byla zkopírována do schránky.")
    return json_output

# Hlavní část programu
if __name__ == "__main__":
    # Otevření dialogu pro výběr souboru
    Tk().withdraw()  # Skryje hlavní okno tkinter
    file_path = filedialog.askopenfilename(
        title="Vyberte XML soubor",
        filetypes=[("XML soubory", "*.xml"), ("Všechny soubory", "*.*")]
    )
    
    if file_path:  # Zkontroluje, zda uživatel vybral soubor
        try:
            result = process_xml(file_path)
            print(result)  # Výpis JSON dat do konzole
        except Exception as e:
            print(f"Nastala chyba při zpracování souboru: {e}")
    else:
        print("Nebyl vybrán žádný soubor.")

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import sys

class WikiLinkerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wiki Linker - Překladač odkazů")
        self.root.geometry("950x650")

        # --- Styl ---
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10))
        style.configure("TLabel", font=("Helvetica", 10))

        # --- Horní panel s nastavením ---
        control_frame = ttk.LabelFrame(root, text="Nastavení", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)

        # Definice jazyků
        self.langs = ('cs', 'en', 'de', 'sk', 'fr', 'pl', 'es', 'it', 'ru', 'hu', 'pt', 'zh', 'wikidata')

        # Výběr zdrojového jazyka
        ttk.Label(control_frame, text="Zdrojový jazyk:").grid(row=0, column=0, padx=5, sticky="w")
        self.src_lang_var = tk.StringVar(value="cs")
        self.src_combo = ttk.Combobox(control_frame, textvariable=self.src_lang_var, width=10)
        self.src_combo['values'] = self.langs
        self.src_combo.grid(row=0, column=1, padx=5, sticky="w")

        # Výběr cílového jazyka
        ttk.Label(control_frame, text="Cílový jazyk:").grid(row=0, column=2, padx=5, sticky="w")
        self.target_lang_var = tk.StringVar(value="en")
        self.target_combo = ttk.Combobox(control_frame, textvariable=self.target_lang_var, width=10)
        self.target_combo['values'] = self.langs
        self.target_combo.grid(row=0, column=3, padx=5, sticky="w")
        
        # Checkbox pro prázdné řádky
        self.empty_if_missing_var = tk.BooleanVar(value=True)
        self.empty_check = ttk.Checkbutton(control_frame, text="Pokud neexistuje, nechat prázdné", variable=self.empty_if_missing_var)
        self.empty_check.grid(row=0, column=4, padx=15, sticky="w")

        # Tlačítko start
        self.start_btn = ttk.Button(control_frame, text="SPUSTIT PŘEKLAD", command=self.start_processing_thread)
        self.start_btn.grid(row=0, column=5, padx=20, sticky="e")

        # Progress bar
        self.progress = ttk.Progressbar(control_frame, orient="horizontal", length=200, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(10, 0))

        # --- Hlavní oblast s textovými poli ---
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Levý sloupec (Vstup)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ttk.Label(left_frame, text="Vstupní články / ID (1 řádek = 1 položka):").pack(anchor="w")
        self.input_text = scrolledtext.ScrolledText(left_frame, width=40, height=20)
        self.input_text.pack(fill="both", expand=True)
        # Vložíme demo data
        self.input_text.insert(tk.END, "Voda\nKarel Čapek\nPraha\nVelká Británie\nNeexistujiciClanek123\n")

        # Pravý sloupec (Výstup)
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ttk.Label(right_frame, text="Výsledek (kopírujte do Excelu):").pack(anchor="w")
        self.output_text = scrolledtext.ScrolledText(right_frame, width=40, height=20, bg="#f0f0f0")
        self.output_text.pack(fill="both", expand=True)

    def start_processing_thread(self):
        """Spustí zpracování v novém vlákně, aby nezamrzlo GUI."""
        src = self.src_lang_var.get().strip()
        tgt = self.target_lang_var.get().strip()
        raw_data = self.input_text.get("1.0", tk.END).strip()
        empty_on_missing = self.empty_if_missing_var.get()

        if not raw_data:
            messagebox.showwarning("Chyba", "Vložte prosím seznam článků.")
            return

        self.start_btn.config(state="disabled")
        self.output_text.delete("1.0", tk.END) # Vymazat staré výsledky
        self.progress['value'] = 0
        
        # Spuštění ve vlákně
        thread = threading.Thread(target=self.run_logic, args=(raw_data, src, tgt, empty_on_missing))
        thread.daemon = True
        thread.start()

    def run_logic(self, raw_input, src_lang, target_lang, empty_on_missing):
        """Logika stahování dat."""
        
        try:
            url = "https://www.wikidata.org/w/api.php"
            
            # Příprava seznamu
            clean_titles = [line.strip() for line in raw_input.split('\n')]
            # Ignorujeme pouze poslední prázdný řádek vzniklý kopírováním
            if clean_titles and not clean_titles[-1]: 
                clean_titles.pop() 

            results_map = {}
            chunk_size = 50
            total = len(clean_titles)
            
            # Nastavení maxima pro progress bar
            self.root.after(0, lambda: self.progress.configure(maximum=total))

            for i in range(0, total, chunk_size):
                chunk = clean_titles[i:i + chunk_size]
                # Filtrujeme prázdné řetězce pro API dotaz
                query_chunk = [t for t in chunk if t] 
                
                if not query_chunk:
                    continue

                titles_str = "|".join(query_chunk)
                
                # Rozlišení parametrů podle toho, zda je vstupem Wikidata ID nebo název článku
                params = {
                    "action": "wbgetentities",
                    "props": "sitelinks",
                    "format": "json",
                    "languages": target_lang
                }
                
                if src_lang.lower() == 'wikidata':
                    # Pokud je vstupem Wikidata ID (Q...), používáme parametr 'ids'
                    params["ids"] = titles_str
                else:
                    # Jinak hledáme podle názvu článku na konkrétní wiki
                    params["sites"] = f"{src_lang}wiki"
                    params["titles"] = titles_str
                
                headers = {'User-Agent': 'WikiLinkerGui/1.0'}
                
                try:
                    response = requests.get(url, params=params, headers=headers)
                    data = response.json()
                    
                    # Normalizace (pouze pro názvy článků, pro ID není relevantní)
                    normalized_map = {t: t for t in query_chunk}
                    if "normalized" in data:
                        for norm in data["normalized"]:
                            normalized_map[norm['to']] = norm['from']

                    entities = data.get("entities", {})
                    
                    for qid, entity in entities.items():
                        if qid == "-1": continue # ID neexistuje
                        if "missing" in entity: continue # Entita chybí
                        
                        original_input = ""
                        
                        if src_lang.lower() == 'wikidata':
                            # Pokud byl vstup QID, je klíčem přímo QID
                            original_input = qid
                        else:
                            # Pokud byl vstup název, musíme zjistit, ke kterému vstupu toto QID patří
                            source_sitelink = entity.get("sitelinks", {}).get(f"{src_lang}wiki", {})
                            canonical_title = source_sitelink.get("title")
                            if not canonical_title:
                                # Může se stát, že máme entitu, ale ta nemá sitelink na zdrojovou wiki (divné, ale možné při přesměrování)
                                # V takovém případě se pokusíme najít match v normalizaci, pokud to jde, jinak přeskočíme
                                continue
                            original_input = normalized_map.get(canonical_title, canonical_title)
                        
                        # Získání cílové hodnoty
                        target_value = ""
                        if target_lang.lower() == 'wikidata':
                            target_value = qid
                        else:
                            target_sitelink = entity.get("sitelinks", {}).get(f"{target_lang}wiki", {})
                            target_value = target_sitelink.get("title", "")
                        
                        if original_input:
                            results_map[original_input] = target_value
                            # Pro jistotu uložíme i pod canonical pro případné fallbacky
                            if src_lang.lower() != 'wikidata' and 'canonical_title' in locals():
                                results_map[canonical_title] = target_value

                except Exception as e:
                    self.append_log(f"Chyba API v bloku {i}: {str(e)}")

                # Aktualizace progress baru
                self.root.after(0, lambda step=chunk_size: self.progress.step(step))

            # === VYPISOVÁNÍ VÝSLEDKŮ ===
            final_output_string = ""
            for title in clean_titles:
                if not title: # Ponechat prázdné řádky ve vstupu jako prázdné ve výstupu
                    final_output_string += "\n"
                    continue

                val = ""
                found = False
                
                # 1. Přímá shoda
                if title in results_map:
                    val = results_map[title]
                    found = True
                else:
                    # 2. Case-insensitive fallback (pokud není vstup ID)
                    if src_lang.lower() != 'wikidata':
                        for k, v in results_map.items():
                            if k.lower() == title.lower():
                                val = v
                                found = True
                                break
                
                # Logika pro nenalezené výsledky
                if found and not val:
                    # Našli jsme entitu, ale nemá článek v cílovém jazyce
                    val = "" if empty_on_missing else "--- NENALEZENO ---"
                elif not found:
                    # Nenašli jsme entitu vůbec
                    val = "" if empty_on_missing else "--- NENALEZENO ---"
                
                final_output_string += val + "\n"

            # Vložení do GUI
            self.root.after(0, lambda: self.finish_processing(final_output_string))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Kritická chyba", str(e)))
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

    def finish_processing(self, result_string):
        """Zobrazí výsledky a znovu aktivuje tlačítko."""
        self.output_text.insert(tk.END, result_string)
        self.start_btn.config(state="normal")
        self.progress['value'] = 0
        messagebox.showinfo("Hotovo", "Překlad dokončen! Výsledky můžete zkopírovat.")

    def append_log(self, text):
        print(text) # Pro ladění do konzole

if __name__ == "__main__":
    root = tk.Tk()
    app = WikiLinkerApp(root)
    root.mainloop()

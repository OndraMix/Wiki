import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pywikibot
from pywikibot import textlib
import threading
import queue
import re
import math

class WikiChemApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wiki Chem Checker (CS vs EN/DE)")
        self.root.geometry("1300x850") # Mírně rozšířeno pro nový sloupec

        # Nastavení fronty pro komunikaci mezi vlákny
        self.msg_queue = queue.Queue()
        
        # Definice polí
        # Struktura: (Label, CS klíč, EN klíče, DE klíče, Typ ID/Text, Default SmartUnits?)
        self.fields_def = [
            ('CAS', 'číslo CAS', ['CASNo', 'CAS-No', 'CASNo1', 'CASNoOther', 'CASNo2'], ['CAS'], 'id', False),
            ('EINECS', 'číslo EINECS', ['EINECS', 'EC_number', 'EC-no'], ['EG-Nummer'], 'id', False),
            ('PubChem', 'PubChem', ['PubChem'], ['PubChem'], 'id', False),
            ('Molární hmotnost', 'molární hmotnost', ['MolarMass'], ['Molare Masse'], 'text', False),
            ('Rozpustnost', 'rozpustnost', ['Solubility'], ['Löslichkeit'], 'text', True), # Často g/l vs g/100ml
            ('Teplota tání', 'teplota tání', ['MeltingPt', 'MeltingPtC'], ['Schmelzpunkt'], 'text', True),
            ('Teplota varu', 'teplota varu', ['BoilingPt', 'BoilingPtC'], ['Siedepunkt'], 'text', True),
            ('Hustota', 'hustota', ['Density'], ['Dichte'], 'text', True), # Často g/cm3 vs kg/m3
        ]
        
        # Statistiky pro počítadla
        self.stats = {'error': 0, 'ok': 0, 'missing': 0}
        self.field_config = {} 

        # -- GUI Prvky --
        
        # 1. Konfigurace
        config_frame = ttk.LabelFrame(root, text="Nastavení kontroly a normalizace")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Hlavičky
        headers = ["Parametr", "Kontrolovat?", "Režim porovnání", "Tolerance +/-", "Smart Units?"]
        for col, text in enumerate(headers):
            ttk.Label(config_frame, text=text, font=('bold')).grid(row=0, column=col, padx=5, pady=2, sticky="w")

        # Generování řádků
        for idx, (label, _, _, _, ftype, def_smart) in enumerate(self.fields_def):
            row = idx + 1
            
            ttk.Label(config_frame, text=label).grid(row=row, column=0, padx=10, sticky="w")
            
            # Checkbox Enabled
            chk_var = tk.BooleanVar(value=True)
            ttk.Checkbutton(config_frame, variable=chk_var).grid(row=row, column=1, padx=10)
            
            # Mode Combobox
            mode_var = tk.StringVar()
            values = ["Standardní", "Agresivní (jen čísla)", "Super Agresivní (první číslo)"]
            if ftype == 'id':
                mode_var.set("Standardní") 
            else:
                mode_var.set("Super Agresivní (první číslo)")
            mode_cb = ttk.Combobox(config_frame, textvariable=mode_var, values=values, state="readonly", width=25)
            mode_cb.grid(row=row, column=2, padx=10, sticky="w")
            
            # Tolerance
            tol_var = tk.StringVar(value="0.0")
            if ftype == 'text': tol_var.set("0.5") # Default tolerance pro fyz. veličiny
            tol_entry = ttk.Entry(config_frame, textvariable=tol_var, width=8)
            tol_entry.grid(row=row, column=3, padx=10, sticky="w")

            # Smart Units Checkbox (Konverze jednotek)
            smart_var = tk.BooleanVar(value=def_smart)
            ttk.Checkbutton(config_frame, variable=smart_var).grid(row=row, column=4, padx=10)
            
            self.field_config[label] = {
                'enabled': chk_var,
                'mode': mode_var,
                'tolerance': tol_var,
                'smart': smart_var
            }

        # 2. Vstup
        input_frame = ttk.LabelFrame(root, text="Vstup: Seznam článků (jeden na řádek)")
        input_frame.pack(fill="x", padx=10, pady=5)
        self.input_text = scrolledtext.ScrolledText(input_frame, height=6)
        self.input_text.pack(fill="both", padx=5, pady=5)
        
        # 3. Ovládání
        ctrl_frame = ttk.Frame(root)
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        self.btn_start = ttk.Button(ctrl_frame, text="Spustit kontrolu", command=self.start_check_thread)
        self.btn_start.pack(side="left", padx=5)
        self.btn_stop = ttk.Button(ctrl_frame, text="Zastavit", command=self.stop_check, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(ctrl_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        self.status_lbl = ttk.Label(ctrl_frame, text="Připraveno")
        self.status_lbl.pack(side="right", padx=5)

        # 4. Výstup (Notebook)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tab_errors = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_errors, text="⚠️ Nesrovnalosti (0)")
        self.txt_errors = scrolledtext.ScrolledText(self.tab_errors)
        self.txt_errors.pack(fill="both", expand=True)
        
        self.tab_ok = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ok, text="✅ V pořádku (0)")
        self.txt_ok = scrolledtext.ScrolledText(self.tab_ok)
        self.txt_ok.pack(fill="both", expand=True)
        
        self.tab_missing = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_missing, text="❓ Chybějící (0)")
        self.txt_missing = scrolledtext.ScrolledText(self.tab_missing)
        self.txt_missing.pack(fill="both", expand=True)

        self.tab_log = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_log, text="Log")
        self.txt_log = scrolledtext.ScrolledText(self.tab_log, state='disabled', bg="#f0f0f0")
        self.txt_log.pack(fill="both", expand=True)

        self.is_running = False
        self.stop_event = threading.Event()
        self.root.after(100, self.process_queue)

    # --- GUI Metody ---
    def log(self, message):
        self.msg_queue.put(("log", message))

    def output_result(self, category, text):
        self.msg_queue.put(("result", (category, text)))

    def update_progress(self, value, text):
        self.msg_queue.put(("progress", (value, text)))

    def update_tabs_counter(self):
        self.notebook.tab(self.tab_errors, text=f"⚠️ Nesrovnalosti ({self.stats['error']})")
        self.notebook.tab(self.tab_ok, text=f"✅ V pořádku ({self.stats['ok']})")
        self.notebook.tab(self.tab_missing, text=f"❓ Chybějící ({self.stats['missing']})")

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.msg_queue.get_nowait()
                if msg_type == "log":
                    self.txt_log.config(state='normal')
                    self.txt_log.insert(tk.END, data + "\n")
                    self.txt_log.see(tk.END)
                    self.txt_log.config(state='disabled')
                elif msg_type == "progress":
                    val, txt = data
                    self.progress_var.set(val)
                    self.status_lbl.config(text=txt)
                elif msg_type == "result":
                    category, text = data
                    # Update text
                    target = self.txt_errors if category == "error" else (self.txt_ok if category == "ok" else self.txt_missing)
                    target.insert(tk.END, text + "\n")
                    if category == "error": target.insert(tk.END, "-"*40 + "\n")
                    
                    # Update counters
                    if category in self.stats:
                        self.stats[category] += 1
                        self.update_tabs_counter()
                        
                elif msg_type == "done":
                    self.is_running = False
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    messagebox.showinfo("Hotovo", f"Dokončeno.\nChyby: {self.stats['error']}\nOK: {self.stats['ok']}\nChybějící: {self.stats['missing']}")
                self.msg_queue.task_done()
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def start_check_thread(self):
        articles_raw = self.input_text.get("1.0", tk.END).strip()
        if not articles_raw:
            messagebox.showwarning("Chyba", "Zadejte seznam článků.")
            return
        
        article_list = [line.strip() for line in articles_raw.split('\n') if line.strip()]
        
        # Reset GUI
        self.stats = {'error': 0, 'ok': 0, 'missing': 0}
        self.update_tabs_counter()
        self.txt_errors.delete("1.0", tk.END)
        self.txt_ok.delete("1.0", tk.END)
        self.txt_missing.delete("1.0", tk.END)
        self.txt_log.config(state='normal')
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.config(state='disabled')

        # Config
        current_config = {}
        for label, conf in self.field_config.items():
            try:
                tol = float(conf['tolerance'].get().replace(',', '.'))
            except ValueError:
                tol = 0.0
            current_config[label] = {
                'enabled': conf['enabled'].get(),
                'mode': conf['mode'].get(),
                'tolerance': tol,
                'smart': conf['smart'].get()
            }

        self.is_running = True
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        threading.Thread(target=self.run_check, args=(article_list, current_config), daemon=True).start()

    def stop_check(self):
        if self.is_running:
            self.stop_event.set()
            self.log("!!! Požadováno zastavení...")

    # --- Logika Normalizace a Porovnání ---

    def clean_wiki_markup(self, text):
        if not text: return ""
        s = str(text)
        s = re.sub(r'<ref.*?>.*?</ref>', '', s, flags=re.DOTALL)
        s = re.sub(r'<ref[^>]*/>', '', s)
        s = re.sub(r'<!--.*?-->', '', s, flags=re.DOTALL)
        s = re.sub(r'\{\{val\|([0-9.,]+)(?:\|.*?)?\}\}', r'\1', s, flags=re.IGNORECASE)
        return s.strip()

    def extract_floats(self, text):
        s = self.clean_wiki_markup(text)
        s = s.replace(',', '.')
        matches = re.findall(r'-?\d+\.?\d*', s)
        nums = []
        for m in matches:
            try:
                val = float(m)
                nums.append(val)
            except ValueError: pass
        return nums

    def normalize_standard(self, text_str, is_id=False):
        s = self.clean_wiki_markup(text_str)
        if is_id:
            match = re.search(r'\b(\d{2,7}-\d{2,3}-\d)\b', s)
            if match: return match.group(1)
            return re.sub(r'[^\d-]', '', s).strip()
        else:
            s = s.replace('&nbsp;', ' ').replace('\xa0', ' ')
            return ' '.join(s.split())

    def check_smart_match(self, n1, n2, tolerance):
        """
        Pokusí se najít shodu pomocí převodu jednotek.
        Vrací True, pokud se podaří najít shodu.
        """
        # 1. Základní tolerance (už bylo zkontrolováno v main funkci, ale pro jistotu)
        if abs(n1 - n2) <= tolerance: return True
        
        # 2. Násobky 10 (Hustota: g/cm3 vs kg/m3, Rozpustnost: g/L vs g/100ml)
        # Kontrolujeme faktory 10, 100, 1000 oběma směry
        if n2 != 0:
            ratio = n1 / n2
            # Tolerance pro ratio - např. 1000 vs 999.9
            # Pokud je ratio blízko 10, 100, 1000 nebo 0.1, 0.01, 0.001
            valid_factors = [10, 100, 1000, 0.1, 0.01, 0.001]
            for f in valid_factors:
                # Zkontrolujeme, zda n1 je přibližně n2 * faktor (s tolerancí aplikovanou na výsledek)
                if abs(n1 - (n2 * f)) <= tolerance:
                    return True

        # 3. Teploty (Kelvin, Celsius, Fahrenheit)
        # Kelvin offset: 273.15
        # C = K - 273.15  NEBO  K = C + 273.15
        diff = abs(n1 - n2)
        if abs(diff - 273.15) <= 1.0: # Tolerance 1 stupeň pro konverzi K/C
            return True
            
        # Fahrenheit: F = C * 1.8 + 32
        # Zkusíme: n1 je C, n2 je F
        f_from_n1 = n1 * 1.8 + 32
        if abs(f_from_n1 - n2) <= max(tolerance, 1.0): return True
        
        # Zkusíme: n1 je F, n2 je C
        c_from_n1 = (n1 - 32) / 1.8
        if abs(c_from_n1 - n2) <= max(tolerance, 1.0): return True

        return False

    def check_values_match(self, val_cs, val_target, config_item, is_id_type):
        mode = config_item['mode']
        tolerance = config_item['tolerance']
        smart_units = config_item['smart']

        # Standardní (String)
        if mode == "Standardní":
            norm_cs = self.normalize_standard(val_cs, is_id=is_id_type)
            norm_target = self.normalize_standard(val_target, is_id=is_id_type)
            return (norm_cs == norm_target, norm_cs, norm_target)

        # Numerické režimy
        nums_cs = self.extract_floats(val_cs)
        nums_target = self.extract_floats(val_target)

        if not nums_cs or not nums_target:
            s_cs = " ".join(map(str, nums_cs))
            s_tg = " ".join(map(str, nums_target))
            return (s_cs == s_tg, s_cs, s_tg)

        # Super Agresivní (První číslo)
        if mode == "Super Agresivní (první číslo)":
            n1, n2 = nums_cs[0], nums_target[0]
            
            # Přímá shoda s tolerancí
            match = abs(n1 - n2) <= tolerance
            
            # Smart Units Check
            if not match and smart_units:
                match = self.check_smart_match(n1, n2, tolerance)
                
            return (match, str(n1), str(n2))

        # Agresivní (Všechna čísla)
        if mode == "Agresivní (jen čísla)":
            # Zde je smart unit složitější, aplikujeme ho jen pokud délky sedí
            # a aplikujeme ho prvek po prvku.
            if len(nums_cs) != len(nums_target):
                return (False, str(nums_cs), str(nums_target))
            
            matches = []
            for a, b in zip(nums_cs, nums_target):
                is_match = abs(a - b) <= tolerance
                if not is_match and smart_units:
                    is_match = self.check_smart_match(a, b, tolerance)
                matches.append(is_match)
            
            is_ok = all(matches)
            return (is_ok, str(nums_cs), str(nums_target))
        
        return (False, val_cs, val_target)

    # --- Worker Thread ---
    def get_infobox_params(self, page, templates_to_find):
        try:
            code = page.text
            templates = textlib.extract_templates_and_params(code)
            combined = {}
            found = False
            for t_name, params in templates:
                norm_name = t_name.replace('_', ' ').strip().lower()
                for target in templates_to_find:
                    if target.lower() in norm_name:
                        clean_p = {k.strip(): v.strip() for k, v in params.items()}
                        combined.update(clean_p)
                        found = True
            return combined if found else None
        except Exception as e:
            self.log(f"Chyba parsování {page.title()}: {e}")
            return None

    def run_check(self, article_list, config):
        try:
            self.log("Připojuji se k Wikipedii...")
            site_cs = pywikibot.Site('cs', 'wikipedia')
            site_en = pywikibot.Site('en', 'wikipedia')
            site_de = pywikibot.Site('de', 'wikipedia')
            
            target_templates = {
                'cs': ['Infobox - chemická sloučenina'],
                'en': ['Chembox', 'Infobox chemical', 'Chembox Identifiers', 'Chembox Properties', 'Chembox Hazards', 'Chembox Thermochemistry'],
                'de': ['Infobox Chemikalie']
            }

            total = len(article_list)
            
            for i, article_name in enumerate(article_list):
                if self.stop_event.is_set(): break
                self.update_progress((i / total) * 100, f"Zpracovávám: {article_name}")
                
                page_cs = pywikibot.Page(site_cs, article_name)
                if not page_cs.exists():
                    self.output_result("missing", f"{article_name}: Neexistuje na CS.")
                    continue
                if page_cs.isRedirectPage():
                    page_cs = page_cs.getRedirectTarget()

                params_cs = self.get_infobox_params(page_cs, target_templates['cs'])
                if not params_cs:
                    self.output_result("missing", f"{article_name}: Bez infoboxu.")
                    continue

                item = pywikibot.ItemPage.fromPage(page_cs)
                params_en, params_de = None, None
                en_title, de_title = "N/A", "N/A"

                try:
                    if item.exists():
                        sitelinks = item.sitelinks
                        if 'enwiki' in sitelinks:
                            en_title = sitelinks['enwiki'].title
                            params_en = self.get_infobox_params(pywikibot.Page(site_en, en_title), target_templates['en'])
                        if 'dewiki' in sitelinks:
                            de_title = sitelinks['dewiki'].title
                            params_de = self.get_infobox_params(pywikibot.Page(site_de, de_title), target_templates['de'])
                except Exception: pass

                if not params_en and not params_de:
                    self.output_result("missing", f"{article_name}: Chybí EN/DE infoboxy.")
                    continue

                discrepancies = []

                for label, key_cs, keys_en, keys_de, ftype, _ in self.fields_def:
                    conf = config.get(label)
                    if not conf or not conf['enabled']: continue

                    val_cs = params_cs.get(key_cs, "")
                    if not val_cs: continue

                    if params_en:
                        val_en = ""
                        for k in keys_en:
                            if k in params_en:
                                val_en = params_en[k]
                                break
                        if val_en:
                            match_ok, s_cs, s_en = self.check_values_match(val_cs, val_en, conf, ftype == 'id')
                            if not match_ok:
                                discrepancies.append(f"EN {label}: CS('{s_cs}') vs EN('{s_en}')")

                    if params_de:
                        val_de = ""
                        for k in keys_de:
                            if k in params_de:
                                val_de = params_de[k]
                                break
                        if val_de:
                            match_ok, s_cs, s_de = self.check_values_match(val_cs, val_de, conf, ftype == 'id')
                            if not match_ok:
                                discrepancies.append(f"DE {label}: CS('{s_cs}') vs DE('{s_de}')")

                header = f"Článek: [[{article_name}]] (EN: {en_title}, DE: {de_title})"
                if discrepancies:
                    self.output_result("error", header + "\n" + "\n".join(discrepancies))
                else:
                    self.output_result("ok", header + " -> OK")

            self.update_progress(100, "Hotovo")
            self.msg_queue.put(("done", None))

        except Exception as e:
            self.log(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = WikiChemApp(root)
    root.mainloop()

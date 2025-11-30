# DO VSTUPNÍHO OKNA VLOŽIT KÓD ČLÁNKU S CITAČNÍ ŠABLONOU S NEPOJMENOVANÝM PARMETREM A MĚL BY BÝT DETEKOVÁN A VYPSÁN V DOLNÍM OKNĚ
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
import mwparserfromhell # Knihovna pro parsování wikitextu

def find_unnamed_parameters(text, template_names):
    """
    Finds unnamed parameters in specified citation templates within the given text.

    Args:
        text (str): Article text (wikitext).
        template_names (list): List of citation template names to search for (without "Šablona:" prefix).

    Returns:
        dict: A dictionary where the key is the template name and the value is a list of unnamed parameters.
    """
    unnamed_params_found = {}

    # Use mwparserfromhell to parse the entire text.
    parsed_wikicode = mwparserfromhell.parse(text)

    # List of template names we are looking for, in lowercase for easy comparison.
    lower_template_names = [name.lower() for name in template_names]

    # Iterate through all templates found in the text.
    for template in parsed_wikicode.filter_templates():
        # Get the template name and convert it to lowercase for comparison.
        # Remove "Šablona:" prefix if it exists.
        template_name_raw = str(template.name).strip()
        if template_name_raw.lower().startswith("šablona:"):
            template_name_clean = template_name_raw[len("šablona:"):].strip()
        else:
            template_name_clean = template_name_raw

        # Check if the template is one of those we are monitoring.
        if template_name_clean.lower() in lower_template_names:
            current_template_unnamed_params = []
            
            # Iterate through all template parameters.
            for param in template.params:
                # Check if the parameter name is numeric (positional).
                # Unnamed (positional) parameters have names like '1', '2', '3', etc.
                param_name_str = str(param.name).strip()
                if param_name_str.isdigit():
                    # Get the value of the unnamed parameter.
                    param_value = str(param.value).strip()
                    if param_value: # Add only non-empty parameters
                        current_template_unnamed_params.append(param_value)
                
            if current_template_unnamed_params:
                # Normalize the template name for consistent output.
                normalized_template_name = next((name for name in template_names if name.lower() == template_name_clean.lower()), template_name_clean)
                unnamed_params_found.setdefault(normalized_template_name, []).extend(current_template_unnamed_params)
            
    return unnamed_params_found

def clear_input_text():
    """
    Clears the content of the input text area.
    """
    input_text_area.delete("1.0", tk.END)
    output_text_area.config(state=tk.NORMAL)
    output_text_area.delete("1.0", tk.END)
    output_text_area.config(state=tk.DISABLED)

def copy_instructions_to_clipboard():
    """
    Copies a specific instruction text to the clipboard.
    """
    instruction_text = "Oprava nebo smazání nepojmenovaného parametru citační šablony -> vyřazení z [[Kategorie:Údržba:Citační šablona s nepojmenovaným parametrem]]"
    root.clipboard_clear()
    root.clipboard_append(instruction_text)

def copy_important_to_clipboard():
    """
    Copies a specific instruction text to the clipboard.
    """
    instruction_text = "V URL: \"%7C\" místo | a <nowiki>|</nowiki>"
    root.clipboard_clear()
    root.clipboard_append(instruction_text)


def run_analysis():
    """
    Function that runs when the "Analyze" button is pressed.
    Retrieves text from the input field, performs analysis, and displays results.
    """
    article_text = input_text_area.get("1.0", tk.END) # Get all text from the input field
    
    # Clear the output field before new analysis
    output_text_area.config(state=tk.NORMAL) # Enable editing to insert text
    output_text_area.delete("1.0", tk.END)
    
    if not article_text.strip():
        messagebox.showwarning("Upozornění", "Prosím, vložte text článku k analýze.")
        output_text_area.config(state=tk.DISABLED) # Disable editing again
        return

    # List of monitored citation templates (without "Šablona:" prefix, script finds them even with lowercase)
    citation_templates = [
        "Citace monografie", "Citace elektronické monografie", "Citace kvalifikační práce", "Citace elektronického periodika", "Citace periodika", "Citace patentu",
        "Citace právního předpisu", "Citace sborníku", "Cite encyclopedia", "Nahlížení do KN", "Citace normy", 
        "Cite web", "Cite paper", "Cite news", "Cite journal", "Citace webu", "Citace Sbírky zákonů", "Citace soudního rozhodnutí", 
        "Cite press release", "Cite book", "Cite Q", "Citace webu", "SpringerEOM", "Citation", "Cit", "Citace arXiv", "Citace DzU", "Citace koránu", "Citace videohry", "Citace knihy", "Citace konference"
    ]

    try:
        unnamed_params = find_unnamed_parameters(article_text, citation_templates)
        
        if unnamed_params:
            output_text_area.insert(tk.END, "Nalezené nepojmenované parametry:\n")
            output_text_area.insert(tk.END, "-" * 50 + "\n")
            for template, params in unnamed_params.items():
                output_text_area.insert(tk.END, f"  Šablona: {template}\n")
                for param in params:
                    output_text_area.insert(tk.END, f"    - Nepojmenovaný parametr: '{param}'\n")
            output_text_area.insert(tk.END, "-" * 50 + "\n")
        else:
            output_text_area.insert(tk.END, "Nenalezeny žádné nepojmenované parametry v sledovaných šablonách v zadaném textu.\n")
            
    except Exception as e:
        messagebox.showerror("Chyba", f"Došlo k chybě při analýze: {e}")
    finally:
        output_text_area.config(state=tk.DISABLED) # Disable output field editing again

# --- Main GUI window setup ---
root = tk.Tk()
root.title("Analyzátor citačních šablon")
root.geometry("800x600") # Initial window size

# --- Input area for article text ---
input_frame = tk.LabelFrame(root, text="Vložte text článku zde:", padx=10, pady=10)
input_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

input_text_area = scrolledtext.ScrolledText(input_frame, wrap=tk.WORD, width=80, height=15, font=("Arial", 10))
input_text_area.pack(fill=tk.BOTH, expand=True)

# --- Button frame for organization ---
button_frame = tk.Frame(root)
button_frame.pack(pady=10)

# --- Analyze button ---
analyze_button = tk.Button(button_frame, text="Analyzovat text", command=run_analysis, font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", activebackground="#45a049")
analyze_button.pack(side=tk.LEFT, padx=5)

# --- Clear Input button ---
clear_button = tk.Button(button_frame, text="Vyčistit vstup", command=clear_input_text, font=("Arial", 12), bg="#f44336", fg="white", activebackground="#da190b")
clear_button.pack(side=tk.LEFT, padx=5)

# --- Copy Instructions button ---
copy_button = tk.Button(button_frame, text="Kopírovat shrnutí editace", command=copy_instructions_to_clipboard, font=("Arial", 12), bg="#2196F3", fg="white", activebackground="#0b7dda")
copy_button.pack(side=tk.LEFT, padx=5)

# --- Copy Instructions button ---
copy_button = tk.Button(button_frame, text="Kopírovat užitečné značky", command=copy_important_to_clipboard, font=("Arial", 12), bg="#2196F3", fg="white", activebackground="#0b7dda")
copy_button.pack(side=tk.LEFT, padx=5)

# --- Output area for results ---
output_frame = tk.LabelFrame(root, text="Výsledky analýzy:", padx=10, pady=10)
output_frame.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

output_text_area = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, width=80, height=15, font=("Courier New", 10), state=tk.DISABLED, bg="#f0f0f0")
output_text_area.pack(fill=tk.BOTH, expand=True)

# --- Start the main GUI loop ---
if __name__ == "__main__":
    root.mainloop()

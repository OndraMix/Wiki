import React, { useState } from 'react';
import { Upload, FileJson, CheckCircle, AlertCircle, Download, FileCode, Database } from 'lucide-react';

export default function WikiParser() {
  const [status, setStatus] = useState('idle'); // idle, processing, complete, error
  const [stats, setStats] = useState({ totalPages: 0, compoundsFound: 0 });
  const [resultData, setResultData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [previewItems, setPreviewItems] = useState([]);

  // Funkce pro extrakci textu šablony se správným párováním závorek {{ }}
  const extractTemplateContent = (fullText, templateName) => {
    // Normalizace názvu šablony pro vyhledávání (ignorujeme velikost písmen na začátku)
    const regex = new RegExp(`\\{\\{\\s*${templateName}`, 'i');
    const match = fullText.match(regex);
    
    if (!match) return null;

    const startIndex = match.index;
    let openBraces = 0;
    let endIndex = -1;
    
    // Procházíme text od začátku šablony a počítáme závorky
    for (let i = startIndex; i < fullText.length; i++) {
      if (fullText[i] === '{') openBraces++;
      if (fullText[i] === '}') openBraces--;

      if (openBraces === 0) {
        endIndex = i + 1;
        break;
      }
    }

    if (endIndex === -1) return null; // Šablona nebyla správně uzavřena

    // Vrátíme obsah šablony bez vnějších {{ }} a názvu šablony
    // Ořízneme '{{Infobox - chemická sloučenina' ze začátku a '}}' z konce
    const rawContent = fullText.substring(startIndex, endIndex);
    
    // Odstranění vnějších závorek pro parsování parametrů
    return rawContent.substring(2, rawContent.length - 2).replace(new RegExp(`^\\s*${templateName}\\s*`, 'i'), '');
  };

  // Funkce pro parsování parametrů z textu šablony
  const parseInfoboxParams = (rawInfobox) => {
    const params = {};
    let buffer = '';
    let currentKey = null;
    let insideLink = 0; // [[ ]]
    let insideTemplate = 0; // {{ }}
    
    // Jednoduchý stavový automat pro procházení znaků, aby se nerozbily vnořené struktury
    for (let i = 0; i < rawInfobox.length; i++) {
      const char = rawInfobox[i];
      const nextChar = rawInfobox[i + 1] || '';

      // Detekce vnořených struktur
      if (char === '{' && nextChar === '{') insideTemplate++;
      if (char === '}' && nextChar === '}') insideTemplate--;
      if (char === '[' && nextChar === '[') insideLink++;
      if (char === ']' && nextChar === ']') insideLink--;

      // Hledání oddělovače parametrů '|', ale pouze na nejvyšší úrovni
      if (char === '|' && insideTemplate <= 0 && insideLink <= 0) {
        if (currentKey) {
          // Uložení předchozího parametru
          params[currentKey.trim()] = buffer.trim();
        } else if (buffer.trim()) {
           // Případ pro první parametr bez klíče (vzácné u infoboxů, ale možné)
        }
        
        // Reset pro nový parametr - hledáme rovnítko
        currentKey = null;
        buffer = '';
        
        // Zkusíme najít klíč v následujícím řetězci
        let j = i + 1;
        let tempKey = '';
        let foundEquals = false;
        
        while (j < rawInfobox.length) {
          if (rawInfobox[j] === '=' && rawInfobox[j+1] !== '=') { // Ignorovat == nadpisy
             foundEquals = true;
             i = j; // Posuneme hlavní index
             break;
          }
          if (rawInfobox[j] === '|' || rawInfobox[j] === '}') break; // Narazili jsme na další param
          tempKey += rawInfobox[j];
          j++;
        }

        if (foundEquals) {
          currentKey = tempKey;
        } else {
           // Pokud není rovnítko, je to jen "flag" nebo divný formát, přidáme do bufferu
           buffer += char; 
        }

      } else {
        buffer += char;
      }
    }

    // Uložení posledního parametru
    if (currentKey) {
      params[currentKey.trim()] = buffer.trim();
    }

    return params;
  };

  const processFile = async (file) => {
    setStatus('processing');
    setErrorMessage('');
    setPreviewItems([]);

    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const text = e.target.result;
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(text, "text/xml");

        // Kontrola chyb v XML
        const parseError = xmlDoc.getElementsByTagName("parsererror");
        if (parseError.length > 0) {
          throw new Error("Chyba při parsování XML souboru.");
        }

        const pages = xmlDoc.getElementsByTagName('page');
        const extractedData = [];
        let count = 0;

        for (let i = 0; i < pages.length; i++) {
          const title = pages[i].getElementsByTagName('title')[0]?.textContent || "Neznámý název";
          const revisions = pages[i].getElementsByTagName('revision');
          
          if (revisions.length > 0) {
            // Získání textu poslední revize
            const textElement = revisions[revisions.length - 1].getElementsByTagName('text')[0];
            const pageContent = textElement?.textContent || "";

            // Hledáme specifický infobox
            const infoboxContent = extractTemplateContent(pageContent, 'Infobox - chemická sloučenina');

            if (infoboxContent) {
              const parsedParams = parseInfoboxParams(infoboxContent);
              
              extractedData.push({
                title: title,
                infobox: parsedParams
              });
              count++;
            }
          }
        }

        setStats({
          totalPages: pages.length,
          compoundsFound: count
        });

        setResultData(extractedData);
        setPreviewItems(extractedData.slice(0, 5)); // Náhled prvních 5
        setStatus('complete');

      } catch (err) {
        console.error(err);
        setErrorMessage(err.message || "Nastala neočekávaná chyba při zpracování.");
        setStatus('error');
      }
    };

    reader.onerror = () => {
      setErrorMessage("Chyba při čtení souboru.");
      setStatus('error');
    };

    reader.readAsText(file);
  };

  const handleDownload = () => {
    if (!resultData) return;

    const jsonString = JSON.stringify(resultData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = 'chemicke_slouceniny_data.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans text-slate-900">
      <div className="max-w-4xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-slate-800 flex items-center justify-center gap-3">
            <Database className="w-8 h-8 text-blue-600" />
            Wikipedia Infobox Extractor
          </h1>
          <p className="text-slate-600">
            Nástroj pro robotické čtení: Extrahuje parametry z <code>Infobox - chemická sloučenina</code> a maže zbytek článku.
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-lg p-10 hover:bg-slate-50 transition-colors">
            <input
              type="file"
              accept=".xml"
              onChange={(e) => e.target.files[0] && processFile(e.target.files[0])}
              className="hidden"
              id="file-upload"
              disabled={status === 'processing'}
            />
            <label
              htmlFor="file-upload"
              className={`flex flex-col items-center cursor-pointer ${status === 'processing' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {status === 'processing' ? (
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
              ) : (
                <Upload className="w-12 h-12 text-blue-500 mb-4" />
              )}
              <span className="text-lg font-medium text-slate-700">
                {status === 'processing' ? 'Zpracovávám XML...' : 'Klikněte pro nahrání XML exportu'}
              </span>
              <span className="text-sm text-slate-500 mt-2">Podporuje standardní MediaWiki XML exporty</span>
            </label>
          </div>

          {/* Error Message */}
          {status === 'error' && (
            <div className="mt-4 p-4 bg-red-50 text-red-700 rounded-lg flex items-center gap-3 border border-red-200">
              <AlertCircle className="w-5 h-5" />
              {errorMessage}
            </div>
          )}

          {/* Stats Bar */}
          {status === 'complete' && (
            <div className="mt-6 grid grid-cols-2 gap-4">
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100 flex items-center justify-between">
                <span className="text-blue-700 font-medium">Prohledáno stránek</span>
                <span className="text-2xl font-bold text-blue-800">{stats.totalPages}</span>
              </div>
              <div className="bg-green-50 p-4 rounded-lg border border-green-100 flex items-center justify-between">
                <span className="text-green-700 font-medium">Nalezeno sloučenin</span>
                <span className="text-2xl font-bold text-green-800">{stats.compoundsFound}</span>
              </div>
            </div>
          )}
        </div>

        {/* Results Preview & Download */}
        {status === 'complete' && resultData && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-semibold flex items-center gap-2">
                <FileCode className="w-5 h-5" />
                Náhled dat (prvních 5)
              </h2>
              <button
                onClick={handleDownload}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors shadow-sm"
              >
                <Download className="w-5 h-5" />
                Stáhnout kompletní JSON
              </button>
            </div>

            <div className="bg-slate-900 rounded-xl overflow-hidden shadow-lg border border-slate-800">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-slate-300">
                  <thead className="bg-slate-950 text-slate-100">
                    <tr>
                      <th className="p-4 font-semibold border-b border-slate-800 w-1/4">Název článku</th>
                      <th className="p-4 font-semibold border-b border-slate-800">Extrahovaná data (Infobox)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {previewItems.length > 0 ? (
                      previewItems.map((item, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/50">
                          <td className="p-4 align-top font-medium text-white">{item.title}</td>
                          <td className="p-4 font-mono text-xs text-green-400">
                            <pre className="whitespace-pre-wrap break-all">
                              {JSON.stringify(item.infobox, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan="2" className="p-8 text-center text-slate-500">
                          Nebyly nalezeny žádné stránky s infoboxem "chemická sloučenina".
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
            
            <div className="text-sm text-slate-500 text-center">
               Poznámka: Výsledný soubor je formátován jako pole JSON objektů, kde každý objekt obsahuje název a mapu parametrů. Všechny ostatní texty byly odstraněny.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

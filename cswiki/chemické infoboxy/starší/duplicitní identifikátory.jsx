import React, { useState, useMemo } from 'react';
import { Upload, AlertCircle, FileJson, CheckCircle, Search, X, Code, List, Copy, Check } from 'lucide-react';

const DuplicateFinder = () => {
  const [jsonData, setJsonData] = useState(null);
  const [fileName, setFileName] = useState("");
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('visual'); // 'visual' nebo 'wikitext'
  const [copied, setCopied] = useState(false);

  // Seznam parametrů, které budeme prohledávat
  const PARAMETERS_TO_CHECK = [
    "číslo CAS",
    "PubChem",
    "SMILES",
    "InChI",
    "číslo EINECS",
    "indexové číslo",
    "číslo EC",
    "ChEBI",
    "UN kód",
    "číslo RTECS"
  ];

  // Funkce pro načtení souboru
  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setFileName(file.name);
    setError(null);
    setJsonData(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = JSON.parse(e.target.result);
        if (!Array.isArray(content)) {
          throw new Error("Soubor musí obsahovat pole objektů (JSON Array).");
        }
        setJsonData(content);
      } catch (err) {
        setError("Chyba při čtení JSON souboru. Ujistěte se, že je formát platný.");
      }
    };
    reader.readAsText(file);
  };

  // Logika pro vyhledání duplicit
  const analysisResults = useMemo(() => {
    if (!jsonData) return null;

    const duplicates = {};
    let totalIssues = 0;

    // Inicializace struktury pro výsledky
    PARAMETERS_TO_CHECK.forEach(param => {
      duplicates[param] = [];
    });

    // Pomocná mapa pro sledování výskytů
    const tracker = {};

    jsonData.forEach((item) => {
      const title = item.title || "Neznámý název";
      const infobox = item.infobox;

      if (!infobox) return;

      PARAMETERS_TO_CHECK.forEach((param) => {
        if (infobox[param]) {
          let value = String(infobox[param]).trim();
          
          if (value === "" || value === "-") return;

          if (!tracker[param]) tracker[param] = {};
          if (!tracker[param][value]) tracker[param][value] = [];

          tracker[param][value].push(title);
        }
      });
    });

    // Filtrace
    PARAMETERS_TO_CHECK.forEach((param) => {
      if (tracker[param]) {
        Object.entries(tracker[param]).forEach(([value, titles]) => {
          if (titles.length > 1) {
            duplicates[param].push({ value, titles });
            totalIssues++;
          }
        });
      }
    });

    return { duplicates, totalIssues, totalItems: jsonData.length };

  }, [jsonData]);

  const resetData = () => {
    setJsonData(null);
    setFileName("");
    setError(null);
    setViewMode('visual');
  };

  const generateWikitext = () => {
    if (!analysisResults) return "";

    let wikitext = `= Duplicity v souboru ${fileName} =\n\n`;
    wikitext += `Analyzováno ${analysisResults.totalItems} záznamů. Nalezeno ${analysisResults.totalIssues} konfliktů.\n\n`;

    PARAMETERS_TO_CHECK.forEach(param => {
      const items = analysisResults.duplicates[param];
      if (items && items.length > 0) {
        wikitext += `== ${param} ==\n`;
        items.forEach(dup => {
          wikitext += `* ${dup.value}\n`;
          dup.titles.forEach(title => {
            wikitext += `** [[${title}]]\n`;
          });
        });
        wikitext += `\n`;
      }
    });

    if (analysisResults.totalIssues === 0) {
      wikitext += "Nebyly nalezeny žádné duplicity.\n";
    }

    return wikitext;
  };

  const copyToClipboard = () => {
    const text = generateWikitext();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans text-slate-900">
      <div className="max-w-5xl mx-auto space-y-6">
        
        {/* Hlavička */}
        <header className="flex items-center space-x-3 pb-4 border-b border-slate-200">
          <div className="p-3 bg-blue-600 rounded-lg text-white">
            <Search size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Detektor Duplicit Chemických Identifikátorů</h1>
            <p className="text-slate-500 text-sm">Analyzuje JSON soubor a hledá kolize v parametrech (CAS, PubChem, SMILES...)</p>
          </div>
        </header>

        {/* Sekce pro nahrání souboru */}
        {!jsonData && (
          <div className="bg-white p-10 rounded-xl shadow-sm border border-slate-200 text-center">
            <div className="flex flex-col items-center justify-center space-y-4">
              <div className="p-4 bg-blue-50 text-blue-600 rounded-full">
                <FileJson size={48} />
              </div>
              <h2 className="text-xl font-semibold">Nahrajte JSON soubor</h2>
              <p className="text-slate-500 max-w-md mx-auto">
                Vyberte soubor <code>chemicke_slouceniny_data.json</code> z vašeho počítače. Aplikace jej zpracuje lokálně v prohlížeči.
              </p>
              
              <label className="cursor-pointer inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors">
                <Upload className="w-5 h-5 mr-2" />
                Vybrat soubor
                <input type="file" accept=".json" onChange={handleFileUpload} className="hidden" />
              </label>

              {error && (
                <div className="flex items-center text-red-600 bg-red-50 px-4 py-2 rounded-lg mt-4">
                  <AlertCircle size={18} className="mr-2" />
                  {error}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Výsledky analýzy */}
        {jsonData && analysisResults && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Souhrnná karta */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 flex flex-col md:flex-row md:justify-between md:items-center gap-4">
              <div>
                <h3 className="text-lg font-semibold flex items-center">
                  <FileJson className="w-5 h-5 mr-2 text-slate-400" />
                  {fileName}
                </h3>
                <div className="text-sm text-slate-500 mt-1">
                  Analyzováno <span className="font-mono font-medium text-slate-700">{analysisResults.totalItems}</span> záznamů
                </div>
              </div>
              
              <div className="flex items-center space-x-4">
                <div className="flex bg-slate-100 p-1 rounded-lg">
                  <button
                    onClick={() => setViewMode('visual')}
                    className={`flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      viewMode === 'visual' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <List size={16} className="mr-2" />
                    Přehled
                  </button>
                  <button
                    onClick={() => setViewMode('wikitext')}
                    className={`flex items-center px-3 py-1.5 text-sm font-medium rounded-md transition-all ${
                      viewMode === 'wikitext' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    <Code size={16} className="mr-2" />
                    Wikikód
                  </button>
                </div>

                <div className="h-8 w-px bg-slate-200 mx-2 hidden md:block"></div>

                <div className="text-right hidden md:block">
                  <div className="text-sm text-slate-500">Duplicity</div>
                  <div className={`text-xl font-bold ${analysisResults.totalIssues > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                    {analysisResults.totalIssues}
                  </div>
                </div>

                <button 
                  onClick={resetData}
                  className="p-2 hover:bg-slate-100 rounded-full text-slate-400 hover:text-slate-600 transition-colors"
                  title="Zavřít a nahrát jiný soubor"
                >
                  <X size={24} />
                </button>
              </div>
            </div>

            {/* Obsah - Visual Mode */}
            {viewMode === 'visual' && (
              <>
                {analysisResults.totalIssues === 0 ? (
                  <div className="bg-green-50 border border-green-100 p-8 rounded-xl text-center text-green-800">
                    <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-600" />
                    <h3 className="text-xl font-bold">Vše v pořádku</h3>
                    <p>Nebyly nalezeny žádné duplicity ve sledovaných parametrech.</p>
                  </div>
                ) : (
                  <div className="grid gap-6">
                    {PARAMETERS_TO_CHECK.map(param => {
                      const items = analysisResults.duplicates[param];
                      if (!items || items.length === 0) return null;

                      return (
                        <div key={param} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                          <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex justify-between items-center">
                            <h4 className="font-bold text-slate-700">{param}</h4>
                            <span className="bg-orange-100 text-orange-700 text-xs px-2 py-1 rounded-full font-bold">
                              {items.length} {items.length === 1 ? 'konflikt' : (items.length < 5 ? 'konflikty' : 'konfliktů')}
                            </span>
                          </div>
                          <div className="divide-y divide-slate-100">
                            {items.map((dup, idx) => (
                              <div key={idx} className="p-6 hover:bg-slate-50 transition-colors">
                                <div className="flex flex-col md:flex-row md:items-start gap-4">
                                  <div className="md:w-1/4">
                                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">Duplicitní hodnota</span>
                                    <code className="bg-red-50 text-red-700 px-2 py-1 rounded border border-red-100 font-mono text-sm break-all block w-fit">
                                      {dup.value}
                                    </code>
                                  </div>
                                  <div className="md:w-3/4">
                                    <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">Nalezeno v článcích ({dup.titles.length})</span>
                                    <ul className="space-y-1">
                                      {dup.titles.map((title, tIdx) => (
                                        <li key={tIdx} className="flex items-center text-slate-700 text-sm">
                                          <span className="w-1.5 h-1.5 bg-slate-300 rounded-full mr-2"></span>
                                          {title}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </>
            )}

            {/* Obsah - Wikitext Mode */}
            {viewMode === 'wikitext' && (
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-[600px]">
                <div className="bg-slate-50 px-6 py-3 border-b border-slate-200 flex justify-between items-center">
                  <h4 className="font-bold text-slate-700 flex items-center">
                    <Code className="w-4 h-4 mr-2" />
                    Výstup pro Wikipedii
                  </h4>
                  <button
                    onClick={copyToClipboard}
                    className="flex items-center px-3 py-1.5 bg-white border border-slate-300 text-slate-700 text-sm font-medium rounded hover:bg-slate-50 transition-colors"
                  >
                    {copied ? <Check size={16} className="mr-2 text-green-600" /> : <Copy size={16} className="mr-2" />}
                    {copied ? "Zkopírováno!" : "Zkopírovat kód"}
                  </button>
                </div>
                <div className="flex-1 p-0">
                  <textarea 
                    className="w-full h-full p-4 font-mono text-sm text-slate-800 resize-none focus:outline-none"
                    value={generateWikitext()}
                    readOnly
                  />
                </div>
              </div>
            )}

          </div>
        )}
      </div>
    </div>
  );
};

export default DuplicateFinder;

import React, { useState, useCallback } from 'react';
import { Upload, AlertCircle, CheckCircle, FileText, Copy, AlertTriangle } from 'lucide-react';

const CasValidatorApp = () => {
  const [jsonContent, setJsonContent] = useState(null);
  const [issues, setIssues] = useState([]);
  const [wikiText, setWikiText] = useState('');
  const [error, setError] = useState('');
  const [fileName, setFileName] = useState('');

  // Funkce pro analýzu CAS čísla
  const analyzeCas = (cas, title) => {
    if (!cas) return null;
    
    // Převedeme na string, kdyby to náhodou bylo číslo
    const casStr = String(cas).trim();

    // Regex: Povolujeme pouze číslice 0-9 a základní spojovník -
    // Pokud obsahuje cokoliv jiného, je to "chyba" dle zadání
    const isValid = /^[0-9-]+$/.test(casStr);

    if (!isValid) {
      let problemDescription = [];
      
      // Detekce specifických problémů pro lepší report
      if (/[a-zA-Z]/.test(casStr)) problemDescription.push("obsahuje písmena");
      if (/\s/.test(casStr)) problemDescription.push("obsahuje mezery");
      if (/–/.test(casStr)) problemDescription.push("obsahuje půlčtvercovou pomlčku (–)");
      if (/—/.test(casStr)) problemDescription.push("obsahuje čtvercovou pomlčku (—)");
      if (/−/.test(casStr)) problemDescription.push("obsahuje typografické mínus (−)");
      if (/,/.test(casStr)) problemDescription.push("obsahuje čárky");
      if (problemDescription.length === 0) problemDescription.push("obsahuje nepovolené znaky");

      return {
        title,
        cas: casStr,
        reason: problemDescription.join(", ")
      };
    }
    return null;
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setFileName(file.name);
    setError('');
    setIssues([]);
    setWikiText('');

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const content = JSON.parse(e.target.result);
        setJsonContent(content);
        processData(content);
      } catch (err) {
        setError('Chyba při čtení JSON souboru. Zkontroluj, zda je formát validní.');
        console.error(err);
      }
    };
    reader.readAsText(file);
  };

  const processData = (data) => {
    if (!Array.isArray(data)) {
      setError('Očekáván formát JSON pole (Array of Objects).');
      return;
    }

    const foundIssues = [];

    data.forEach(item => {
      // Bezpečný přístup k datům, i když infobox chybí
      const title = item.title || "Neznámý článek";
      const infobox = item.infobox || {};
      const cas = infobox['číslo CAS'];

      if (cas) {
        // Někdy může být CAS pole (pokud je více hodnot), ošetříme to
        if (Array.isArray(cas)) {
          cas.forEach(c => {
            const result = analyzeCas(c, title);
            if (result) foundIssues.push(result);
          });
        } else {
          const result = analyzeCas(cas, title);
          if (result) foundIssues.push(result);
        }
      }
    });

    setIssues(foundIssues);
    generateWikiText(foundIssues);
  };

  const generateWikiText = (issuesList) => {
    if (issuesList.length === 0) {
      setWikiText("Nebyly nalezeny žádné chyby.");
      return;
    }

    // ZMĚNA: Generování seznamu místo tabulky
    const listItems = issuesList.map(issue => {
      return `* [[${issue.title}]] – CAS: <nowiki>${issue.cas}</nowiki> (${issue.reason})`;
    }).join('\n');

    setWikiText(listItems);
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(wikiText).then(() => {
      alert("Wikitext zkopírován do schránky!");
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 font-sans">
      <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-lg overflow-hidden">
        
        {/* Header */}
        <div className="bg-blue-600 p-6 text-white">
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <AlertCircle className="w-8 h-8" />
            Validátor CAS čísel pro Wikipedii
          </h1>
          <p className="mt-2 text-blue-100 opacity-90">
            Nahrajte JSON export a nástroj najde nevalidní znaky v položce "číslo CAS".
          </p>
        </div>

        <div className="p-6 space-y-6">
          
          {/* File Upload */}
          <div className="border-2 border-dashed border-slate-300 rounded-lg p-8 text-center hover:bg-slate-50 transition-colors relative">
            <input 
              type="file" 
              accept=".json"
              onChange={handleFileUpload}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
            <div className="flex flex-col items-center gap-3 text-slate-500">
              <Upload className="w-12 h-12 text-blue-500" />
              <span className="text-lg font-medium text-slate-700">
                {fileName ? `Vybráno: ${fileName}` : "Klikněte pro nahrání souboru JSON"}
              </span>
              <span className="text-sm">Analýza proběhne automaticky po nahrání</span>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 text-red-700 p-4 rounded-lg flex items-center gap-3 border border-red-200">
              <AlertTriangle />
              {error}
            </div>
          )}

          {/* Results Summary */}
          {fileName && !error && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white border border-slate-200 p-4 rounded-lg shadow-sm flex flex-col justify-center items-center">
                <span className="text-sm text-slate-500 uppercase tracking-wide font-semibold">Zpracováno článků</span>
                <span className="text-3xl font-bold text-slate-800">
                   {jsonContent ? jsonContent.length : 0}
                </span>
              </div>
              <div className={`border p-4 rounded-lg shadow-sm flex flex-col justify-center items-center ${issues.length > 0 ? 'bg-orange-50 border-orange-200' : 'bg-green-50 border-green-200'}`}>
                <span className="text-sm text-slate-500 uppercase tracking-wide font-semibold">Nalezené problémy</span>
                <span className={`text-3xl font-bold ${issues.length > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                  {issues.length}
                </span>
              </div>
            </div>
          )}

          {/* Wikitext Output */}
          {issues.length > 0 && (
            <div className="space-y-3">
              <div className="flex justify-between items-end">
                <h2 className="text-lg font-semibold text-slate-800 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-blue-600" />
                  Výstupní Wikitext
                </h2>
                <button 
                  onClick={copyToClipboard}
                  className="bg-slate-800 hover:bg-slate-700 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center gap-2 transition-colors"
                >
                  <Copy className="w-4 h-4" />
                  Zkopírovat kód
                </button>
              </div>
              
              <textarea 
                readOnly
                value={wikiText}
                className="w-full h-64 font-mono text-sm bg-slate-800 text-green-400 p-4 rounded-lg border border-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              
              <div className="bg-blue-50 text-blue-800 text-sm p-4 rounded-lg border border-blue-100">
                <strong>Tip:</strong> Tento kód zkopírujte a vložte do vašeho pískoviště na Wikipedii.
              </div>
            </div>
          )}

          {/* Success State */}
          {fileName && !error && issues.length === 0 && (
            <div className="bg-green-50 p-8 rounded-lg text-center text-green-800 border border-green-200">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-green-500" />
              <h3 className="text-xl font-bold mb-2">Vše vypadá v pořádku!</h3>
              <p>Všechna nalezená CAS čísla obsahují pouze číslice a spojovníky.</p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

export default CasValidatorApp;

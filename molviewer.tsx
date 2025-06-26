import React, { useEffect, useRef, useState } from 'react';

// Add type declarations for 3Dmol.js and jQuery on the window object
declare global {
  interface Window {
    $: any;
    $3Dmol: any;
  }
}

const Mol3DViewer = ({ 
  pdbText = '', 
  sdfOptions = [], // Array of {id, name, sdfText, confidence}
  selectedSdfId = null,
  width = '100%', 
  height = '600px',
  onSdfChange = (newSelectedId: any) => {}
}) => {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);

  const selectedSdf = sdfOptions.find(opt => opt.id === selectedSdfId);

  useEffect(() => {
    let jqueryScript = null;
    let threeDmolScript = null;

    const loadScripts = async () => {
      try {
        if (window.$ && window.$3Dmol) {
          setIsLoaded(true);
          return;
        }

        if (!window.$) {
          jqueryScript = document.createElement('script');
          jqueryScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.6.0/jquery.min.js';
          jqueryScript.crossOrigin = 'anonymous';
          
          await new Promise((resolve, reject) => {
            jqueryScript.onload = resolve;
            jqueryScript.onerror = reject;
            document.head.appendChild(jqueryScript);
          });
        }

        if (!window.$3Dmol) {
          threeDmolScript = document.createElement('script');
          threeDmolScript.src = 'https://3Dmol.csb.pitt.edu/build/3Dmol-min.js';
          
          await new Promise((resolve, reject) => {
            threeDmolScript.onload = resolve;
            threeDmolScript.onerror = reject;
            document.head.appendChild(threeDmolScript);
          });
        }

        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (window.$ && window.$3Dmol) {
          setIsLoaded(true);
        } else {
          throw new Error('Scripts loaded but libraries not available');
        }
      } catch (err) {
        console.error('Script loading error:', err);
        setError('Failed to load required libraries');
      }
    };

    loadScripts();
  }, []);

  useEffect(() => {
    if (!isLoaded || !containerRef.current) return;

    const initViewer = () => {
      try {
        const container = containerRef.current;
        container.innerHTML = '';

        const element = window.$(container);
        const config = { backgroundColor: "white" };
        const viewer = window.$3Dmol.createViewer(element, config);
        viewerRef.current = viewer;

        let modelCount = 0;

        // Add PDB model (protein structure)
        if (pdbText && pdbText.trim()) {
          viewer.addModel(pdbText, "pdb");
          const pdbModel = viewer.getModel(modelCount);
          pdbModel.setStyle({}, {cartoon: {color: "spectrum", opacity: 0.8}});
          modelCount++;
        }

        // Add selected SDF model (ligand)
        if (selectedSdf && selectedSdf.sdfText && selectedSdf.sdfText.trim()) {
          viewer.addModel(selectedSdf.sdfText, "sdf");
          const sdfModel = viewer.getModel(modelCount);
          sdfModel.setStyle({}, {stick: {color: "red", radius: 0.2, opacity: 0.9}});
          modelCount++;
        }

        if (modelCount > 0) {
          viewer.zoomTo();
          viewer.render();
        }

        setError(null);
      } catch (err) {
        console.error('Viewer initialization error:', err);
        setError(`Viewer error: ${err.message}`);
      }
    };

    const timer = setTimeout(initViewer, 50);
    
    return () => {
      clearTimeout(timer);
      if (viewerRef.current) {
        try {
          viewerRef.current.clear();
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    };
  }, [isLoaded, pdbText, selectedSdf]);

  const handleSdfSelection = (e) => {
    const newSelectedId = e.target.value || null;
    onSdfChange(newSelectedId);
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-100';
    if (confidence >= 0.6) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getConfidenceLabel = (confidence) => {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.6) return 'Medium';
    return 'Low';
  };

  if (error) {
    return (
      <div className="space-y-4">
        {sdfOptions.length > 0 && (
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Select Ligand:</label>
            <select 
              value={selectedSdfId || ''}
              onChange={handleSdfSelection}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled
            >
              <option value="">None selected</option>
              {sdfOptions.map(option => (
                <option key={option.id} value={option.id}>
                  {option.name} (Score: {option.confidence.toFixed(3)})
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex items-center justify-center bg-red-50 border border-red-300 rounded-lg p-4" style={{ width, height }}>
          <div className="text-red-700 text-center">
            <div className="font-semibold mb-2">❌ Molecular Viewer Error</div>
            <div className="text-sm">{error}</div>
            <button 
              onClick={() => window.location.reload()} 
              className="mt-2 px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="space-y-4">
        {sdfOptions.length > 0 && (
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Select Ligand:</label>
            <select 
              disabled
              className="px-3 py-2 border border-gray-300 rounded-lg bg-gray-100 text-gray-500"
            >
              <option>Loading...</option>
            </select>
          </div>
        )}
        <div className="flex items-center justify-center bg-blue-50 border border-blue-300 rounded-lg" style={{ width, height }}>
          <div className="text-blue-700 text-center">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent mb-3"></div>
            <div className="font-medium">Loading 3Dmol.js...</div>
            <div className="text-sm mt-1">Please wait while we load the molecular viewer</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Ligand Selection Dropdown */}
      {sdfOptions.length > 0 && (
        <div className="bg-gray-50 p-4 rounded-lg border">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-2">
              <label className="text-sm font-semibold text-gray-700">Select Ligand:</label>
              <select 
                value={selectedSdfId || ''}
                onChange={handleSdfSelection}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white min-w-48"
              >
                <option value="">-- No ligand selected --</option>
                {sdfOptions.map(option => (
                  <option key={option.id} value={option.id}>
                    {option.name} (Score: {option.confidence.toFixed(3)})
                  </option>
                ))}
              </select>
            </div>
            
            {selectedSdf && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-600">Confidence:</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getConfidenceColor(selectedSdf.confidence)}`}>
                  {getConfidenceLabel(selectedSdf.confidence)} ({selectedSdf.confidence.toFixed(3)})
                </span>
              </div>
            )}
          </div>
          
          {selectedSdf && (
            <div className="mt-2 text-sm text-gray-600">
              <strong>Selected:</strong> {selectedSdf.name} - 
              <span className="ml-1">
                {selectedSdf.confidence >= 0.8 ? 'Highly confident binding prediction' :
                 selectedSdf.confidence >= 0.6 ? 'Moderate confidence binding prediction' :
                 'Low confidence binding prediction'}
              </span>
            </div>
          )}
        </div>
      )}

      {/* 3D Viewer */}
      <div className="border border-gray-300 rounded-lg overflow-hidden shadow-sm">
        <div 
          ref={containerRef}
          style={{ width, height, position: 'relative' }}
          className="bg-white"
        />
        <div className="bg-gray-50 px-3 py-2 text-xs text-gray-600 border-t">
          <div className="flex justify-between items-center">
            <div>
              <div className="font-medium">3Dmol.js: Molecular visualization with WebGL</div>
              <div className="mt-1">
                <strong>Citation:</strong> Rego, N. & Koes, D. 3Dmol.js: molecular visualization with WebGL. 
                <em> Bioinformatics</em> <strong>31</strong>, 1322–1324 (2015).
              </div>
            </div>
            <div className="text-right">
              {pdbText && <div className="text-blue-600">🧬 Protein: Cartoon</div>}
              {selectedSdf && <div className="text-red-600">⚛️ Ligand: Sticks</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Demo component with multiple SDF options
const App = () => {
  // Sample PDB data
  const samplePDB = `HEADER    SAMPLE PROTEIN
ATOM      1  N   ALA A   1      20.154  16.000  10.000  1.00 20.00           N  
ATOM      2  CA  ALA A   1      20.154  17.500  10.000  1.00 20.00           C  
ATOM      3  C   ALA A   1      18.818  18.200  10.000  1.00 20.00           C  
ATOM      4  O   ALA A   1      17.728  17.600  10.000  1.00 20.00           O  
ATOM      5  CB  ALA A   1      21.400  18.200   9.500  1.00 20.00           C  
ATOM      6  N   GLY A   2      18.818  19.500  10.000  1.00 20.00           N  
ATOM      7  CA  GLY A   2      17.600  20.300  10.000  1.00 20.00           C  
ATOM      8  C   GLY A   2      17.600  21.800  10.000  1.00 20.00           C  
ATOM      9  O   GLY A   2      18.700  22.400  10.000  1.00 20.00           O  
CONECT    1    2
CONECT    2    1    3    5
CONECT    3    2    4    6
CONECT    4    3
CONECT    5    2
CONECT    6    3    7
CONECT    7    6    8
CONECT    8    7    9
CONECT    9    8
END`;

  // Sample SDF options with confidence scores
  const sampleSdfOptions = [
    {
      id: 'ligand1',
      name: 'Aspirin',
      confidence: 0.892,
      sdfText: `
  Aspirin
  
  
 13 13  0  0  0  0  0  0  0  0999 V2000
    2.8660    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.1516    0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4371    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.4371   -0.8250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.1516   -1.2375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.8660   -0.8250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.7226    0.4125    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.7226    1.2375    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    3.5805   -1.2375    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    4.2949   -0.8250    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    5.0094   -1.2375    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    4.2949   -0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  2  3  1  0  0  0  0
  3  4  2  0  0  0  0
  4  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  1  1  0  0  0  0
  3  7  1  0  0  0  0
  7  8  1  0  0  0  0
  7  9  2  0  0  0  0
  6 10  1  0  0  0  0
 10 11  1  0  0  0  0
 11 12  1  0  0  0  0
 11 13  2  0  0  0  0
M  END
$$$$`
    },
    {
      id: 'ligand2',
      name: 'Caffeine',
      confidence: 0.756,
      sdfText: `
  Caffeine
  
  
 14 15  0  0  0  0  0  0  0  0999 V2000
    1.0000    0.0000    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    0.5000    0.8660    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.5000    0.8660    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
   -1.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.5000   -0.8660    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.5000   -0.8660    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.5000   -1.6920    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    0.5000   -1.6920    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.0000   -0.8660    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    2.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.0000   -1.7320    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    1.0000    1.7320    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -1.0000    1.7320    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  2  3  1  0  0  0  0
  3  4  1  0  0  0  0
  4  5  1  0  0  0  0
  5  6  1  0  0  0  0
  6  1  1  0  0  0  0
  5  7  1  0  0  0  0
  7  8  1  0  0  0  0
  8  9  1  0  0  0  0
  9  6  1  0  0  0  0
  1 10  1  0  0  0  0
  9 11  1  0  0  0  0
  4 12  2  0  0  0  0
  2 13  2  0  0  0  0
  3 14  1  0  0  0  0
M  END
$$$$`
    },
    {
      id: 'ligand3',
      name: 'Benzene',
      confidence: 0.432,
      sdfText: `
  Benzene
  
  
  6  6  0  0  0  0  0  0  0  0999 V2000
    1.2000    0.6928    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.2000   -0.6928    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000   -1.3856    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.2000   -0.6928    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.2000    0.6928    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    0.0000    1.3856    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0  0  0  0
  2  3  1  0  0  0  0
  3  4  2  0  0  0  0
  4  5  1  0  0  0  0
  5  6  2  0  0  0  0
  6  1  1  0  0  0  0
M  END
$$$$`
    }
  ];

  const [pdbData, setPdbData] = useState('');
  const [sdfOptions, setSdfOptions] = useState([]);
  const [selectedSdfId, setSelectedSdfId] = useState(null);

  const loadSampleData = () => {
    setPdbData(samplePDB);
    setSdfOptions(sampleSdfOptions);
    setSelectedSdfId(sampleSdfOptions[0].id); // Auto-select first option
  };

  const clearAll = () => {
    setPdbData('');
    setSdfOptions([]);
    setSelectedSdfId(null);
  };

  const addSdfOption = () => {
    const newId = `custom_${Date.now()}`;
    const newOption = {
      id: newId,
      name: `Custom Ligand ${sdfOptions.length + 1}`,
      confidence: Math.random() * 0.5 + 0.5, // Random between 0.5-1.0
      sdfText: ''
    };
    setSdfOptions([...sdfOptions, newOption]);
  };

  const updateSdfOption = (id, field, value) => {
    setSdfOptions(options => 
      options.map(opt => 
        opt.id === id ? { ...opt, [field]: value } : opt
      )
    );
  };

  const removeSdfOption = (id) => {
    setSdfOptions(options => options.filter(opt => opt.id !== id));
    if (selectedSdfId === id) {
      setSelectedSdfId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Multi-Ligand Molecular Viewer</h1>
        <p className="text-gray-600">Visualize protein structures with multiple ligand options and confidence scores</p>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Panel */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <h3 className="font-semibold text-gray-900 mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button 
                onClick={loadSampleData}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200 font-medium"
              >
                🧬 Load Sample Data
              </button>
              <button 
                onClick={clearAll}
                className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors duration-200 font-medium"
              >
                🗑️ Clear All
              </button>
            </div>
          </div>

          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <h3 className="font-semibold text-gray-900 mb-3">Protein Structure (PDB)</h3>
            <textarea
              value={pdbData}
              onChange={(e) => setPdbData(e.target.value)}
              className="w-full h-32 p-3 border border-gray-300 rounded-lg text-sm font-mono resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Paste PDB data here..."
            />
          </div>

          <div className="bg-white p-4 rounded-lg border shadow-sm">
            <div className="flex justify-between items-center mb-3">
              <h3 className="font-semibold text-gray-900">Ligand Options</h3>
              <button
                onClick={addSdfOption}
                className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700"
              >
                + Add
              </button>
            </div>
            
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {sdfOptions.map((option, index) => (
                <div key={option.id} className="p-3 border rounded-lg bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <input
                      type="text"
                      value={option.name}
                      onChange={(e) => updateSdfOption(option.id, 'name', e.target.value)}
                      className="text-sm font-medium bg-transparent border-none p-0 focus:ring-0 focus:outline-none flex-grow"
                    />
                    <button
                      onClick={() => removeSdfOption(option.id)}
                      className="text-red-500 hover:text-red-700 text-sm ml-2"
                    >
                      ✕
                    </button>
                  </div>
                  
                  <div className="mb-2">
                    <label className="text-xs text-gray-600">Confidence Score:</label>
                    <input
                      type="number"
                      min="0"
                      max="1"
                      step="0.001"
                      value={option.confidence}
                      onChange={(e) => updateSdfOption(option.id, 'confidence', parseFloat(e.target.value) || 0)}
                      className="w-full text-sm p-1 border border-gray-300 rounded mt-1"
                    />
                  </div>
                  
                  <textarea
                    value={option.sdfText}
                    onChange={(e) => updateSdfOption(option.id, 'sdfText', e.target.value)}
                    className="w-full h-20 p-2 border border-gray-300 rounded text-xs font-mono resize-none"
                    placeholder="SDF data..."
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Viewer Panel */}
        <div className="lg:col-span-2">
          <Mol3DViewer
            pdbText={pdbData}
            sdfOptions={sdfOptions}
            selectedSdfId={selectedSdfId}
            onSdfChange={setSelectedSdfId}
            width="100%"
            height="600px"
          />
        </div>
      </div>

      {/* Help Section */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-lg">
          <h3 className="font-semibold text-blue-900 mb-2">🎯 How to Use:</h3>
          <ul className="text-blue-800 text-sm space-y-1">
            <li>• Load a protein structure (PDB format) in the left panel</li>
            <li>• Add multiple ligand options with confidence scores</li>
            <li>• Select ligands from the dropdown to visualize binding</li>
            <li>• Higher confidence scores indicate better binding predictions</li>
          </ul>
        </div>

        <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-r-lg">
          <h3 className="font-semibold text-green-900 mb-2">📊 Confidence Levels:</h3>
          <ul className="text-green-800 text-sm space-y-1">
            <li>• <span className="font-medium">High (≥0.8):</span> Strong binding prediction</li>
            <li>• <span className="font-medium">Medium (0.6-0.8):</span> Moderate confidence</li>
            <li>• <span className="font-medium">Low (&lt;0.6):</span> Weak binding prediction</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default App;

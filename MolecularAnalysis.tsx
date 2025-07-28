import React, { useState, useEffect } from 'react';
import { SmilesSvgRenderer } from 'react-ocl';
import { X, Copy, Check } from 'lucide-react';

interface MolecularResult {
  smiles: string;
  score: number;
}

interface APIResponse {
  smiles: string;
  score: number;
}

const MolecularAnalysis: React.FC = () => {
  const [moleculeExample, setMoleculeExample] = useState('Spirapril');
  const [moleculeSequence, setMoleculeSequence] = useState('N13CC2(CC14)SCCS2.C4(=O)O.[*{20-25}]');
  const [numMolecules, setNumMolecules] = useState(30);
  const [temperature, setTemperature] = useState(1);
  const [noise, setNoise] = useState(0);
  const [diffusionStepSize, setDiffusionStepSize] = useState(1);
  const [propertyToCompute, setPropertyToCompute] = useState('QED');
  const [apiKey, setApiKey] = useState('');
  const [results, setResults] = useState<MolecularResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedMolecule, setSelectedMolecule] = useState<MolecularResult | null>(null);
  const [showJsonPanel, setShowJsonPanel] = useState(false);
  const [copiedSmiles, setCopiedSmiles] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);

  // Mock data for fallback
  const mockResults: MolecularResult[] = [
    { smiles: "Cc1cccc(N2CC3(CC2C(=O)O)SCCS3)c1", score: 0.908 },
    { smiles: "O=C(O)C1CC2(CN1c1ccccc1)SCCS2", score: 0.902 },
    { smiles: "O=C(O)C1CC2(CN1c1ccc(O)nc1)SCCS2", score: 0.859 },
    { smiles: "O=CCC1CCN(C(=O)N2CC3(CC2C(=O)O)SCCS3)CC1", score: 0.775 },
    { smiles: "O=C(O)C1CC2(CN1c1ccc(Oc3ccccc3)cc1Cl)SCCS2", score: 0.772 },
    { smiles: "O=C(O)C1CC2(CN1c1ccc(Nc3ccccc3)cc1Cl)SCCS2", score: 0.751 },
    { smiles: "O=C(O)C1CC2(CN1C(=O)N1CCNCC1)SCCS2", score: 0.727 },
    { smiles: "CNC(=O)N1CC2(CC1C(=O)O)SCCS2", score: 0.726 },
    { smiles: "O=C(O)C1CC2(CN1C(=O)CO)SCCS2", score: 0.721 },
    { smiles: "O=C(O)C1CC2(CN1c1ccc(-c3nc4ccccc4o3)cc1)SCCS2", score: 0.704 },
    { smiles: "O=C(O)C1CC2(CN1)SCCS2", score: 0.657 },
    { smiles: "NC(=O)C(=O)N1CC2(CC1C(=O)O)SCCS2", score: 0.616 },
    { smiles: "NN1CC2(CC1C(=O)O)SCCS2", score: 0.615 },
    { smiles: "CCOCCNCCCNC(=O)N1CC2(CC1C(=O)O)SCCS2", score: 0.517 },
    { smiles: "O=C(O)C1CC2(CN1c1ccccc1)SCCS2", score: 0.902 },
    { smiles: "O=C(O)C1CC2(CN1c1ccccc1)SCCS2", score: 0.902 }
  ];

  const callNvidiaAPI = async () => {
    if (!apiKey.trim()) {
      // Use mock data if no API key provided
      setResults(mockResults);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('https://health.api.nvidia.com/v1/biology/nvidia/genmol/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          smiles: moleculeSequence,
          num_molecules: numMolecules.toString(),
          temperature: temperature.toString(),
          noise: noise.toString(),
          step_size: diffusionStepSize.toString(),
          scoring: propertyToCompute
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      const data: APIResponse[] = await response.json();
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      // Fallback to mock data on error
      setResults(mockResults);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRun = () => {
    callNvidiaAPI();
  };

  const handleReset = () => {
    setMoleculeExample('Spirapril');
    setMoleculeSequence('N13CC2(CC14)SCCS2.C4(=O)O.[*{20-25}]');
    setNumMolecules(30);
    setTemperature(1);
    setNoise(0);
    setDiffusionStepSize(1);
    setPropertyToCompute('QED');
    setResults([]);
    setError(null);
  };

  const getScoreColor = (score: number) => {
    // Map score (0-1) to color scale from purple to yellow
    const hue = score * 60; // 0 = purple (270°), 1 = yellow (60°)
    return `hsl(${270 + hue}, 70%, 60%)`;
  };

  const getScoreColorClass = (score: number) => {
    if (score >= 0.9) return 'bg-yellow-400';
    if (score >= 0.8) return 'bg-yellow-300';
    if (score >= 0.7) return 'bg-green-400';
    if (score >= 0.6) return 'bg-green-300';
    if (score >= 0.5) return 'bg-blue-400';
    if (score >= 0.4) return 'bg-blue-300';
    return 'bg-purple-400';
  };

  const copyToClipboard = async (text: string, type: 'smiles' | 'json') => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'smiles') {
        setCopiedSmiles(true);
        setTimeout(() => setCopiedSmiles(false), 2000);
      } else {
        setCopiedJson(true);
        setTimeout(() => setCopiedJson(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  // Initialize with mock data
  useEffect(() => {
    setResults(mockResults);
  }, []);

  const averageScore = results.length > 0 ? results.reduce((sum, r) => sum + r.score, 0) / results.length : 0;
  const maxScore = results.length > 0 ? Math.max(...results.map(r => r.score)) : 0;

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex h-screen">
        {/* Left Panel - Input Controls */}
        <div className={`${showJsonPanel ? 'w-1/4' : 'w-1/3'} bg-card border-r border-border p-6 overflow-y-auto transition-all duration-300`}>
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h2 className="ey-heading-lg mb-2">Molecular Analysis</h2>
              <p className="ey-body-sm text-muted-foreground">Configure parameters for molecular generation</p>
            </div>

            {/* API Key Input */}
            <div className="space-y-2">
              <label className="ey-caption">NVIDIA API Key (Optional)</label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter API key for real data"
                className="w-full px-3 py-2 ey-input rounded-md"
              />
              <p className="ey-body-sm text-muted-foreground">Leave empty to use mock data</p>
            </div>

            {/* Molecule Examples */}
            <div className="space-y-2">
              <label className="ey-caption">Molecule Examples</label>
              <select
                value={moleculeExample}
                onChange={(e) => setMoleculeExample(e.target.value)}
                className="w-full px-3 py-2 ey-input rounded-md bg-input"
              >
                <option value="Spirapril">Spirapril</option>
                <option value="Aspirin">Aspirin</option>
                <option value="Caffeine">Caffeine</option>
                <option value="Ibuprofen">Ibuprofen</option>
              </select>
            </div>

            {/* Molecule Sequence */}
            <div className="space-y-2">
              <label className="ey-caption">Molecule Sequence</label>
              <textarea
                value={moleculeSequence}
                onChange={(e) => setMoleculeSequence(e.target.value)}
                rows={3}
                className="w-full px-3 py-2 ey-input rounded-md resize-none"
                placeholder="Enter SMILES notation"
              />
            </div>

            {/* Number of Molecules */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="ey-caption">Number of Molecules</label>
                <span className="ey-body-sm font-mono bg-muted px-2 py-1 rounded">{numMolecules}</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={numMolecules}
                onChange={(e) => setNumMolecules(parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1</span>
                <span>100</span>
              </div>
            </div>

            {/* Temperature */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="ey-caption">Temperature</label>
                <span className="ey-body-sm font-mono bg-muted px-2 py-1 rounded">{temperature}</span>
              </div>
              <input
                type="range"
                min="0.01"
                max="10"
                step="0.01"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0.01</span>
                <span>10</span>
              </div>
            </div>

            {/* Noise */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="ey-caption">Noise</label>
                <span className="ey-body-sm font-mono bg-muted px-2 py-1 rounded">{noise}</span>
              </div>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={noise}
                onChange={(e) => setNoise(parseFloat(e.target.value))}
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0</span>
                <span>1</span>
              </div>
            </div>

            {/* Diffusion Step Size */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="ey-caption">Diffusion Step Size</label>
                <span className="ey-body-sm font-mono bg-muted px-2 py-1 rounded">{diffusionStepSize}</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                value={diffusionStepSize}
                onChange={(e) => setDiffusionStepSize(parseInt(e.target.value))}
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer slider"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1</span>
                <span>10</span>
              </div>
            </div>

            {/* Property to Compute */}
            <div className="space-y-2">
              <label className="ey-caption">Property to Compute</label>
              <select
                value={propertyToCompute}
                onChange={(e) => setPropertyToCompute(e.target.value)}
                className="w-full px-3 py-2 ey-input rounded-md bg-input"
              >
                <option value="QED">QED</option>
                <option value="LogP">LogP</option>
                <option value="SA">SA</option>
                <option value="MW">MW</option>
              </select>
            </div>

            {/* Error Display */}
            {error && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
                <p className="ey-body-sm text-destructive">{error}</p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <button
                onClick={handleReset}
                className="flex-1 px-4 py-2 ey-button-outline rounded-md transition-all"
              >
                Reset
              </button>
              <button
                onClick={handleRun}
                disabled={isLoading}
                className="flex-1 px-4 py-2 ey-button-primary rounded-md transition-all disabled:opacity-50"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full animate-spin"></div>
                    Running...
                  </div>
                ) : (
                  'Run'
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right Panel - Results */}
        <div className={`${showJsonPanel ? 'w-1/2' : 'flex-1'} bg-background p-6 overflow-y-auto transition-all duration-300`}>
          <div className="space-y-6">
            {/* Header */}
            <div className="flex justify-between items-center">
              <div>
                <h2 className="ey-heading-lg">Generated Molecules</h2>
                <p className="ey-body-sm text-muted-foreground">
                  {results.length} molecules generated
                  {results.length > 0 && (
                    <span className="ml-4">
                      Avg Score: {averageScore.toFixed(3)} | Max: {maxScore.toFixed(3)}
                    </span>
                  )}
                </p>
              </div>
              
              <div className="flex items-center gap-4">
                {/* JSON Panel Toggle */}
                <button
                  onClick={() => setShowJsonPanel(!showJsonPanel)}
                  className="px-3 py-1 ey-button-outline rounded-md text-sm transition-all"
                >
                  {showJsonPanel ? 'Hide JSON' : 'Show JSON'}
                </button>
                
                {/* Color Scale Legend */}
                <div className="flex items-center gap-2">
                  <span className="ey-caption">Score:</span>
                  <div className="flex items-center gap-1">
                    <div className="w-4 h-4 bg-purple-400 rounded"></div>
                    <span className="ey-body-sm">0.2</span>
                    <div className="w-4 h-4 bg-blue-400 rounded"></div>
                    <div className="w-4 h-4 bg-green-400 rounded"></div>
                    <div className="w-4 h-4 bg-yellow-400 rounded"></div>
                    <span className="ey-body-sm">1.0</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Results Grid */}
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                  <p className="ey-body text-muted-foreground">Generating molecules...</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-4 gap-4">
                {results.map((result, index) => (
                  <div 
                    key={index} 
                    className="ey-card p-4 space-y-3 cursor-pointer hover:scale-105 transition-transform"
                    onClick={() => setSelectedMolecule(result)}
                  >
                    {/* Molecular Structure */}
                    <div className="bg-white rounded-md p-2 h-32 flex items-center justify-center">
                      <SmilesSvgRenderer 
                        smiles={result.smiles} 
                        width={120}
                        height={100}
                      />
                    </div>
                    
                    {/* Score Display */}
                    <div className="text-center">
                      <div className={`inline-block px-3 py-1 rounded-md text-sm font-mono ${getScoreColorClass(result.score)}`}>
                        {result.score.toFixed(3)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {results.length === 0 && !isLoading && (
              <div className="text-center py-12">
                <p className="ey-body text-muted-foreground">Click "Run" to generate molecular structures</p>
              </div>
            )}
          </div>
        </div>

        {/* JSON Preview Panel */}
        {showJsonPanel && (
          <div className="w-1/4 bg-card border-l border-border p-6 overflow-y-auto">
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <h3 className="ey-heading-md">JSON Data</h3>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(results, null, 2), 'json')}
                  className="flex items-center gap-2 px-3 py-1 ey-button-outline rounded-md text-sm"
                >
                  {copiedJson ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copiedJson ? 'Copied!' : 'Copy'}
                </button>
              </div>
              
              <div className="bg-muted rounded-md p-4 overflow-auto max-h-[calc(100vh-200px)]">
                <pre className="text-sm font-mono text-foreground whitespace-pre-wrap">
                  {JSON.stringify(results, null, 2)}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Molecule Detail Modal */}
      {selectedMolecule && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-6">
              <h3 className="ey-heading-lg">Molecule Details</h3>
              <button
                onClick={() => setSelectedMolecule(null)}
                className="p-2 hover:bg-muted rounded-md transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-6">
              {/* Large Molecular Structure */}
              <div className="bg-white rounded-lg p-6 flex items-center justify-center">
                <SmilesSvgRenderer 
                  smiles={selectedMolecule.smiles} 
                  width={400}
                  height={300}
                />
              </div>
              
              {/* Molecule Information */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="ey-caption">Score</label>
                  <div className={`inline-block px-4 py-2 rounded-md text-lg font-mono ${getScoreColorClass(selectedMolecule.score)}`}>
                    {selectedMolecule.score.toFixed(3)}
                  </div>
                </div>
                
                <div className="space-y-2">
                  <label className="ey-caption">Property</label>
                  <div className="px-4 py-2 bg-muted rounded-md text-lg font-mono">
                    {propertyToCompute}
                  </div>
                </div>
              </div>
              
              {/* SMILES Code */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="ey-caption">SMILES Code</label>
                  <button
                    onClick={() => copyToClipboard(selectedMolecule.smiles, 'smiles')}
                    className="flex items-center gap-2 px-3 py-1 ey-button-outline rounded-md text-sm"
                  >
                    {copiedSmiles ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                    {copiedSmiles ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <div className="bg-muted rounded-md p-4">
                  <code className="text-sm font-mono break-all">
                    {selectedMolecule.smiles}
                  </code>
                </div>
              </div>
              
              {/* JSON Preview */}
              <div className="space-y-2">
                <label className="ey-caption">JSON Data</label>
                <div className="bg-muted rounded-md p-4">
                  <pre className="text-sm font-mono">
                    {JSON.stringify(selectedMolecule, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MolecularAnalysis;
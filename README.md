# 🔬 Drug Discovery Pipeline: Pathway Analysis for Protein Target Selection

A comprehensive Python pipeline for identifying and prioritizing protein targets for drug discovery using pathway analysis, protein function analysis, network analysis, and multi-factor scoring.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Usage Examples](#usage-examples)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

This pipeline implements a systematic approach to drug target identification by:

1. **Disease to Pathway Mapping**: Identifies relevant biological pathways using KEGG and Reactome databases
2. **Pathway Parsing**: Extracts proteins involved in disease-relevant pathways
3. **Protein Analysis**: Retrieves protein function and druggability information from UniProt
4. **Network Analysis**: Analyzes protein-protein interactions using STRING database
5. **Network Centrality**: Computes centrality measures to identify important network hubs
6. **Target Scoring**: Combines multiple factors to prioritize targets
7. **Results Output**: Generates ranked target lists with detailed analysis

## ✨ Features

- **Multi-Database Integration**: KEGG, Reactome, UniProt, and STRING APIs
- **Network Analysis**: Comprehensive protein interaction network analysis
- **Druggability Assessment**: Automated scoring of protein druggability
- **Customizable Scoring**: Adjustable weights for different prioritization factors
- **Batch Processing**: Efficient analysis of multiple proteins
- **Export Options**: Results in CSV format with detailed reports
- **Error Handling**: Robust error handling and logging
- **Rate Limiting**: Respectful API usage with configurable delays

## 🚀 Installation

### Prerequisites

- Python 3.9+ recommended
- Internet connection for API access

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Package Installation

```bash
# Clone the repository
git clone <repository-url>
cd drug-discovery-pipeline

# Install in development mode
pip install -e .
```

## 🏃‍♂️ Quick Start

### Basic Usage

```python
from drug_discovery import DrugDiscoveryPipeline

# Initialize pipeline
pipeline = DrugDiscoveryPipeline()

# Identify and rank targets for a disease
results = pipeline.identify_and_rank_targets("cancer", max_targets=20)

# Display top targets
print(results.head())
```

### Save Results

```python
# Save results to CSV
output_file = pipeline.save_results(results, "cancer")
print(f"Results saved to: {output_file}")
```

### Generate Detailed Report

```python
# Generate comprehensive report
report = pipeline.generate_detailed_report("cancer", max_targets=20)
print(f"Found {report['analysis_summary']['total_pathways_found']} pathways")
print(f"Top target: {report['analysis_summary']['top_target']}")
```

## 🏗️ Architecture

### Core Components

```
drug_discovery/
├── pathway_analysis.py      # Disease → Pathway mapping (KEGG/Reactome)
├── protein_analysis.py      # Protein function & druggability (UniProt)
├── network_analysis.py      # Protein interactions & centrality (STRING)
├── scoring.py              # Multi-factor target scoring
├── main.py                 # Main orchestration pipeline
└── __init__.py            # Package initialization
```

### Data Flow

```
Disease Name → Pathways → Proteins → Analysis → Network → Scoring → Results
     ↓            ↓          ↓         ↓         ↓         ↓        ↓
   KEGG/      Pathway    UniProt   Function   STRING   Weighted  Ranked
  Reactome    Parsing    Data      Analysis   Network   Score    DataFrame
```

## 📖 Usage Examples

### Example 1: Basic Target Identification

```python
from drug_discovery import identify_and_rank_targets

# Simple function call
results = identify_and_rank_targets("alzheimer", max_targets=15)
print(f"Found {len(results)} targets")
```

### Example 2: Custom Scoring Weights

```python
from drug_discovery import DrugDiscoveryPipeline

pipeline = DrugDiscoveryPipeline()

# Adjust scoring weights
pipeline.update_scoring_weights(
    druggability_weight=0.5,  # Emphasize druggability
    centrality_weight=0.3,    # Network importance
    pathway_weight=0.15,      # Pathway involvement
    disease_weight=0.05       # Disease association
)

results = pipeline.identify_and_rank_targets("diabetes")
```

### Example 3: Compare Multiple Diseases

```python
pipeline = DrugDiscoveryPipeline()

# Compare target identification across diseases
comparison = pipeline.compare_diseases(
    ["cancer", "alzheimer", "diabetes"], 
    max_targets=10
)

for disease, data in comparison.items():
    if 'error' not in data:
        print(f"{disease}: {data['total_targets']} targets, top: {data['top_target']}")
```

### Example 4: Individual Component Usage

```python
from drug_discovery import PathwayAnalyzer, ProteinAnalyzer, NetworkAnalyzer

# Use individual components
pathway_analyzer = PathwayAnalyzer()
protein_analyzer = ProteinAnalyzer()
network_analyzer = NetworkAnalyzer()

# Get pathways for a disease
pathways = pathway_analyzer.get_pathway_ids_from_disease("cancer")
print(f"Found {len(pathways)} pathways")

# Analyze specific proteins
protein_data = protein_analyzer.get_protein_function_and_druggability("TP53")
print(f"Druggability score: {protein_data['druggability_score']}")

# Get protein interactions
interactions = network_analyzer.get_protein_interactions("TP53")
print(f"Found {len(interactions)} interactions")
```

## 📚 API Reference

### DrugDiscoveryPipeline

Main orchestration class for the drug discovery pipeline.

#### Methods

- `identify_and_rank_targets(disease_name, max_targets=50, include_network_analysis=True)`
- `generate_detailed_report(disease_name, max_targets=50)`
- `save_results(results_df, disease_name, output_dir="results")`
- `compare_diseases(disease_list, max_targets=20)`
- `update_scoring_weights(druggability_weight, centrality_weight, pathway_weight, disease_weight)`

### PathwayAnalyzer

Handles disease to pathway mapping and pathway parsing.

#### Methods

- `get_pathway_ids_from_disease(disease_name)`
- `get_proteins_from_pathway(pathway_id)`
- `get_pathway_info(pathway_id)`

### ProteinAnalyzer

Manages protein function and druggability analysis.

#### Methods

- `get_protein_function_and_druggability(protein_id)`
- `batch_analyze_proteins(protein_ids)`
- `get_protein_interactions_partners(uniprot_id)`

### NetworkAnalyzer

Performs network analysis and centrality calculations.

#### Methods

- `get_protein_interactions(protein_id)`
- `get_interaction_network(protein_ids)`
- `compute_network_centrality(network_data)`
- `analyze_protein_network(protein_ids)`

### TargetScorer

Handles multi-factor scoring and ranking.

#### Methods

- `compute_protein_target_score(protein_data, centrality_score, pathway_involvement, disease_relevance)`
- `score_target_list(protein_analyses, centrality_scores, pathway_involvement, disease_associations)`
- `create_scoring_report(target_scores)`
- `export_results_to_dataframe(target_scores)`

## ⚙️ Configuration

### Scoring Weights

Default scoring weights can be adjusted:

```python
# Default weights
druggability_weight = 0.4  # 40% - Protein druggability
centrality_weight = 0.3    # 30% - Network centrality
pathway_weight = 0.2       # 20% - Pathway involvement
disease_weight = 0.1       # 10% - Disease association
```

### API Rate Limits

```python
# Configure request delays
pipeline = DrugDiscoveryPipeline(
    request_delay=0.1,        # 100ms delay between requests
    score_threshold=400,      # STRING interaction score threshold
    max_proteins_per_pathway=50  # Limit proteins per pathway
)
```

## 📊 Output Format

### Results DataFrame Columns

| Column | Description |
|--------|-------------|
| Rank | Target ranking (1 = highest priority) |
| Protein ID | Protein identifier |
| Protein Name | Full protein name |
| Final Score | Composite prioritization score (0-1) |
| Druggability Score | Druggability assessment (0-1) |
| Centrality Score | Network centrality measure (0-1) |
| Pathway Score | Pathway involvement score (0-1) |
| Disease Relevance Score | Disease association score (0-1) |
| Confidence Score | Data quality confidence (0-1) |

### Example Output

```
Rank  Protein ID  Protein Name                    Final Score  Druggability Score  Centrality Score
1     EGFR        Epidermal growth factor receptor     0.847           0.923              0.756
2     TP53        Tumor protein p53                    0.834           0.812              0.789
3     BRCA1       Breast cancer 1                      0.798           0.745              0.823
```

## 🧪 Testing

Run the test suite:

```bash
# Run individual module tests
python -m drug_discovery.pathway_analysis
python -m drug_discovery.protein_analysis
python -m drug_discovery.network_analysis
python -m drug_discovery.scoring
python -m drug_discovery.main

# Run pipeline test
python -c "from drug_discovery import DrugDiscoveryPipeline; print('Testing...'); pipeline = DrugDiscoveryPipeline(); results = pipeline.identify_and_rank_targets('cancer', max_targets=5); print(f'Success: {len(results)} targets found')"
```

## 🔬 Implementation Details

### Database APIs Used

- **KEGG REST API**: Disease-pathway mapping and pathway information
- **Reactome ContentService**: Pathway analysis and protein participants
- **UniProt REST API**: Protein function, druggability, and annotations
- **STRING API**: Protein-protein interaction networks

### Network Analysis Features

- **Centrality Measures**: Degree, betweenness, closeness, PageRank, eigenvector
- **Community Detection**: Functional protein clusters
- **Network Properties**: Density, connectivity, clustering coefficient
- **Hub Identification**: Key network nodes with high centrality

### Scoring Algorithm

The final score combines multiple factors:

```
Final Score = w₁×Druggability + w₂×Centrality + w₃×Pathway + w₄×Disease
```

Where:
- **Druggability**: Based on binding sites, known drugs, structural features
- **Centrality**: Network importance and connectivity
- **Pathway**: Number of disease-relevant pathways
- **Disease**: Direct disease associations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- KEGG Database for pathway information
- Reactome for pathway analysis
- UniProt for protein data
- STRING for protein interaction networks
- NetworkX for network analysis algorithms

## 📧 Contact

For questions or support, please contact: [contact@drugdiscovery.example.com](mailto:contact@drugdiscovery.example.com)

---

**Note**: This pipeline is for research purposes. Always validate computational predictions with experimental data before proceeding with drug development.
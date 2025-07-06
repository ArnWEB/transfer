"""
Drug Discovery Package for Protein Target Identification and Prioritization

This package implements a comprehensive pipeline for identifying and prioritizing 
protein targets for drug discovery using pathway analysis, protein function analysis, 
network analysis, and multi-factor scoring.

Main Components:
- PathwayAnalyzer: Disease to pathway mapping using KEGG and Reactome
- ProteinAnalyzer: Protein function and druggability analysis using UniProt
- NetworkAnalyzer: Protein-protein interaction analysis using STRING
- TargetScorer: Multi-factor scoring and ranking of targets
- DrugDiscoveryPipeline: Main orchestration class

Example Usage:
    from drug_discovery import DrugDiscoveryPipeline
    
    pipeline = DrugDiscoveryPipeline()
    results = pipeline.identify_and_rank_targets("cancer", max_targets=20)
    print(results.head())
"""

from .pathway_analysis import PathwayAnalyzer
from .protein_analysis import ProteinAnalyzer
from .network_analysis import NetworkAnalyzer
from .scoring import TargetScorer, TargetScore
from .main import DrugDiscoveryPipeline, identify_and_rank_targets

__version__ = "1.0.0"
__author__ = "Drug Discovery Team"
__email__ = "contact@drugdiscovery.example.com"

# Package metadata
__all__ = [
    "DrugDiscoveryPipeline",
    "PathwayAnalyzer",
    "ProteinAnalyzer", 
    "NetworkAnalyzer",
    "TargetScorer",
    "TargetScore",
    "identify_and_rank_targets"
]

# Package information
PACKAGE_INFO = {
    "name": "drug_discovery",
    "version": __version__,
    "description": "Pathway Analysis for Protein Target Selection",
    "author": __author__,
    "email": __email__,
    "dependencies": [
        "requests>=2.31.0",
        "pandas>=2.0.0",
        "networkx>=3.1.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0"
    ]
}

def get_package_info():
    """Get package information"""
    return PACKAGE_INFO

def version():
    """Get package version"""
    return __version__
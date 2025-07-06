"""
Scoring Module for Drug Discovery
Implements target prioritization scoring combining druggability, centrality, and other factors
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TargetScore:
    """Data class for target scoring results"""
    protein_id: str
    protein_name: str
    final_score: float
    druggability_score: float
    centrality_score: float
    pathway_score: float
    disease_relevance_score: float
    confidence_score: float
    components: Dict[str, float]
    rank: int = 0

class TargetScorer:
    """Main class for target prioritization scoring"""
    
    def __init__(self, 
                 druggability_weight: float = 0.4,
                 centrality_weight: float = 0.3,
                 pathway_weight: float = 0.2,
                 disease_weight: float = 0.1):
        """
        Initialize TargetScorer with scoring weights
        
        Args:
            druggability_weight: Weight for druggability score (0-1)
            centrality_weight: Weight for network centrality score (0-1)
            pathway_weight: Weight for pathway involvement score (0-1)
            disease_weight: Weight for disease relevance score (0-1)
        """
        # Normalize weights to sum to 1
        total_weight = druggability_weight + centrality_weight + pathway_weight + disease_weight
        
        self.weights = {
            'druggability': druggability_weight / total_weight,
            'centrality': centrality_weight / total_weight,
            'pathway': pathway_weight / total_weight,
            'disease': disease_weight / total_weight
        }
        
        logger.info(f"Initialized TargetScorer with weights: {self.weights}")
    
    def compute_protein_target_score(self, 
                                   protein_data: Dict,
                                   centrality_score: float,
                                   pathway_involvement: int = 1,
                                   disease_relevance: List[str] = None) -> float:
        """
        Calculate a final prioritization score combining druggability and centrality.
        
        Args:
            protein_data: Protein analysis data from protein_analysis module
            centrality_score: Network centrality score from network_analysis module
            pathway_involvement: Number of disease-relevant pathways protein is involved in
            disease_relevance: List of disease associations
            
        Returns:
            Final prioritization score (0-1)
        """
        # Extract druggability score
        druggability_score = protein_data.get('druggability_score', 0.0)
        
        # Calculate pathway involvement score
        pathway_score = self._calculate_pathway_score(pathway_involvement)
        
        # Calculate disease relevance score
        disease_score = self._calculate_disease_score(disease_relevance or [])
        
        # Combine scores using weights
        final_score = (
            self.weights['druggability'] * druggability_score +
            self.weights['centrality'] * centrality_score +
            self.weights['pathway'] * pathway_score +
            self.weights['disease'] * disease_score
        )
        
        return min(final_score, 1.0)  # Ensure score doesn't exceed 1.0
    
    def _calculate_pathway_score(self, pathway_involvement: int) -> float:
        """
        Calculate pathway involvement score
        
        Args:
            pathway_involvement: Number of disease-relevant pathways
            
        Returns:
            Pathway score (0-1)
        """
        if pathway_involvement == 0:
            return 0.0
        
        # Logarithmic scaling for pathway involvement
        # More pathways = higher score, but with diminishing returns
        score = np.log(pathway_involvement + 1) / np.log(10)  # Log base 10
        return min(score, 1.0)
    
    def _calculate_disease_score(self, disease_associations: List[str]) -> float:
        """
        Calculate disease relevance score
        
        Args:
            disease_associations: List of disease associations
            
        Returns:
            Disease relevance score (0-1)
        """
        if not disease_associations:
            return 0.0
        
        # Simple scoring based on number of disease associations
        # Could be enhanced with disease-specific weights
        num_associations = len(disease_associations)
        score = min(num_associations / 5.0, 1.0)  # Normalize to max 5 diseases
        
        return score
    
    def calculate_confidence_score(self, 
                                 protein_data: Dict,
                                 centrality_data: Dict,
                                 pathway_data: Dict) -> float:
        """
        Calculate confidence score based on data quality and completeness
        
        Args:
            protein_data: Protein analysis data
            centrality_data: Network centrality data
            pathway_data: Pathway involvement data
            
        Returns:
            Confidence score (0-1)
        """
        confidence_factors = []
        
        # Protein data quality
        if protein_data.get('uniprot_id'):
            confidence_factors.append(0.2)  # Has UniProt ID
        
        if protein_data.get('function'):
            confidence_factors.append(0.2)  # Has function description
        
        if protein_data.get('binding_sites'):
            confidence_factors.append(0.1)  # Has binding sites
        
        # Network data quality
        if centrality_data.get('degree', 0) > 0:
            confidence_factors.append(0.15)  # Has network connections
        
        if centrality_data.get('betweenness', 0) > 0.1:
            confidence_factors.append(0.1)  # Significant betweenness centrality
        
        # Pathway data quality
        if pathway_data.get('pathway_count', 0) > 0:
            confidence_factors.append(0.15)  # Involved in pathways
        
        if pathway_data.get('pathway_names'):
            confidence_factors.append(0.1)  # Has pathway names
        
        confidence_score = sum(confidence_factors)
        return min(confidence_score, 1.0)
    
    def score_target_list(self, 
                         protein_analyses: List[Dict],
                         centrality_scores: Dict[str, Dict],
                         pathway_involvement: Dict[str, int],
                         disease_associations: Dict[str, List[str]] = None) -> List[TargetScore]:
        """
        Score a list of protein targets
        
        Args:
            protein_analyses: List of protein analysis results
            centrality_scores: Dictionary of centrality scores by protein ID
            pathway_involvement: Dictionary of pathway involvement counts by protein ID
            disease_associations: Dictionary of disease associations by protein ID
            
        Returns:
            List of TargetScore objects, sorted by final score
        """
        target_scores = []
        
        for protein_data in protein_analyses:
            if protein_data.get('error'):
                continue
                
            protein_id = protein_data.get('protein_id', '')
            protein_name = protein_data.get('protein_name', '')
            
            # Get centrality score
            centrality_data = centrality_scores.get(protein_id, {})
            centrality_score = centrality_data.get('composite', 0.0)
            
            # Get pathway involvement
            pathway_count = pathway_involvement.get(protein_id, 0)
            
            # Get disease associations
            diseases = disease_associations.get(protein_id, []) if disease_associations else []
            
            # Calculate final score
            final_score = self.compute_protein_target_score(
                protein_data, centrality_score, pathway_count, diseases
            )
            
            # Calculate individual component scores
            druggability_score = protein_data.get('druggability_score', 0.0)
            pathway_score = self._calculate_pathway_score(pathway_count)
            disease_score = self._calculate_disease_score(diseases)
            
            # Calculate confidence score
            confidence_score = self.calculate_confidence_score(
                protein_data, centrality_data, {'pathway_count': pathway_count}
            )
            
            # Create TargetScore object
            target_score = TargetScore(
                protein_id=protein_id,
                protein_name=protein_name,
                final_score=final_score,
                druggability_score=druggability_score,
                centrality_score=centrality_score,
                pathway_score=pathway_score,
                disease_relevance_score=disease_score,
                confidence_score=confidence_score,
                components={
                    'druggability_weighted': self.weights['druggability'] * druggability_score,
                    'centrality_weighted': self.weights['centrality'] * centrality_score,
                    'pathway_weighted': self.weights['pathway'] * pathway_score,
                    'disease_weighted': self.weights['disease'] * disease_score
                }
            )
            
            target_scores.append(target_score)
        
        # Sort by final score (descending)
        target_scores.sort(key=lambda x: x.final_score, reverse=True)
        
        # Add ranks
        for i, score in enumerate(target_scores):
            score.rank = i + 1
        
        return target_scores
    
    def create_scoring_report(self, target_scores: List[TargetScore]) -> Dict:
        """
        Create a comprehensive scoring report
        
        Args:
            target_scores: List of TargetScore objects
            
        Returns:
            Dictionary containing scoring report
        """
        if not target_scores:
            return {
                'summary': {'total_targets': 0, 'error': 'No targets to score'},
                'top_targets': [],
                'statistics': {}
            }
        
        # Calculate statistics
        final_scores = [score.final_score for score in target_scores]
        druggability_scores = [score.druggability_score for score in target_scores]
        centrality_scores = [score.centrality_score for score in target_scores]
        
        statistics = {
            'final_score': {
                'mean': np.mean(final_scores),
                'median': np.median(final_scores),
                'std': np.std(final_scores),
                'min': np.min(final_scores),
                'max': np.max(final_scores)
            },
            'druggability': {
                'mean': np.mean(druggability_scores),
                'median': np.median(druggability_scores),
                'std': np.std(druggability_scores)
            },
            'centrality': {
                'mean': np.mean(centrality_scores),
                'median': np.median(centrality_scores),
                'std': np.std(centrality_scores)
            }
        }
        
        # Create summary
        summary = {
            'total_targets': len(target_scores),
            'top_score': target_scores[0].final_score if target_scores else 0,
            'top_target': target_scores[0].protein_name if target_scores else '',
            'avg_score': statistics['final_score']['mean'],
            'scoring_weights': self.weights
        }
        
        # Get top targets
        top_targets = []
        for score in target_scores[:10]:  # Top 10
            top_targets.append({
                'rank': score.rank,
                'protein_id': score.protein_id,
                'protein_name': score.protein_name,
                'final_score': round(score.final_score, 3),
                'druggability_score': round(score.druggability_score, 3),
                'centrality_score': round(score.centrality_score, 3),
                'pathway_score': round(score.pathway_score, 3),
                'disease_score': round(score.disease_relevance_score, 3),
                'confidence_score': round(score.confidence_score, 3)
            })
        
        return {
            'summary': summary,
            'top_targets': top_targets,
            'statistics': statistics,
            'scoring_weights': self.weights
        }
    
    def export_results_to_dataframe(self, target_scores: List[TargetScore]) -> pd.DataFrame:
        """
        Export target scores to pandas DataFrame
        
        Args:
            target_scores: List of TargetScore objects
            
        Returns:
            pandas DataFrame with target scores
        """
        data = []
        
        for score in target_scores:
            data.append({
                'Rank': score.rank,
                'Protein ID': score.protein_id,
                'Protein Name': score.protein_name,
                'Final Score': score.final_score,
                'Druggability Score': score.druggability_score,
                'Centrality Score': score.centrality_score,
                'Pathway Score': score.pathway_score,
                'Disease Relevance Score': score.disease_relevance_score,
                'Confidence Score': score.confidence_score,
                'Druggability (Weighted)': score.components['druggability_weighted'],
                'Centrality (Weighted)': score.components['centrality_weighted'],
                'Pathway (Weighted)': score.components['pathway_weighted'],
                'Disease (Weighted)': score.components['disease_weighted']
            })
        
        return pd.DataFrame(data)
    
    def adjust_scoring_weights(self, 
                             druggability_weight: float = None,
                             centrality_weight: float = None,
                             pathway_weight: float = None,
                             disease_weight: float = None):
        """
        Adjust scoring weights for re-scoring
        
        Args:
            druggability_weight: New weight for druggability score
            centrality_weight: New weight for centrality score
            pathway_weight: New weight for pathway score
            disease_weight: New weight for disease relevance score
        """
        # Update weights if provided
        if druggability_weight is not None:
            self.weights['druggability'] = druggability_weight
        if centrality_weight is not None:
            self.weights['centrality'] = centrality_weight
        if pathway_weight is not None:
            self.weights['pathway'] = pathway_weight
        if disease_weight is not None:
            self.weights['disease'] = disease_weight
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        for key in self.weights:
            self.weights[key] /= total_weight
        
        logger.info(f"Updated scoring weights: {self.weights}")

# Example usage and testing
if __name__ == "__main__":
    # Test the target scorer
    scorer = TargetScorer()
    
    # Mock data for testing
    protein_analyses = [
        {
            'protein_id': 'TP53',
            'protein_name': 'Tumor protein p53',
            'druggability_score': 0.8,
            'uniprot_id': 'P04637',
            'function': 'Acts as a tumor suppressor',
            'binding_sites': ['DNA-binding domain']
        },
        {
            'protein_id': 'EGFR',
            'protein_name': 'Epidermal growth factor receptor',
            'druggability_score': 0.9,
            'uniprot_id': 'P00533',
            'function': 'Receptor tyrosine kinase',
            'binding_sites': ['ATP-binding site']
        }
    ]
    
    centrality_scores = {
        'TP53': {'composite': 0.7, 'degree': 0.8, 'betweenness': 0.6},
        'EGFR': {'composite': 0.6, 'degree': 0.7, 'betweenness': 0.5}
    }
    
    pathway_involvement = {
        'TP53': 5,
        'EGFR': 3
    }
    
    disease_associations = {
        'TP53': ['cancer', 'Li-Fraumeni syndrome'],
        'EGFR': ['cancer', 'lung adenocarcinoma']
    }
    
    # Score targets
    target_scores = scorer.score_target_list(
        protein_analyses, centrality_scores, pathway_involvement, disease_associations
    )
    
    # Create report
    report = scorer.create_scoring_report(target_scores)
    
    print("Target Scoring Report:")
    print(f"Total targets: {report['summary']['total_targets']}")
    print(f"Top target: {report['summary']['top_target']}")
    print(f"Top score: {report['summary']['top_score']:.3f}")
    print(f"Average score: {report['summary']['avg_score']:.3f}")
    
    print("\nTop targets:")
    for target in report['top_targets']:
        print(f"{target['rank']}. {target['protein_name']} ({target['protein_id']})")
        print(f"   Final Score: {target['final_score']}")
        print(f"   Druggability: {target['druggability_score']}")
        print(f"   Centrality: {target['centrality_score']}")
        print()
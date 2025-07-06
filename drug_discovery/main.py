"""
Main Orchestration Module for Drug Discovery Pipeline
Integrates pathway analysis, protein analysis, network analysis, and scoring
"""

import pandas as pd
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
import os

# Import our modules
from .pathway_analysis import PathwayAnalyzer
from .protein_analysis import ProteinAnalyzer
from .network_analysis import NetworkAnalyzer
from .scoring import TargetScorer, TargetScore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DrugDiscoveryPipeline:
    """
    Main pipeline for drug discovery target identification and prioritization
    """
    
    def __init__(self, 
                 request_delay: float = 0.1,
                 score_threshold: int = 400,
                 max_proteins_per_pathway: int = 50):
        """
        Initialize the drug discovery pipeline
        
        Args:
            request_delay: Delay between API requests
            score_threshold: Minimum interaction score for STRING database
            max_proteins_per_pathway: Maximum proteins to extract per pathway
        """
        self.pathway_analyzer = PathwayAnalyzer(request_delay)
        self.protein_analyzer = ProteinAnalyzer(request_delay)
        self.network_analyzer = NetworkAnalyzer(request_delay, score_threshold)
        self.target_scorer = TargetScorer()
        
        self.max_proteins_per_pathway = max_proteins_per_pathway
        
        logger.info("Initialized DrugDiscoveryPipeline")
    
    def identify_and_rank_targets(self, disease_name: str, 
                                max_targets: int = 50,
                                include_network_analysis: bool = True) -> pd.DataFrame:
        """
        Full pipeline: given disease name, return a ranked list of target proteins with details.
        
        Args:
            disease_name: Name of the disease to analyze
            max_targets: Maximum number of targets to return
            include_network_analysis: Whether to include network analysis
            
        Returns:
            pandas DataFrame with ranked target proteins
        """
        logger.info(f"Starting target identification for disease: {disease_name}")
        
        try:
            # Step 1: Disease to Pathway Mapping
            logger.info("Step 1: Mapping disease to pathways...")
            pathway_ids = self.pathway_analyzer.get_pathway_ids_from_disease(disease_name)
            logger.info(f"Found {len(pathway_ids)} pathways for {disease_name}")
            
            if not pathway_ids:
                logger.warning(f"No pathways found for disease: {disease_name}")
                return pd.DataFrame()
            
            # Step 2: Pathway Parsing
            logger.info("Step 2: Extracting proteins from pathways...")
            all_proteins = set()
            pathway_involvement = {}
            
            for pathway_id in pathway_ids:
                proteins = self.pathway_analyzer.get_proteins_from_pathway(pathway_id)
                logger.info(f"Found {len(proteins)} proteins in pathway {pathway_id}")
                
                # Limit proteins per pathway to avoid overwhelming the analysis
                proteins = proteins[:self.max_proteins_per_pathway]
                
                for protein in proteins:
                    all_proteins.add(protein)
                    pathway_involvement[protein] = pathway_involvement.get(protein, 0) + 1
            
            logger.info(f"Total unique proteins found: {len(all_proteins)}")
            
            # Limit total proteins for analysis
            protein_list = list(all_proteins)[:max_targets * 2]  # Get more than needed for filtering
            
            # Step 3: Protein Function and Druggability Analysis
            logger.info("Step 3: Analyzing protein function and druggability...")
            protein_analyses = self.protein_analyzer.batch_analyze_proteins(protein_list)
            
            # Filter out proteins with errors
            valid_proteins = [p for p in protein_analyses if not p.get('error')]
            logger.info(f"Successfully analyzed {len(valid_proteins)} proteins")
            
            if not valid_proteins:
                logger.warning("No valid proteins found for analysis")
                return pd.DataFrame()
            
            # Step 4: Network Analysis (if enabled)
            centrality_scores = {}
            if include_network_analysis:
                logger.info("Step 4: Performing network analysis...")
                
                # Extract protein IDs for network analysis
                protein_ids = [p['protein_id'] for p in valid_proteins]
                
                try:
                    network_results = self.network_analyzer.analyze_protein_network(protein_ids)
                    centrality_scores = network_results.get('centrality_scores', {})
                    logger.info(f"Network analysis completed for {len(centrality_scores)} proteins")
                except Exception as e:
                    logger.error(f"Network analysis failed: {e}")
                    # Continue without network analysis
                    centrality_scores = {p['protein_id']: {'composite': 0.0} for p in valid_proteins}
            else:
                # Use default centrality scores
                centrality_scores = {p['protein_id']: {'composite': 0.0} for p in valid_proteins}
            
            # Step 5: Target Scoring and Ranking
            logger.info("Step 5: Scoring and ranking targets...")
            
            # Prepare disease associations
            disease_associations = {}
            for protein in valid_proteins:
                protein_id = protein['protein_id']
                diseases = protein.get('diseases', [])
                if disease_name.lower() in ' '.join(diseases).lower():
                    disease_associations[protein_id] = diseases
                else:
                    disease_associations[protein_id] = []
            
            # Score targets
            target_scores = self.target_scorer.score_target_list(
                valid_proteins,
                centrality_scores,
                pathway_involvement,
                disease_associations
            )
            
            # Limit to requested number of targets
            target_scores = target_scores[:max_targets]
            
            # Convert to DataFrame
            results_df = self.target_scorer.export_results_to_dataframe(target_scores)
            
            logger.info(f"Pipeline completed successfully. Returning {len(results_df)} targets.")
            
            return results_df
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}")
            raise
    
    def generate_detailed_report(self, disease_name: str, 
                               max_targets: int = 50) -> Dict:
        """
        Generate a detailed analysis report
        
        Args:
            disease_name: Name of the disease to analyze
            max_targets: Maximum number of targets to analyze
            
        Returns:
            Dictionary containing detailed analysis results
        """
        logger.info(f"Generating detailed report for: {disease_name}")
        
        # Run the main pipeline
        results_df = self.identify_and_rank_targets(disease_name, max_targets)
        
        if results_df.empty:
            return {
                'disease': disease_name,
                'timestamp': datetime.now().isoformat(),
                'error': 'No targets found',
                'results': {}
            }
        
        # Get additional analysis details
        pathway_ids = self.pathway_analyzer.get_pathway_ids_from_disease(disease_name)
        pathway_details = []
        
        for pathway_id in pathway_ids[:10]:  # Limit to top 10 pathways
            pathway_info = self.pathway_analyzer.get_pathway_info(pathway_id)
            if pathway_info:
                pathway_details.append(pathway_info)
        
        # Create comprehensive report
        report = {
            'disease': disease_name,
            'timestamp': datetime.now().isoformat(),
            'analysis_summary': {
                'total_pathways_found': len(pathway_ids),
                'total_targets_analyzed': len(results_df),
                'top_target': results_df.iloc[0]['Protein Name'] if not results_df.empty else None,
                'top_score': results_df.iloc[0]['Final Score'] if not results_df.empty else None,
                'avg_druggability_score': results_df['Druggability Score'].mean() if not results_df.empty else None,
                'avg_centrality_score': results_df['Centrality Score'].mean() if not results_df.empty else None
            },
            'pathway_details': pathway_details,
            'top_targets': results_df.head(10).to_dict('records') if not results_df.empty else [],
            'scoring_statistics': {
                'final_score_distribution': {
                    'mean': results_df['Final Score'].mean() if not results_df.empty else None,
                    'std': results_df['Final Score'].std() if not results_df.empty else None,
                    'min': results_df['Final Score'].min() if not results_df.empty else None,
                    'max': results_df['Final Score'].max() if not results_df.empty else None
                },
                'druggability_distribution': {
                    'mean': results_df['Druggability Score'].mean() if not results_df.empty else None,
                    'std': results_df['Druggability Score'].std() if not results_df.empty else None
                }
            }
        }
        
        return report
    
    def save_results(self, results_df: pd.DataFrame, 
                    disease_name: str, 
                    output_dir: str = "results") -> str:
        """
        Save results to CSV file
        
        Args:
            results_df: Results DataFrame
            disease_name: Disease name for filename
            output_dir: Output directory
            
        Returns:
            Path to saved file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{disease_name.replace(' ', '_')}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        
        # Save to CSV
        results_df.to_csv(filepath, index=False)
        
        logger.info(f"Results saved to: {filepath}")
        return filepath
    
    def compare_diseases(self, disease_list: List[str], 
                        max_targets: int = 20) -> Dict:
        """
        Compare target identification results across multiple diseases
        
        Args:
            disease_list: List of disease names to compare
            max_targets: Maximum targets per disease
            
        Returns:
            Dictionary with comparison results
        """
        logger.info(f"Comparing diseases: {disease_list}")
        
        comparison_results = {}
        
        for disease in disease_list:
            try:
                results_df = self.identify_and_rank_targets(disease, max_targets)
                
                if not results_df.empty:
                    comparison_results[disease] = {
                        'total_targets': len(results_df),
                        'top_target': results_df.iloc[0]['Protein Name'],
                        'top_score': results_df.iloc[0]['Final Score'],
                        'avg_druggability': results_df['Druggability Score'].mean(),
                        'avg_centrality': results_df['Centrality Score'].mean(),
                        'targets': results_df.head(10).to_dict('records')
                    }
                else:
                    comparison_results[disease] = {
                        'total_targets': 0,
                        'error': 'No targets found'
                    }
                    
            except Exception as e:
                comparison_results[disease] = {
                    'error': str(e)
                }
        
        return comparison_results
    
    def update_scoring_weights(self, 
                             druggability_weight: float = None,
                             centrality_weight: float = None,
                             pathway_weight: float = None,
                             disease_weight: float = None):
        """
        Update scoring weights for the pipeline
        
        Args:
            druggability_weight: Weight for druggability score
            centrality_weight: Weight for centrality score
            pathway_weight: Weight for pathway involvement
            disease_weight: Weight for disease relevance
        """
        self.target_scorer.adjust_scoring_weights(
            druggability_weight,
            centrality_weight,
            pathway_weight,
            disease_weight
        )
        
        logger.info("Scoring weights updated")

# Convenience function for direct usage
def identify_and_rank_targets(disease_name: str, 
                            max_targets: int = 50,
                            output_file: str = None) -> pd.DataFrame:
    """
    Convenience function to run the full pipeline
    
    Args:
        disease_name: Name of the disease to analyze
        max_targets: Maximum number of targets to return
        output_file: Optional output file path
        
    Returns:
        DataFrame with ranked target proteins
    """
    pipeline = DrugDiscoveryPipeline()
    results = pipeline.identify_and_rank_targets(disease_name, max_targets)
    
    if output_file:
        results.to_csv(output_file, index=False)
        logger.info(f"Results saved to: {output_file}")
    
    return results

# Example usage and testing
if __name__ == "__main__":
    # Test the pipeline
    pipeline = DrugDiscoveryPipeline()
    
    # Test with a disease
    disease = "cancer"
    print(f"Testing pipeline with disease: {disease}")
    
    try:
        # Run the pipeline
        results = pipeline.identify_and_rank_targets(disease, max_targets=10)
        
        if not results.empty:
            print(f"\nTop 5 targets for {disease}:")
            print(results.head().to_string(index=False))
            
            # Save results
            output_file = pipeline.save_results(results, disease)
            print(f"\nResults saved to: {output_file}")
            
            # Generate detailed report
            report = pipeline.generate_detailed_report(disease, max_targets=10)
            print(f"\nAnalysis Summary:")
            print(f"Total pathways found: {report['analysis_summary']['total_pathways_found']}")
            print(f"Total targets analyzed: {report['analysis_summary']['total_targets_analyzed']}")
            print(f"Top target: {report['analysis_summary']['top_target']}")
            print(f"Top score: {report['analysis_summary']['top_score']:.3f}")
            
        else:
            print(f"No results found for {disease}")
            
    except Exception as e:
        print(f"Error running pipeline: {e}")
        logger.error(f"Pipeline error: {e}")
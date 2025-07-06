#!/usr/bin/env python3
"""
Example Usage Script for Drug Discovery Pipeline
Demonstrates basic usage of the pathway analysis system for protein target selection
"""

import sys
import os
import pandas as pd
from datetime import datetime

# Add the drug_discovery package to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the pipeline
from drug_discovery import DrugDiscoveryPipeline, identify_and_rank_targets

def example_basic_usage():
    """
    Example 1: Basic target identification
    """
    print("=" * 60)
    print("Example 1: Basic Target Identification")
    print("=" * 60)
    
    # Simple function call
    disease = "cancer"
    print(f"Identifying targets for: {disease}")
    
    try:
        results = identify_and_rank_targets(disease, max_targets=10)
        
        if not results.empty:
            print(f"\nFound {len(results)} targets:")
            print(results[['Rank', 'Protein ID', 'Protein Name', 'Final Score', 
                          'Druggability Score', 'Centrality Score']].to_string(index=False))
        else:
            print("No targets found.")
    except Exception as e:
        print(f"Error: {e}")

def example_custom_pipeline():
    """
    Example 2: Custom pipeline with adjusted weights
    """
    print("\n" + "=" * 60)
    print("Example 2: Custom Pipeline with Adjusted Weights")
    print("=" * 60)
    
    # Initialize pipeline
    pipeline = DrugDiscoveryPipeline()
    
    # Adjust scoring weights to emphasize druggability
    pipeline.update_scoring_weights(
        druggability_weight=0.5,  # Emphasize druggability
        centrality_weight=0.3,    # Network importance
        pathway_weight=0.15,      # Pathway involvement
        disease_weight=0.05       # Disease association
    )
    
    disease = "diabetes"
    print(f"Identifying targets for: {disease}")
    print("Using custom weights: Druggability=0.5, Centrality=0.3, Pathway=0.15, Disease=0.05")
    
    try:
        results = pipeline.identify_and_rank_targets(disease, max_targets=10)
        
        if not results.empty:
            print(f"\nFound {len(results)} targets:")
            print(results.head()[['Rank', 'Protein ID', 'Protein Name', 'Final Score']].to_string(index=False))
            
            # Save results
            output_file = pipeline.save_results(results, disease)
            print(f"\nResults saved to: {output_file}")
        else:
            print("No targets found.")
    except Exception as e:
        print(f"Error: {e}")

def example_detailed_report():
    """
    Example 3: Generate detailed analysis report
    """
    print("\n" + "=" * 60)
    print("Example 3: Detailed Analysis Report")
    print("=" * 60)
    
    pipeline = DrugDiscoveryPipeline()
    disease = "alzheimer"
    
    print(f"Generating detailed report for: {disease}")
    
    try:
        report = pipeline.generate_detailed_report(disease, max_targets=10)
        
        if 'error' not in report:
            print(f"\nAnalysis Summary:")
            print(f"• Total pathways found: {report['analysis_summary']['total_pathways_found']}")
            print(f"• Total targets analyzed: {report['analysis_summary']['total_targets_analyzed']}")
            print(f"• Top target: {report['analysis_summary']['top_target']}")
            print(f"• Top score: {report['analysis_summary']['top_score']:.3f}")
            print(f"• Average druggability: {report['analysis_summary']['avg_druggability_score']:.3f}")
            print(f"• Average centrality: {report['analysis_summary']['avg_centrality_score']:.3f}")
            
            print(f"\nTop 5 Targets:")
            for i, target in enumerate(report['top_targets'][:5]):
                print(f"{i+1}. {target['Protein Name']} ({target['Protein ID']})")
                print(f"   Score: {target['Final Score']:.3f}, Druggability: {target['Druggability Score']:.3f}")
            
            print(f"\nPathway Details:")
            for pathway in report['pathway_details'][:3]:
                print(f"• {pathway.get('name', 'Unknown pathway')} ({pathway.get('source', 'Unknown')})")
        else:
            print(f"Error generating report: {report['error']}")
    except Exception as e:
        print(f"Error: {e}")

def example_compare_diseases():
    """
    Example 4: Compare multiple diseases
    """
    print("\n" + "=" * 60)
    print("Example 4: Disease Comparison")
    print("=" * 60)
    
    pipeline = DrugDiscoveryPipeline()
    diseases = ["cancer", "diabetes", "alzheimer"]
    
    print(f"Comparing diseases: {diseases}")
    
    try:
        comparison = pipeline.compare_diseases(diseases, max_targets=5)
        
        print(f"\nComparison Results:")
        print("-" * 40)
        
        for disease, data in comparison.items():
            if 'error' not in data:
                print(f"{disease.capitalize()}:")
                print(f"  • Total targets: {data['total_targets']}")
                print(f"  • Top target: {data['top_target']}")
                print(f"  • Top score: {data['top_score']:.3f}")
                print(f"  • Avg druggability: {data['avg_druggability']:.3f}")
                print(f"  • Avg centrality: {data['avg_centrality']:.3f}")
            else:
                print(f"{disease.capitalize()}: Error - {data['error']}")
            print()
    except Exception as e:
        print(f"Error: {e}")

def example_individual_components():
    """
    Example 5: Using individual components
    """
    print("\n" + "=" * 60)
    print("Example 5: Individual Component Usage")
    print("=" * 60)
    
    from drug_discovery import PathwayAnalyzer, ProteinAnalyzer, NetworkAnalyzer
    
    # Initialize components
    pathway_analyzer = PathwayAnalyzer()
    protein_analyzer = ProteinAnalyzer()
    network_analyzer = NetworkAnalyzer()
    
    print("Testing individual components...")
    
    try:
        # Test pathway analysis
        print("\n1. Pathway Analysis:")
        pathways = pathway_analyzer.get_pathway_ids_from_disease("cancer")
        print(f"   Found {len(pathways)} pathways for cancer")
        
        if pathways:
            # Get info for first pathway
            pathway_info = pathway_analyzer.get_pathway_info(pathways[0])
            print(f"   First pathway: {pathway_info.get('name', 'Unknown')} ({pathway_info.get('source', 'Unknown')})")
            
            # Get proteins from pathway
            proteins = pathway_analyzer.get_proteins_from_pathway(pathways[0])
            print(f"   Proteins in pathway: {len(proteins)}")
        
        # Test protein analysis
        print("\n2. Protein Analysis:")
        test_protein = "TP53"
        protein_data = protein_analyzer.get_protein_function_and_druggability(test_protein)
        
        if not protein_data.get('error'):
            print(f"   Protein: {protein_data['protein_name']}")
            print(f"   UniProt ID: {protein_data['uniprot_id']}")
            print(f"   Druggability Score: {protein_data['druggability_score']:.3f}")
            print(f"   Function: {protein_data['function'][:100]}...")
        else:
            print(f"   Error analyzing {test_protein}: {protein_data['error']}")
        
        # Test network analysis
        print("\n3. Network Analysis:")
        interactions = network_analyzer.get_protein_interactions(test_protein)
        print(f"   {test_protein} interactions: {len(interactions)}")
        
        if interactions:
            print(f"   Top 5 partners: {interactions[:5]}")
    
    except Exception as e:
        print(f"Error: {e}")

def main():
    """
    Main function to run all examples
    """
    print("🔬 Drug Discovery Pipeline - Example Usage")
    print("=" * 60)
    
    # Run all examples
    example_basic_usage()
    # example_custom_pipeline()
    # example_detailed_report()
    # example_compare_diseases()
    # example_individual_components()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
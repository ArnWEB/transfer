"""
Network Analysis Module for Drug Discovery
Implements protein-protein interaction retrieval using STRING API and network centrality analysis
"""

import requests
import json
import networkx as nx
import numpy as np
from typing import List, Dict, Optional, Union, Tuple
from urllib.parse import quote
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkAnalyzer:
    """Main class for network analysis operations"""
    
    def __init__(self, request_delay: float = 0.1, score_threshold: int = 400):
        """
        Initialize NetworkAnalyzer
        
        Args:
            request_delay: Delay between API requests to respect rate limits
            score_threshold: Minimum interaction score for STRING database (0-1000)
        """
        self.request_delay = request_delay
        self.score_threshold = score_threshold
        self.string_base_url = "https://string-db.org/api"
        self.species_id = "9606"  # Human
        
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make HTTP request with error handling and rate limiting
        
        Args:
            url: URL to request
            params: Optional query parameters
            
        Returns:
            Response data or None if error
        """
        try:
            time.sleep(self.request_delay)
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                return {'text': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
    
    def get_protein_interactions(self, protein_id: str) -> List[str]:
        """
        Query STRING API to get interaction partners of a protein.
        
        Args:
            protein_id: Protein identifier (gene name, UniProt ID, etc.)
            
        Returns:
            List of interaction partner identifiers
        """
        # Clean protein ID
        clean_id = self._clean_protein_id(protein_id)
        
        # Get STRING interactions
        interactions = self._get_string_interactions(clean_id)
        
        # Extract partner IDs
        partners = []
        for interaction in interactions:
            partner_id = self._extract_partner_id(interaction, clean_id)
            if partner_id:
                partners.append(partner_id)
        
        return partners
    
    def _clean_protein_id(self, protein_id: str) -> str:
        """
        Clean protein ID for STRING API
        
        Args:
            protein_id: Raw protein identifier
            
        Returns:
            Cleaned protein identifier
        """
        # Remove prefixes
        if ':' in protein_id:
            protein_id = protein_id.split(':', 1)[1]
        
        # Remove common suffixes
        protein_id = protein_id.replace('_HUMAN', '').replace('_human', '')
        
        return protein_id.strip()
    
    def _get_string_interactions(self, protein_id: str) -> List[Dict]:
        """
        Get protein interactions from STRING database
        
        Args:
            protein_id: Protein identifier
            
        Returns:
            List of interaction data
        """
        try:
            url = f"{self.string_base_url}/network"
            params = {
                'identifiers': protein_id,
                'species': self.species_id,
                'required_score': self.score_threshold,
                'format': 'json'
            }
            
            response = self._make_request(url, params)
            
            if response and isinstance(response, list):
                return response
            else:
                logger.warning(f"No interactions found for {protein_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting STRING interactions for {protein_id}: {e}")
            return []
    
    def _extract_partner_id(self, interaction: Dict, query_protein: str) -> Optional[str]:
        """
        Extract interaction partner ID from STRING interaction data
        
        Args:
            interaction: STRING interaction data
            query_protein: Original query protein
            
        Returns:
            Partner protein ID or None
        """
        protein_a = interaction.get('preferredName_A', '')
        protein_b = interaction.get('preferredName_B', '')
        
        # Return the partner that's not the query protein
        if protein_a.lower() == query_protein.lower():
            return protein_b
        elif protein_b.lower() == query_protein.lower():
            return protein_a
        else:
            # If neither matches exactly, return the first one
            return protein_a if protein_a else protein_b
    
    def get_interaction_network(self, protein_ids: List[str]) -> Dict:
        """
        Get interaction network for a list of proteins
        
        Args:
            protein_ids: List of protein identifiers
            
        Returns:
            Dictionary containing network data
        """
        # Get all interactions for the protein set
        all_interactions = []
        protein_set = set()
        
        for protein_id in protein_ids:
            clean_id = self._clean_protein_id(protein_id)
            interactions = self._get_string_interactions(clean_id)
            
            for interaction in interactions:
                protein_a = interaction.get('preferredName_A', '')
                protein_b = interaction.get('preferredName_B', '')
                score = interaction.get('score', 0)
                
                # Only include interactions between proteins in our set
                if protein_a and protein_b:
                    protein_set.add(protein_a)
                    protein_set.add(protein_b)
                    all_interactions.append({
                        'protein_a': protein_a,
                        'protein_b': protein_b,
                        'score': score
                    })
        
        return {
            'proteins': list(protein_set),
            'interactions': all_interactions,
            'num_proteins': len(protein_set),
            'num_interactions': len(all_interactions)
        }
    
    def compute_network_centrality(self, network_data: Dict) -> Dict[str, float]:
        """
        Calculate centrality metrics for each node in the protein interaction network.
        
        Args:
            network_data: Network data from get_interaction_network()
            
        Returns:
            Dictionary mapping protein IDs to centrality scores
        """
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for protein in network_data['proteins']:
            G.add_node(protein)
        
        # Add edges with weights
        for interaction in network_data['interactions']:
            protein_a = interaction['protein_a']
            protein_b = interaction['protein_b']
            score = interaction['score']
            
            # Convert STRING score (0-1000) to weight (0-1)
            weight = score / 1000.0
            G.add_edge(protein_a, protein_b, weight=weight)
        
        # Calculate centrality measures
        centrality_scores = {}
        
        try:
            # Degree centrality
            degree_centrality = nx.degree_centrality(G)
            
            # Betweenness centrality
            betweenness_centrality = nx.betweenness_centrality(G, weight='weight')
            
            # Closeness centrality
            closeness_centrality = nx.closeness_centrality(G, distance='weight')
            
            # PageRank centrality
            pagerank_centrality = nx.pagerank(G, weight='weight')
            
            # Eigenvector centrality (if graph is connected)
            try:
                eigenvector_centrality = nx.eigenvector_centrality(G, weight='weight')
            except nx.NetworkXError:
                eigenvector_centrality = {node: 0.0 for node in G.nodes()}
            
            # Combine centrality measures
            for protein in G.nodes():
                centrality_scores[protein] = {
                    'degree': degree_centrality.get(protein, 0.0),
                    'betweenness': betweenness_centrality.get(protein, 0.0),
                    'closeness': closeness_centrality.get(protein, 0.0),
                    'pagerank': pagerank_centrality.get(protein, 0.0),
                    'eigenvector': eigenvector_centrality.get(protein, 0.0)
                }
                
                # Calculate composite score
                centrality_scores[protein]['composite'] = (
                    0.3 * centrality_scores[protein]['degree'] +
                    0.25 * centrality_scores[protein]['betweenness'] +
                    0.2 * centrality_scores[protein]['closeness'] +
                    0.15 * centrality_scores[protein]['pagerank'] +
                    0.1 * centrality_scores[protein]['eigenvector']
                )
                
        except Exception as e:
            logger.error(f"Error computing centrality measures: {e}")
            # Return default scores if computation fails
            for protein in network_data['proteins']:
                centrality_scores[protein] = {
                    'degree': 0.0,
                    'betweenness': 0.0,
                    'closeness': 0.0,
                    'pagerank': 0.0,
                    'eigenvector': 0.0,
                    'composite': 0.0
                }
        
        return centrality_scores
    
    def get_network_properties(self, network_data: Dict) -> Dict:
        """
        Calculate network properties and statistics
        
        Args:
            network_data: Network data from get_interaction_network()
            
        Returns:
            Dictionary containing network properties
        """
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes and edges
        for protein in network_data['proteins']:
            G.add_node(protein)
        
        for interaction in network_data['interactions']:
            protein_a = interaction['protein_a']
            protein_b = interaction['protein_b']
            score = interaction['score']
            weight = score / 1000.0
            G.add_edge(protein_a, protein_b, weight=weight)
        
        # Calculate network properties
        properties = {
            'num_nodes': G.number_of_nodes(),
            'num_edges': G.number_of_edges(),
            'density': nx.density(G),
            'is_connected': nx.is_connected(G),
            'num_connected_components': nx.number_connected_components(G),
            'average_clustering': nx.average_clustering(G),
            'transitivity': nx.transitivity(G)
        }
        
        # Calculate average degree
        degrees = [G.degree(node) for node in G.nodes()]
        properties['average_degree'] = np.mean(degrees) if degrees else 0
        properties['degree_variance'] = np.var(degrees) if degrees else 0
        
        # Calculate average path length for largest connected component
        if nx.is_connected(G):
            properties['average_path_length'] = nx.average_shortest_path_length(G)
        else:
            # Get largest connected component
            largest_cc = max(nx.connected_components(G), key=len)
            if len(largest_cc) > 1:
                subgraph = G.subgraph(largest_cc)
                properties['average_path_length'] = nx.average_shortest_path_length(subgraph)
            else:
                properties['average_path_length'] = 0
        
        return properties
    
    def identify_network_hubs(self, centrality_scores: Dict[str, Dict], 
                             top_n: int = 10) -> List[Dict]:
        """
        Identify network hubs based on centrality scores
        
        Args:
            centrality_scores: Centrality scores from compute_network_centrality()
            top_n: Number of top hubs to return
            
        Returns:
            List of hub proteins with their scores
        """
        # Sort proteins by composite centrality score
        sorted_proteins = sorted(
            centrality_scores.items(),
            key=lambda x: x[1]['composite'],
            reverse=True
        )
        
        hubs = []
        for protein, scores in sorted_proteins[:top_n]:
            hubs.append({
                'protein_id': protein,
                'composite_score': scores['composite'],
                'degree_centrality': scores['degree'],
                'betweenness_centrality': scores['betweenness'],
                'closeness_centrality': scores['closeness'],
                'pagerank_centrality': scores['pagerank'],
                'eigenvector_centrality': scores['eigenvector']
            })
        
        return hubs
    
    def get_protein_functional_clusters(self, network_data: Dict) -> List[List[str]]:
        """
        Identify functional clusters in the protein network
        
        Args:
            network_data: Network data from get_interaction_network()
            
        Returns:
            List of protein clusters
        """
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes and edges
        for protein in network_data['proteins']:
            G.add_node(protein)
        
        for interaction in network_data['interactions']:
            protein_a = interaction['protein_a']
            protein_b = interaction['protein_b']
            score = interaction['score']
            weight = score / 1000.0
            G.add_edge(protein_a, protein_b, weight=weight)
        
        # Use community detection algorithms
        try:
            # Try different community detection methods
            import networkx.algorithms.community as nx_comm
            
            # Louvain method (if available)
            try:
                communities = nx_comm.louvain_communities(G, weight='weight')
                return [list(community) for community in communities]
            except:
                pass
            
            # Greedy modularity method
            try:
                communities = nx_comm.greedy_modularity_communities(G, weight='weight')
                return [list(community) for community in communities]
            except:
                pass
            
            # Fallback: connected components
            connected_components = nx.connected_components(G)
            return [list(component) for component in connected_components]
            
        except Exception as e:
            logger.error(f"Error identifying functional clusters: {e}")
            return []
    
    def analyze_protein_network(self, protein_ids: List[str]) -> Dict:
        """
        Comprehensive network analysis for a list of proteins
        
        Args:
            protein_ids: List of protein identifiers
            
        Returns:
            Complete network analysis results
        """
        # Get network data
        network_data = self.get_interaction_network(protein_ids)
        
        # Compute centrality scores
        centrality_scores = self.compute_network_centrality(network_data)
        
        # Get network properties
        network_properties = self.get_network_properties(network_data)
        
        # Identify hubs
        hubs = self.identify_network_hubs(centrality_scores)
        
        # Find functional clusters
        clusters = self.get_protein_functional_clusters(network_data)
        
        return {
            'network_data': network_data,
            'centrality_scores': centrality_scores,
            'network_properties': network_properties,
            'hubs': hubs,
            'functional_clusters': clusters,
            'analysis_summary': {
                'num_proteins': network_data['num_proteins'],
                'num_interactions': network_data['num_interactions'],
                'density': network_properties['density'],
                'top_hub': hubs[0]['protein_id'] if hubs else None,
                'num_clusters': len(clusters)
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # Test the network analyzer
    analyzer = NetworkAnalyzer()
    
    # Test with some protein IDs
    test_proteins = ["TP53", "BRCA1", "EGFR", "MYC", "RB1"]
    
    print(f"Testing network analysis for proteins: {test_proteins}")
    
    # Test individual protein interactions
    for protein in test_proteins[:2]:  # Test first 2 proteins
        print(f"\nTesting interactions for: {protein}")
        interactions = analyzer.get_protein_interactions(protein)
        print(f"Found {len(interactions)} interactions")
        print(f"Top 5 partners: {interactions[:5]}")
    
    # Test network analysis
    print(f"\nTesting comprehensive network analysis...")
    results = analyzer.analyze_protein_network(test_proteins)
    
    print(f"Network contains {results['analysis_summary']['num_proteins']} proteins")
    print(f"Network contains {results['analysis_summary']['num_interactions']} interactions")
    print(f"Network density: {results['analysis_summary']['density']:.3f}")
    print(f"Top hub: {results['analysis_summary']['top_hub']}")
    print(f"Number of clusters: {results['analysis_summary']['num_clusters']}")
    
    # Show top hubs
    print("\nTop 3 network hubs:")
    for i, hub in enumerate(results['hubs'][:3]):
        print(f"{i+1}. {hub['protein_id']} (score: {hub['composite_score']:.3f})")
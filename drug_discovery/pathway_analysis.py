"""
Pathway Analysis Module for Drug Discovery
Implements disease to pathway mapping and pathway parsing using KEGG and Reactome APIs
"""

import requests
import json
import re
from typing import List, Dict, Optional, Union
from urllib.parse import quote
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PathwayAnalyzer:
    """Main class for pathway analysis operations"""
    
    def __init__(self, request_delay: float = 0.1):
        """
        Initialize PathwayAnalyzer
        
        Args:
            request_delay: Delay between API requests to respect rate limits
        """
        self.request_delay = request_delay
        self.kegg_base_url = "https://rest.kegg.jp"
        self.reactome_base_url = "https://reactome.org/ContentService"
        
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
            
            # Handle different response formats
            if 'json' in response.headers.get('content-type', ''):
                return response.json()
            else:
                return {'text': response.text}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
            
    def get_pathway_ids_from_disease(self, disease_name: str) -> List[str]:
        """
        Query KEGG and Reactome APIs to retrieve pathway IDs related to the disease.
        
        Args:
            disease_name: Name of the disease to search for
            
        Returns:
            List of pathway IDs from both KEGG and Reactome
        """
        pathway_ids = []
        
        # Get KEGG pathway IDs
        kegg_pathways = self._get_kegg_pathways_for_disease(disease_name)
        pathway_ids.extend(kegg_pathways)
        
        # Get Reactome pathway IDs
        reactome_pathways = self._get_reactome_pathways_for_disease(disease_name)
        pathway_ids.extend(reactome_pathways)
        
        # Remove duplicates and return
        return list(set(pathway_ids))
    
    def _get_kegg_pathways_for_disease(self, disease_name: str) -> List[str]:
        """
        Get KEGG pathway IDs for a disease
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            List of KEGG pathway IDs
        """
        pathway_ids = []
        
        try:
            # First, try to find the disease in KEGG disease database
            disease_list_url = f"{self.kegg_base_url}/list/disease"
            response = self._make_request(disease_list_url)
            
            if response and 'text' in response:
                disease_lines = response['text'].split('\n')
                disease_id = None
                
                # Search for disease ID by name
                for line in disease_lines:
                    if line and disease_name.lower() in line.lower():
                        disease_id = line.split('\t')[0].replace('ds:', '')
                        break
                
                if disease_id:
                    # Get pathways linked to this disease
                    pathway_link_url = f"{self.kegg_base_url}/link/pathway/{disease_id}"
                    response = self._make_request(pathway_link_url)
                    
                    if response and 'text' in response:
                        pathway_lines = response['text'].split('\n')
                        for line in pathway_lines:
                            if line and 'path:' in line:
                                pathway_id = line.split('\t')[1].replace('path:', '')
                                pathway_ids.append(f"kegg:{pathway_id}")
                
                # Also search for pathways by keyword
                pathway_list_url = f"{self.kegg_base_url}/list/pathway"
                response = self._make_request(pathway_list_url)
                
                if response and 'text' in response:
                    pathway_lines = response['text'].split('\n')
                    for line in pathway_lines:
                        if line and disease_name.lower() in line.lower():
                            pathway_id = line.split('\t')[0].replace('path:', '')
                            pathway_ids.append(f"kegg:{pathway_id}")
                            
        except Exception as e:
            logger.error(f"Error getting KEGG pathways for {disease_name}: {e}")
            
        return pathway_ids
    
    def _get_reactome_pathways_for_disease(self, disease_name: str) -> List[str]:
        """
        Get Reactome pathway IDs for a disease
        
        Args:
            disease_name: Name of the disease
            
        Returns:
            List of Reactome pathway IDs
        """
        pathway_ids = []
        
        try:
            # Search Reactome for disease-related pathways
            search_url = f"{self.reactome_base_url}/data/query/{quote(disease_name)}"
            response = self._make_request(search_url)
            
            if response and isinstance(response, list):
                for entry in response:
                    if entry.get('schemaClass') == 'Pathway':
                        pathway_id = entry.get('stId')
                        if pathway_id:
                            pathway_ids.append(f"reactome:{pathway_id}")
                            
        except Exception as e:
            logger.error(f"Error getting Reactome pathways for {disease_name}: {e}")
            
        return pathway_ids
    
    def get_proteins_from_pathway(self, pathway_id: str) -> List[str]:
        """
        Query KEGG or Reactome to retrieve proteins/genes involved in a pathway.
        
        Args:
            pathway_id: Pathway ID (prefixed with 'kegg:' or 'reactome:')
            
        Returns:
            List of protein/gene identifiers
        """
        if pathway_id.startswith('kegg:'):
            return self._get_kegg_pathway_proteins(pathway_id.replace('kegg:', ''))
        elif pathway_id.startswith('reactome:'):
            return self._get_reactome_pathway_proteins(pathway_id.replace('reactome:', ''))
        else:
            logger.warning(f"Unknown pathway source for {pathway_id}")
            return []
    
    def _get_kegg_pathway_proteins(self, pathway_id: str) -> List[str]:
        """
        Get proteins from KEGG pathway
        
        Args:
            pathway_id: KEGG pathway ID
            
        Returns:
            List of protein identifiers
        """
        proteins = []
        
        try:
            # Get pathway data
            pathway_url = f"{self.kegg_base_url}/get/{pathway_id}"
            response = self._make_request(pathway_url)
            
            if response and 'text' in response:
                pathway_data = response['text']
                
                # Parse KEGG pathway format to extract genes
                gene_section = False
                for line in pathway_data.split('\n'):
                    if line.startswith('GENE'):
                        gene_section = True
                        continue
                    elif line.startswith('COMPOUND') or line.startswith('REFERENCE'):
                        gene_section = False
                        continue
                        
                    if gene_section and line.strip():
                        # Extract gene ID from line
                        gene_match = re.search(r'(\w+)', line.strip())
                        if gene_match:
                            proteins.append(f"kegg:{gene_match.group(1)}")
                            
        except Exception as e:
            logger.error(f"Error getting proteins from KEGG pathway {pathway_id}: {e}")
            
        return proteins
    
    def _get_reactome_pathway_proteins(self, pathway_id: str) -> List[str]:
        """
        Get proteins from Reactome pathway
        
        Args:
            pathway_id: Reactome pathway ID
            
        Returns:
            List of protein identifiers
        """
        proteins = []
        
        try:
            # Get pathway participants
            participants_url = f"{self.reactome_base_url}/data/pathway/{pathway_id}/participants"
            response = self._make_request(participants_url)
            
            if response and isinstance(response, list):
                for participant in response:
                    if participant.get('schemaClass') in ['Protein', 'EntityWithAccessionedSequence']:
                        # Get UniProt accession if available
                        accession = participant.get('identifier')
                        if accession:
                            proteins.append(f"uniprot:{accession}")
                        
                        # Also get gene names
                        gene_names = participant.get('geneName', [])
                        if isinstance(gene_names, list):
                            for gene_name in gene_names:
                                proteins.append(f"gene:{gene_name}")
                                
        except Exception as e:
            logger.error(f"Error getting proteins from Reactome pathway {pathway_id}: {e}")
            
        return proteins
    
    def get_pathway_info(self, pathway_id: str) -> Dict:
        """
        Get detailed information about a pathway
        
        Args:
            pathway_id: Pathway ID (prefixed with 'kegg:' or 'reactome:')
            
        Returns:
            Dictionary containing pathway information
        """
        if pathway_id.startswith('kegg:'):
            return self._get_kegg_pathway_info(pathway_id.replace('kegg:', ''))
        elif pathway_id.startswith('reactome:'):
            return self._get_reactome_pathway_info(pathway_id.replace('reactome:', ''))
        else:
            return {}
    
    def _get_kegg_pathway_info(self, pathway_id: str) -> Dict:
        """Get KEGG pathway information"""
        try:
            pathway_url = f"{self.kegg_base_url}/get/{pathway_id}"
            response = self._make_request(pathway_url)
            
            if response and 'text' in response:
                pathway_data = response['text']
                
                # Parse pathway information
                info = {'id': pathway_id, 'source': 'kegg'}
                
                for line in pathway_data.split('\n'):
                    if line.startswith('NAME'):
                        info['name'] = line.replace('NAME', '').strip()
                    elif line.startswith('DESCRIPTION'):
                        info['description'] = line.replace('DESCRIPTION', '').strip()
                    elif line.startswith('CLASS'):
                        info['class'] = line.replace('CLASS', '').strip()
                        
                return info
                
        except Exception as e:
            logger.error(f"Error getting KEGG pathway info for {pathway_id}: {e}")
            
        return {}
    
    def _get_reactome_pathway_info(self, pathway_id: str) -> Dict:
        """Get Reactome pathway information"""
        try:
            pathway_url = f"{self.reactome_base_url}/data/query/{pathway_id}"
            response = self._make_request(pathway_url)
            
            if response and isinstance(response, dict):
                return {
                    'id': pathway_id,
                    'source': 'reactome',
                    'name': response.get('displayName', ''),
                    'description': response.get('summation', [{}])[0].get('text', ''),
                    'species': response.get('species', [{}])[0].get('displayName', '')
                }
                
        except Exception as e:
            logger.error(f"Error getting Reactome pathway info for {pathway_id}: {e}")
            
        return {}

# Example usage and testing
if __name__ == "__main__":
    # Test the pathway analyzer
    analyzer = PathwayAnalyzer()
    
    # Test with a disease
    disease = "cancer"
    print(f"Testing pathway analysis for: {disease}")
    
    # Get pathway IDs
    pathway_ids = analyzer.get_pathway_ids_from_disease(disease)
    print(f"Found {len(pathway_ids)} pathways")
    
    # Get proteins from first few pathways
    for pathway_id in pathway_ids[:3]:
        proteins = analyzer.get_proteins_from_pathway(pathway_id)
        pathway_info = analyzer.get_pathway_info(pathway_id)
        print(f"Pathway: {pathway_info.get('name', pathway_id)}")
        print(f"Proteins: {len(proteins)}")
        print()
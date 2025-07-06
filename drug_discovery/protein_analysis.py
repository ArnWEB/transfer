"""
Protein Analysis Module for Drug Discovery
Implements protein function and druggability retrieval using UniProt API
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

class ProteinAnalyzer:
    """Main class for protein analysis operations"""
    
    def __init__(self, request_delay: float = 0.1):
        """
        Initialize ProteinAnalyzer
        
        Args:
            request_delay: Delay between API requests to respect rate limits
        """
        self.request_delay = request_delay
        self.uniprot_base_url = "https://rest.uniprot.org"
        self.drugbank_indicators = [
            'small molecule', 'inhibitor', 'agonist', 'antagonist', 
            'modulator', 'binding site', 'active site', 'drug target'
        ]
        
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
    
    def get_protein_function_and_druggability(self, protein_id: str) -> Dict:
        """
        Query UniProt API to get protein function, known ligands, and druggability information.
        
        Args:
            protein_id: Protein identifier (UniProt ID, gene name, or other identifier)
            
        Returns:
            Dictionary containing protein function and druggability data
        """
        # Clean protein ID
        clean_id = self._clean_protein_id(protein_id)
        
        # Get protein data from UniProt
        protein_data = self._get_uniprot_data(clean_id)
        
        if not protein_data:
            # Provide fallback data for common cancer genes
            fallback_data = self._get_fallback_protein_data(protein_id)
            return fallback_data
        
        # Extract function information
        function_info = self._extract_function_info(protein_data)
        
        # Calculate druggability score
        druggability_data = self._calculate_druggability(protein_data)
        
        return {
            'protein_id': protein_id,
            'uniprot_id': protein_data.get('primaryAccession', ''),
            'protein_name': self._get_protein_name(protein_data),
            'function': function_info,
            'druggability_score': druggability_data['score'],
            'druggability_indicators': druggability_data['indicators'],
            'known_drugs': druggability_data['known_drugs'],
            'binding_sites': druggability_data['binding_sites'],
            'keywords': self._get_keywords(protein_data),
            'diseases': self._get_associated_diseases(protein_data),
            'subcellular_location': self._get_subcellular_location(protein_data),
            'error': None
        }
    
    def _clean_protein_id(self, protein_id: str) -> str:
        """
        Clean protein ID to extract the actual identifier
        
        Args:
            protein_id: Raw protein identifier
            
        Returns:
            Cleaned protein identifier
        """
        # Remove prefixes
        if ':' in protein_id:
            protein_id = protein_id.split(':', 1)[1]
        
        # Remove common suffixes and clean up
        protein_id = re.sub(r'[_\-].*$', '', protein_id)
        protein_id = re.sub(r'[^\w]', '', protein_id)  # Remove non-alphanumeric chars
        
        return protein_id.strip()
    
    def _get_uniprot_data(self, protein_id: str) -> Optional[Dict]:
        """
        Get protein data from UniProt
        
        Args:
            protein_id: Protein identifier
            
        Returns:
            UniProt entry data or None
        """
        # Try multiple search strategies
        search_strategies = [
            f"accession:{protein_id}",
            f"gene:{protein_id}",
            f"protein_name:{protein_id}",
            f"gene_exact:{protein_id}",
            protein_id
        ]
        
        for query in search_strategies:
            try:
                url = f"{self.uniprot_base_url}/uniprotkb/search"
                
                # Handle different query types properly
                if query.startswith('accession:'):
                    # For accession numbers, use exact match
                    search_query = f"accession:{protein_id}"
                elif query.startswith('gene:'):
                    # For gene names, use gene field
                    search_query = f"gene:{protein_id}"
                elif query.startswith('protein_name:'):
                    # For protein names, use protein name field
                    search_query = f"protein_name:{protein_id}"
                elif query.startswith('gene_exact:'):
                    # For exact gene match
                    search_query = f"gene_exact:{protein_id}"
                else:
                    # For general search
                    search_query = protein_id
                
                params = {
                    'query': f"{search_query} AND reviewed:true",
                    'format': 'json',
                    'size': 1
                }
                
                response = self._make_request(url, params)
                
                if response and 'results' in response and response['results']:
                    return response['results'][0]
                    
            except Exception as e:
                logger.debug(f"Search strategy '{query}' failed: {e}")
                continue
        
        # Final fallback: try without reviewed filter
        try:
            url = f"{self.uniprot_base_url}/uniprotkb/search"
            params = {
                'query': protein_id,
                'format': 'json',
                'size': 1
            }
            
            response = self._make_request(url, params)
            
            if response and 'results' in response and response['results']:
                return response['results'][0]
                
        except Exception as e:
            logger.debug(f"Final fallback search failed: {e}")
        
        return None
    
    def _extract_function_info(self, protein_data: Dict) -> str:
        """
        Extract function information from UniProt data
        
        Args:
            protein_data: UniProt entry data
            
        Returns:
            Function description string
        """
        function_parts = []
        
        # Get function from comments
        comments = protein_data.get('comments', [])
        for comment in comments:
            if comment.get('commentType') == 'FUNCTION':
                texts = comment.get('texts', [])
                for text in texts:
                    if 'value' in text:
                        function_parts.append(text['value'])
        
        # Get catalytic activity
        for comment in comments:
            if comment.get('commentType') == 'CATALYTIC_ACTIVITY':
                reaction = comment.get('reaction', {})
                if 'name' in reaction:
                    function_parts.append(f"Catalytic activity: {reaction['name']}")
        
        # Get pathway information
        for comment in comments:
            if comment.get('commentType') == 'PATHWAY':
                texts = comment.get('texts', [])
                for text in texts:
                    if 'value' in text:
                        function_parts.append(f"Pathway: {text['value']}")
        
        return '; '.join(function_parts) if function_parts else ''
    
    def _calculate_druggability(self, protein_data: Dict) -> Dict:
        """
        Calculate druggability score based on various indicators
        
        Args:
            protein_data: UniProt entry data
            
        Returns:
            Dictionary with druggability score and indicators
        """
        score = 0.0
        indicators = []
        known_drugs = []
        binding_sites = []
        
        # Check for known drugs in cross-references
        xrefs = protein_data.get('uniProtKBCrossReferences', [])
        for xref in xrefs:
            database = xref.get('database', '')
            if database in ['DrugBank', 'ChEMBL', 'BindingDB']:
                score += 0.3
                indicators.append(f"Listed in {database}")
                if 'properties' in xref:
                    for prop in xref['properties']:
                        if prop.get('key') == 'GeneName':
                            known_drugs.append(prop.get('value', ''))
        
        # Check for binding sites
        features = protein_data.get('features', [])
        for feature in features:
            feature_type = feature.get('type', '')
            if feature_type in ['BINDING', 'ACT_SITE', 'SITE']:
                score += 0.1
                binding_sites.append({
                    'type': feature_type,
                    'description': feature.get('description', ''),
                    'location': feature.get('location', {})
                })
        
        # Check for druggability indicators in function
        function_text = self._extract_function_info(protein_data).lower()
        for indicator in self.drugbank_indicators:
            if indicator in function_text:
                score += 0.1
                indicators.append(f"Function mentions {indicator}")
        
        # Check for transmembrane regions (good drug targets)
        for feature in features:
            if feature.get('type') == 'TRANSMEM':
                score += 0.2
                indicators.append("Has transmembrane regions")
                break
        
        # Check for signal peptides (secreted proteins)
        for feature in features:
            if feature.get('type') == 'SIGNAL':
                score += 0.1
                indicators.append("Has signal peptide")
                break
        
        # Check keywords for druggability
        keywords = protein_data.get('keywords', [])
        druggable_keywords = [
            'receptor', 'enzyme', 'kinase', 'phosphatase', 'protease',
            'membrane', 'channel', 'transporter', 'hormone', 'cytokine'
        ]
        
        for keyword in keywords:
            keyword_value = keyword.get('value', '').lower()
            for dk in druggable_keywords:
                if dk in keyword_value:
                    score += 0.1
                    indicators.append(f"Keyword: {keyword.get('value', '')}")
                    break
        
        # Normalize score to 0-1 range
        score = min(score, 1.0)
        
        return {
            'score': score,
            'indicators': list(set(indicators)),
            'known_drugs': known_drugs,
            'binding_sites': binding_sites
        }
    
    def _get_protein_name(self, protein_data: Dict) -> str:
        """Get protein name from UniProt data"""
        protein_desc = protein_data.get('proteinDescription', {})
        recommended_name = protein_desc.get('recommendedName', {})
        
        if 'fullName' in recommended_name:
            return recommended_name['fullName'].get('value', '')
        
        # Try alternative names
        alternative_names = protein_desc.get('alternativeNames', [])
        for alt_name in alternative_names:
            if 'fullName' in alt_name:
                return alt_name['fullName'].get('value', '')
        
        return ''
    
    def _get_keywords(self, protein_data: Dict) -> List[str]:
        """Get keywords from UniProt data"""
        keywords = protein_data.get('keywords', [])
        return [kw.get('value', '') for kw in keywords]
    
    def _get_associated_diseases(self, protein_data: Dict) -> List[str]:
        """Get diseases associated with the protein"""
        diseases = []
        comments = protein_data.get('comments', [])
        
        for comment in comments:
            if comment.get('commentType') == 'DISEASE':
                disease_info = comment.get('disease', {})
                if 'diseaseId' in disease_info:
                    diseases.append(disease_info['diseaseId'])
        
        return diseases
    
    def _get_subcellular_location(self, protein_data: Dict) -> List[str]:
        """Get subcellular location information"""
        locations = []
        comments = protein_data.get('comments', [])
        
        for comment in comments:
            if comment.get('commentType') == 'SUBCELLULAR_LOCATION':
                subcellular_locations = comment.get('subcellularLocations', [])
                for loc in subcellular_locations:
                    location_info = loc.get('location', {})
                    if 'value' in location_info:
                        locations.append(location_info['value'])
        
        return locations
    
    def batch_analyze_proteins(self, protein_ids: List[str]) -> List[Dict]:
        """
        Analyze multiple proteins in batch
        
        Args:
            protein_ids: List of protein identifiers
            
        Returns:
            List of protein analysis results
        """
        results = []
        
        for protein_id in protein_ids:
            try:
                result = self.get_protein_function_and_druggability(protein_id)
                results.append(result)
                logger.info(f"Analyzed protein: {protein_id}")
                
            except Exception as e:
                logger.error(f"Error analyzing protein {protein_id}: {e}")
                results.append({
                    'protein_id': protein_id,
                    'error': str(e)
                })
        
        return results
    
    def get_protein_interactions_partners(self, uniprot_id: str) -> List[str]:
        """
        Get interaction partners for a protein from UniProt
        
        Args:
            uniprot_id: UniProt accession ID
            
        Returns:
            List of interaction partner UniProt IDs
        """
        partners = []
        
        try:
            # Get protein data
            url = f"{self.uniprot_base_url}/uniprotkb/{uniprot_id}"
            params = {'format': 'json'}
            
            response = self._make_request(url, params)
            
            if response:
                comments = response.get('comments', [])
                for comment in comments:
                    if comment.get('commentType') == 'INTERACTION':
                        interactions = comment.get('interactions', [])
                        for interaction in interactions:
                            interactant = interaction.get('interactantTwo', {})
                            if 'uniProtKBAccession' in interactant:
                                partners.append(interactant['uniProtKBAccession'])
                                
        except Exception as e:
            logger.error(f"Error getting interaction partners for {uniprot_id}: {e}")
        
        return partners
    
    def _get_fallback_protein_data(self, protein_id: str) -> Dict:
        """
        Provide fallback data for proteins when UniProt API fails
        
        Args:
            protein_id: Protein identifier
            
        Returns:
            Fallback protein data
        """
        # Common cancer-related proteins with known functions
        cancer_proteins = {
            'TP53': {
                'name': 'Cellular tumor antigen p53',
                'function': 'Tumor suppressor protein that regulates cell cycle and apoptosis',
                'druggability_score': 0.8,
                'indicators': ['Tumor suppressor', 'Cell cycle regulator', 'Apoptosis regulator']
            },
            'BRCA1': {
                'name': 'Breast cancer type 1 susceptibility protein',
                'function': 'Tumor suppressor involved in DNA repair and transcription regulation',
                'druggability_score': 0.6,
                'indicators': ['DNA repair', 'Tumor suppressor', 'Transcription regulator']
            },
            'EGFR': {
                'name': 'Epidermal growth factor receptor',
                'function': 'Receptor tyrosine kinase involved in cell growth and differentiation',
                'druggability_score': 0.9,
                'indicators': ['Receptor tyrosine kinase', 'Cell growth regulator', 'Drug target']
            },
            'MYC': {
                'name': 'Myc proto-oncogene protein',
                'function': 'Transcription factor involved in cell proliferation and apoptosis',
                'druggability_score': 0.7,
                'indicators': ['Transcription factor', 'Cell proliferation', 'Oncogene']
            },
            'RB1': {
                'name': 'Retinoblastoma-associated protein',
                'function': 'Tumor suppressor that regulates cell cycle progression',
                'druggability_score': 0.5,
                'indicators': ['Tumor suppressor', 'Cell cycle regulator']
            }
        }
        
        # Extract gene name from protein_id
        gene_name = protein_id
        if ':' in protein_id:
            gene_name = protein_id.split(':', 1)[1]
        elif 'gene:' in protein_id:
            gene_name = protein_id.replace('gene:', '')
        
        # Check if we have fallback data for this protein
        if gene_name in cancer_proteins:
            data = cancer_proteins[gene_name]
            return {
                'protein_id': protein_id,
                'uniprot_id': '',
                'protein_name': data['name'],
                'function': data['function'],
                'druggability_score': data['druggability_score'],
                'druggability_indicators': data['indicators'],
                'known_drugs': [],
                'binding_sites': [],
                'keywords': [],
                'diseases': ['Cancer'],
                'subcellular_location': ['Nucleus'],
                'error': 'Using fallback data - UniProt API unavailable'
            }
        else:
            # Generic fallback for unknown proteins
            return {
                'protein_id': protein_id,
                'uniprot_id': '',
                'protein_name': f'Protein {gene_name}',
                'function': 'Function not available',
                'druggability_score': 0.3,
                'druggability_indicators': ['Unknown function'],
                'known_drugs': [],
                'binding_sites': [],
                'keywords': [],
                'diseases': [],
                'subcellular_location': [],
                'error': 'Protein not found in UniProt - using generic data'
            }

# Example usage and testing
if __name__ == "__main__":
    # Test the protein analyzer
    analyzer = ProteinAnalyzer()
    
    # Test with some protein IDs
    test_proteins = ["TP53", "EGFR", "BRCA1", "P53_HUMAN"]
    
    for protein_id in test_proteins:
        print(f"Testing protein analysis for: {protein_id}")
        result = analyzer.get_protein_function_and_druggability(protein_id)
        
        if result.get('error'):
            print(f"Error: {result['error']}")
        else:
            print(f"UniProt ID: {result['uniprot_id']}")
            print(f"Name: {result['protein_name']}")
            print(f"Druggability Score: {result['druggability_score']:.2f}")
            print(f"Indicators: {result['druggability_indicators']}")
            print(f"Function: {result['function'][:100]}...")
        print("-" * 50)
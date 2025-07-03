import os
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict
from dataclasses import dataclass
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import requests
from urllib.parse import quote
import re
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ProteinTarget:
    """Data class for protein target information"""
    name: str
    pdb_id: str
    description: str
    function: str
    disease_relevance: str
    confidence_score: float
    sources: List[str]

class AgentState(TypedDict):
    """State management for the agent"""
    messages: List[Any]
    research_query: str
    disease_context: str
    found_targets: List[ProteinTarget]
    search_results: List[Dict]
    analysis_complete: bool
    error_message: Optional[str]

class ProteinTargetAgent:
    """Production-ready protein target research agent using LangGraph"""
    
    def __init__(self, openai_api_key: str, tavily_api_key: str = None):
        self.openai_api_key = openai_api_key
        self.tavily_api_key = tavily_api_key
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,
            api_key=openai_api_key
        )
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("query_analyzer", self._analyze_query)
        workflow.add_node("web_search", self._web_search)
        workflow.add_node("pdb_search", self._pdb_search)
        workflow.add_node("uniprot_search", self._uniprot_search)
        workflow.add_node("target_analyzer", self._analyze_targets)
        workflow.add_node("result_formatter", self._format_results)
        
        # Add edges
        workflow.add_edge(START, "query_analyzer")
        workflow.add_edge("query_analyzer", "web_search")
        workflow.add_edge("web_search", "pdb_search")
        workflow.add_edge("pdb_search", "uniprot_search")
        workflow.add_edge("uniprot_search", "target_analyzer")
        workflow.add_edge("target_analyzer", "result_formatter")
        workflow.add_edge("result_formatter", END)
        
        return workflow.compile()
    
    @tool
    def tavily_search(self, query: str) -> Dict:
        """Search using Tavily API for molecular biology information"""
        if not self.tavily_api_key:
            return {"error": "Tavily API key not provided"}
        
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_api_key,
                "query": query,
                "search_depth": "advanced",
                "include_domains": [
                    "pubmed.ncbi.nlm.nih.gov",
                    "www.rcsb.org",
                    "www.uniprot.org",
                    "www.ncbi.nlm.nih.gov",
                    "www.nature.com",
                    "www.science.org"
                ],
                "max_results": 10
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Tavily search error: {e}")
            return {"error": str(e)}
    
    @tool
    def pdb_api_search(self, protein_name: str) -> Dict:
        """Search PDB database for protein structures"""
        try:
            # PDB REST API search
            search_url = "https://search.rcsb.org/rcsbsearch/v2/query"
            query_data = {
                "query": {
                    "type": "terminal",
                    "service": "full_text",
                    "parameters": {
                        "value": protein_name
                    }
                },
                "request_options": {
                    "results_content_type": ["experimental"],
                    "sort": [{"sort_by": "score", "direction": "desc"}]
                },
                "return_type": "entry"
            }
            
            response = requests.post(search_url, json=query_data, timeout=30)
            response.raise_for_status()
            
            results = response.json()
            pdb_entries = []
            
            for result in results.get('result_set', [])[:5]:  # Limit to top 5
                pdb_id = result.get('identifier')
                if pdb_id:
                    # Get detailed information
                    detail_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
                    detail_response = requests.get(detail_url, timeout=15)
                    
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        pdb_entries.append({
                            'pdb_id': pdb_id,
                            'title': detail_data.get('struct', {}).get('title', ''),
                            'description': detail_data.get('struct', {}).get('pdbx_descriptor', ''),
                            'resolution': detail_data.get('refine', [{}])[0].get('ls_d_res_high'),
                            'method': detail_data.get('exptl', [{}])[0].get('method')
                        })
            
            return {"pdb_entries": pdb_entries}
            
        except Exception as e:
            logger.error(f"PDB search error: {e}")
            return {"error": str(e)}
    
    @tool
    def uniprot_search(self, protein_name: str) -> Dict:
        """Search UniProt database for protein information"""
        try:
            # UniProt REST API
            url = "https://rest.uniprot.org/uniprotkb/search"
            params = {
                "query": f"protein_name:{protein_name} AND reviewed:true",
                "format": "json",
                "size": 5
            }
            
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            uniprot_entries = []
            
            for entry in data.get('results', []):
                uniprot_entries.append({
                    'accession': entry.get('primaryAccession'),
                    'name': entry.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', ''),
                    'organism': entry.get('organism', {}).get('scientificName', ''),
                    'function': entry.get('comments', [{}])[0].get('texts', [{}])[0].get('value', ''),
                    'diseases': [disease.get('disease', {}).get('diseaseId') for disease in entry.get('comments', []) if disease.get('commentType') == 'DISEASE'],
                    'keywords': [kw.get('value') for kw in entry.get('keywords', [])]
                })
            
            return {"uniprot_entries": uniprot_entries}
            
        except Exception as e:
            logger.error(f"UniProt search error: {e}")
            return {"error": str(e)}
    
    async def _analyze_query(self, state: AgentState) -> AgentState:
        """Analyze the input query to extract disease context and research focus"""
        try:
            messages = state.get("messages", [])
            if not messages:
                return state
            
            last_message = messages[-1].content if messages else ""
            
            analysis_prompt = f"""
            Analyze this protein research query and extract:
            1. Disease or condition context
            2. Specific protein families or pathways mentioned
            3. Research focus (therapeutic targets, biomarkers, etc.)
            
            Query: {last_message}
            
            Provide a structured analysis focusing on molecular targets.
            """
            
            response = await self.llm.ainvoke([SystemMessage(content=analysis_prompt)])
            
            # Extract disease context and set research query
            state["disease_context"] = self._extract_disease_context(last_message)
            state["research_query"] = last_message
            
            logger.info(f"Query analyzed. Disease context: {state['disease_context']}")
            return state
            
        except Exception as e:
            logger.error(f"Query analysis error: {e}")
            state["error_message"] = str(e)
            return state
    
    async def _web_search(self, state: AgentState) -> AgentState:
        """Perform web search using Tavily for protein targets"""
        try:
            query = state["research_query"]
            disease_context = state.get("disease_context", "")
            
            # Enhanced search query for protein targets
            search_query = f"{query} protein targets {disease_context} PDB structure molecular"
            
            search_results = self.tavily_search(search_query)
            
            if "error" not in search_results:
                state["search_results"] = search_results.get("results", [])
                logger.info(f"Found {len(state['search_results'])} web search results")
            else:
                logger.warning(f"Web search failed: {search_results['error']}")
                state["search_results"] = []
            
            return state
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            state["error_message"] = str(e)
            return state
    
    async def _pdb_search(self, state: AgentState) -> AgentState:
        """Search PDB database for protein structures"""
        try:
            query = state["research_query"]
            disease_context = state.get("disease_context", "")
            
            # Extract potential protein names from query
            protein_names = self._extract_protein_names(query)
            
            pdb_results = []
            for protein_name in protein_names[:3]:  # Limit to top 3 proteins
                result = self.pdb_api_search(protein_name)
                if "error" not in result:
                    pdb_results.extend(result.get("pdb_entries", []))
            
            state["pdb_results"] = pdb_results
            logger.info(f"Found {len(pdb_results)} PDB entries")
            
            return state
            
        except Exception as e:
            logger.error(f"PDB search error: {e}")
            state["error_message"] = str(e)
            return state
    
    async def _uniprot_search(self, state: AgentState) -> AgentState:
        """Search UniProt database for protein information"""
        try:
            query = state["research_query"]
            protein_names = self._extract_protein_names(query)
            
            uniprot_results = []
            for protein_name in protein_names[:3]:  # Limit to top 3 proteins
                result = self.uniprot_search(protein_name)
                if "error" not in result:
                    uniprot_results.extend(result.get("uniprot_entries", []))
            
            state["uniprot_results"] = uniprot_results
            logger.info(f"Found {len(uniprot_results)} UniProt entries")
            
            return state
            
        except Exception as e:
            logger.error(f"UniProt search error: {e}")
            state["error_message"] = str(e)
            return state
    
    async def _analyze_targets(self, state: AgentState) -> AgentState:
        """Analyze and rank protein targets based on research relevance"""
        try:
            web_results = state.get("search_results", [])
            pdb_results = state.get("pdb_results", [])
            uniprot_results = state.get("uniprot_results", [])
            disease_context = state.get("disease_context", "")
            
            # Combine all data sources
            analysis_prompt = f"""
            Based on the following research data, identify the most relevant protein targets for {disease_context}:
            
            Web Search Results: {json.dumps(web_results[:5], indent=2)}
            PDB Entries: {json.dumps(pdb_results, indent=2)}
            UniProt Entries: {json.dumps(uniprot_results, indent=2)}
            
            For each protein target, provide:
            1. Protein name
            2. PDB ID (if available)
            3. Function description
            4. Disease relevance
            5. Confidence score (0-1)
            
            Focus on well-studied, therapeutically relevant targets.
            """
            
            response = await self.llm.ainvoke([SystemMessage(content=analysis_prompt)])
            
            # Parse the response to extract protein targets
            targets = self._parse_protein_targets(response.content, pdb_results, uniprot_results)
            
            state["found_targets"] = targets
            state["analysis_complete"] = True
            
            logger.info(f"Analyzed and found {len(targets)} protein targets")
            return state
            
        except Exception as e:
            logger.error(f"Target analysis error: {e}")
            state["error_message"] = str(e)
            return state
    
    async def _format_results(self, state: AgentState) -> AgentState:
        """Format the final results for presentation"""
        try:
            targets = state.get("found_targets", [])
            disease_context = state.get("disease_context", "")
            
            if not targets:
                formatted_result = f"No specific protein targets found for {disease_context}. Please refine your search query."
            else:
                formatted_result = f"For {disease_context} research, I recommend these well-studied targets:\n\n"
                
                for i, target in enumerate(targets[:5], 1):  # Top 5 targets
                    formatted_result += f"• **{target.name}"
                    if target.pdb_id:
                        formatted_result += f" (PDB: {target.pdb_id})"
                    formatted_result += f"** - {target.description}\n"
                    if target.function:
                        formatted_result += f"  Function: {target.function}\n"
                    if target.disease_relevance:
                        formatted_result += f"  Disease Relevance: {target.disease_relevance}\n"
                    formatted_result += f"  Confidence Score: {target.confidence_score:.2f}\n\n"
            
            # Add the formatted result as an AI message
            state["messages"].append(AIMessage(content=formatted_result))
            
            return state
            
        except Exception as e:
            logger.error(f"Result formatting error: {e}")
            state["error_message"] = str(e)
            return state
    
    def _extract_disease_context(self, query: str) -> str:
        """Extract disease context from query"""
        disease_keywords = [
            "cancer", "tumor", "carcinoma", "leukemia", "lymphoma",
            "diabetes", "alzheimer", "parkinson", "huntington",
            "cardiovascular", "heart disease", "hypertension",
            "inflammation", "autoimmune", "arthritis"
        ]
        
        query_lower = query.lower()
        for keyword in disease_keywords:
            if keyword in query_lower:
                return keyword
        
        return "disease"
    
    def _extract_protein_names(self, query: str) -> List[str]:
        """Extract potential protein names from query"""
        # Common protein name patterns
        protein_patterns = [
            r'\b[A-Z]+\d+\b',  # e.g., TP53, EGFR
            r'\b[A-Z][a-z]+-\d+\b',  # e.g., Bcl-2
            r'\b[A-Z]{2,}\b',  # e.g., BRCA, KRAS
        ]
        
        extracted_names = []
        for pattern in protein_patterns:
            matches = re.findall(pattern, query)
            extracted_names.extend(matches)
        
        # Add common aliases
        common_proteins = {
            "p53": "TP53",
            "egfr": "EGFR",
            "bcl2": "BCL2",
            "brca": "BRCA1",
            "kras": "KRAS"
        }
        
        query_lower = query.lower()
        for alias, official in common_proteins.items():
            if alias in query_lower:
                extracted_names.append(official)
        
        return list(set(extracted_names)) if extracted_names else ["protein"]
    
    def _parse_protein_targets(self, llm_response: str, pdb_results: List, uniprot_results: List) -> List[ProteinTarget]:
        """Parse LLM response to extract protein targets"""
        targets = []
        
        # Simple parsing - in production, you'd want more sophisticated parsing
        lines = llm_response.split('\n')
        current_target = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('•') or line.startswith('-'):
                # New target
                if current_target:
                    targets.append(current_target)
                
                # Extract name and PDB ID
                name_match = re.search(r'\*\*([^*]+)\*\*', line)
                pdb_match = re.search(r'PDB:\s*([A-Z0-9]+)', line)
                
                if name_match:
                    name = name_match.group(1).strip()
                    pdb_id = pdb_match.group(1) if pdb_match else ""
                    description = line.split('**')[-1].strip(' -')
                    
                    current_target = ProteinTarget(
                        name=name,
                        pdb_id=pdb_id,
                        description=description,
                        function="",
                        disease_relevance="",
                        confidence_score=0.8,  # Default score
                        sources=[]
                    )
        
        if current_target:
            targets.append(current_target)
        
        return targets
    
    async def research_protein_targets(self, query: str) -> Dict:
        """Main method to research protein targets"""
        try:
            initial_state = AgentState(
                messages=[HumanMessage(content=query)],
                research_query="",
                disease_context="",
                found_targets=[],
                search_results=[],
                analysis_complete=False,
                error_message=None
            )
            
            # Run the graph
            result = await self.graph.ainvoke(initial_state)
            
            return {
                "success": True,
                "targets": result.get("found_targets", []),
                "disease_context": result.get("disease_context", ""),
                "analysis_complete": result.get("analysis_complete", False),
                "error": result.get("error_message")
            }
            
        except Exception as e:
            logger.error(f"Research error: {e}")
            return {
                "success": False,
                "error": str(e),
                "targets": [],
                "disease_context": "",
                "analysis_complete": False
            }

# Example usage and testing
async def main():
    """Example usage of the protein target research agent"""
    
    # Initialize the agent
    agent = ProteinTargetAgent(
        openai_api_key="your-openai-api-key",
        tavily_api_key="your-tavily-api-key"  # Optional
    )
    
    # Example research queries
    test_queries = [
        "Find protein targets for cancer therapy",
        "What are the key protein targets for Alzheimer's disease?",
        "Identify druggable targets for cardiovascular disease",
        "Find structural proteins involved in cell division for cancer research"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Research Query: {query}")
        print(f"{'='*60}")
        
        result = await agent.research_protein_targets(query)
        
        if result["success"]:
            print(f"Disease Context: {result['disease_context']}")
            print(f"Found {len(result['targets'])} targets:")
            
            for target in result['targets']:
                print(f"  • {target.name} (PDB: {target.pdb_id})")
                print(f"    {target.description}")
                print(f"    Confidence: {target.confidence_score:.2f}")
        else:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main())

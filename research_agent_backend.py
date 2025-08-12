import os
import asyncio
import logging
from typing import List, Dict, Any, Optional, Annotated
from datetime import datetime
from dataclasses import dataclass, asdict
import json

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# LangGraph and LangChain imports
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Pydantic models for API
class ResearchRequest(BaseModel):
    query: str = Field(..., description="The research query")
    max_results: int = Field(default=5, description="Maximum number of search results")
    search_depth: str = Field(default="advanced", description="Search depth: basic or advanced")
    focus_areas: List[str] = Field(default=[], description="Specific areas to focus on")

class ResearchResponse(BaseModel):
    id: str
    query: str
    summary: str
    key_findings: List[str]
    recommendations: List[str]
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: datetime

class ResearchStatus(BaseModel):
    id: str
    status: str
    progress: float
    current_step: str
    message: str

# Research Agent State
@dataclass
class ResearchState:
    query: str
    search_results: List[Dict[str, Any]] = None
    analysis: str = ""
    key_findings: List[str] = None
    recommendations: List[str] = None
    sources: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    current_step: str = "initialized"
    progress: float = 0.0

# Initialize tools
@tool
def tavily_search_cybersecurity(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search for cybersecurity-related information using Tavily API.
    
    Args:
        query: The search query focused on cybersecurity topics
        max_results: Maximum number of results to return
    
    Returns:
        List of search results with title, content, url, and relevance score
    """
    try:
        # Initialize Tavily search tool
        search_tool = TavilySearchResults(
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=False,
            include_images=False
        )
        
        # Add cybersecurity context to query
        enhanced_query = f"cybersecurity {query}"
        results = search_tool.invoke(enhanced_query)
        
        # Process and filter results for cybersecurity relevance
        processed_results = []
        for result in results:
            if isinstance(result, dict):
                processed_results.append({
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                    "score": result.get("score", 0.0),
                    "published_date": result.get("published_date", ""),
                })
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Error in Tavily search: {str(e)}")
        return []

# Research Agent Class
class CybersecurityResearchAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0.1,
            api_key=OPENAI_API_KEY
        )
        
        # Initialize tools
        self.tools = [tavily_search_cybersecurity]
        self.tool_executor = ToolExecutor(self.tools)
        
        # Build the research workflow graph
        self.workflow = self._build_workflow()
        
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for research"""
        
        # Define the graph
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("search", self.search_node)
        workflow.add_node("analyze", self.analyze_node)
        workflow.add_node("synthesize", self.synthesize_node)
        workflow.add_node("finalize", self.finalize_node)
        
        # Define the flow
        workflow.set_entry_point("search")
        workflow.add_edge("search", "analyze")
        workflow.add_edge("analyze", "synthesize")
        workflow.add_edge("synthesize", "finalize")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def search_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Search for relevant information"""
        logger.info(f"Starting search for: {state['query']}")
        
        try:
            # Update progress
            state["current_step"] = "Searching for relevant information"
            state["progress"] = 0.25
            
            # Perform search
            search_results = tavily_search_cybersecurity.invoke({
                "query": state["query"],
                "max_results": 8
            })
            
            state["search_results"] = search_results
            logger.info(f"Found {len(search_results)} search results")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in search node: {str(e)}")
            state["search_results"] = []
            return state
    
    async def analyze_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the search results"""
        logger.info("Analyzing search results")
        
        try:
            state["current_step"] = "Analyzing information"
            state["progress"] = 0.5
            
            if not state.get("search_results"):
                state["analysis"] = "No search results to analyze."
                return state
            
            # Prepare content for analysis
            content_summary = "\n\n".join([
                f"Title: {result['title']}\nContent: {result['content'][:500]}..."
                for result in state["search_results"][:5]
            ])
            
            analysis_prompt = f"""
            As a cybersecurity expert, analyze the following search results for the query: "{state['query']}"
            
            Search Results:
            {content_summary}
            
            Provide a comprehensive analysis focusing on:
            1. Key security implications
            2. Current threat landscape
            3. Best practices and recommendations
            4. Emerging trends and technologies
            5. Compliance and regulatory considerations
            
            Analysis:
            """
            
            messages = [
                SystemMessage(content="You are a senior cybersecurity analyst with expertise in threat intelligence, risk assessment, and security architecture."),
                HumanMessage(content=analysis_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            state["analysis"] = response.content
            
            return state
            
        except Exception as e:
            logger.error(f"Error in analyze node: {str(e)}")
            state["analysis"] = "Error occurred during analysis."
            return state
    
    async def synthesize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize key findings and recommendations"""
        logger.info("Synthesizing findings and recommendations")
        
        try:
            state["current_step"] = "Synthesizing key insights"
            state["progress"] = 0.75
            
            synthesis_prompt = f"""
            Based on the following analysis of cybersecurity research for: "{state['query']}"
            
            Analysis:
            {state.get('analysis', '')}
            
            Extract and organize the information into:
            
            1. KEY FINDINGS (3-5 bullet points of the most critical insights)
            2. ACTIONABLE RECOMMENDATIONS (3-5 specific, implementable recommendations)
            
            Format your response as JSON:
            {{
                "key_findings": ["finding 1", "finding 2", ...],
                "recommendations": ["recommendation 1", "recommendation 2", ...]
            }}
            """
            
            messages = [
                SystemMessage(content="You are a cybersecurity consultant tasked with extracting actionable insights from research."),
                HumanMessage(content=synthesis_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            try:
                synthesis_data = json.loads(response.content)
                state["key_findings"] = synthesis_data.get("key_findings", [])
                state["recommendations"] = synthesis_data.get("recommendations", [])
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                state["key_findings"] = ["Analysis completed - detailed findings available in full analysis"]
                state["recommendations"] = ["Review the complete analysis for specific recommendations"]
            
            return state
            
        except Exception as e:
            logger.error(f"Error in synthesize node: {str(e)}")
            state["key_findings"] = []
            state["recommendations"] = []
            return state
    
    async def finalize_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finalize the research results"""
        logger.info("Finalizing research results")
        
        try:
            state["current_step"] = "Finalizing results"
            state["progress"] = 1.0
            
            # Process sources
            sources = []
            for result in state.get("search_results", []):
                if result.get("url"):
                    sources.append({
                        "title": result.get("title", "Unknown Title"),
                        "url": result.get("url"),
                        "snippet": result.get("content", "")[:200] + "...",
                        "relevance_score": result.get("score", 0.0)
                    })
            
            state["sources"] = sources
            
            # Add metadata
            state["metadata"] = {
                "total_sources": len(sources),
                "search_query": state["query"],
                "research_completed_at": datetime.utcnow().isoformat(),
                "analysis_length": len(state.get("analysis", "")),
                "findings_count": len(state.get("key_findings", [])),
                "recommendations_count": len(state.get("recommendations", []))
            }
            
            state["current_step"] = "Complete"
            logger.info("Research completed successfully")
            
            return state
            
        except Exception as e:
            logger.error(f"Error in finalize node: {str(e)}")
            return state
    
    async def conduct_research(self, query: str, research_id: str) -> Dict[str, Any]:
        """Conduct complete research using the workflow"""
        
        # Initialize state
        initial_state = {
            "id": research_id,
            "query": query,
            "search_results": [],
            "analysis": "",
            "key_findings": [],
            "recommendations": [],
            "sources": [],
            "metadata": {},
            "current_step": "Starting research",
            "progress": 0.0
        }
        
        try:
            # Run the workflow
            final_state = await self.workflow.ainvoke(initial_state)
            return final_state
            
        except Exception as e:
            logger.error(f"Error conducting research: {str(e)}")
            return {
                **initial_state,
                "current_step": "Error",
                "progress": 0.0,
                "analysis": f"Research failed: {str(e)}"
            }

# FastAPI Application
app = FastAPI(
    title="Cybersecurity Research Agent API",
    description="LangGraph-powered research agent for cybersecurity topics",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global research agent instance
research_agent = CybersecurityResearchAgent()

# In-memory storage for research sessions (use Redis/DB in production)
research_sessions: Dict[str, Dict[str, Any]] = {}

@app.post("/api/research/start", response_model=ResearchStatus)
async def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    """Start a new research session"""
    
    research_id = f"research_{int(datetime.utcnow().timestamp() * 1000)}"
    
    # Initialize research session
    research_sessions[research_id] = {
        "id": research_id,
        "status": "started",
        "progress": 0.0,
        "current_step": "Initializing",
        "query": request.query,
        "created_at": datetime.utcnow(),
        "result": None
    }
    
    # Start research in background
    background_tasks.add_task(
        execute_research,
        research_id,
        request.query
    )
    
    return ResearchStatus(
        id=research_id,
        status="started",
        progress=0.0,
        current_step="Research initiated",
        message="Research has been started and is running in the background"
    )

async def execute_research(research_id: str, query: str):
    """Execute research in background"""
    try:
        research_sessions[research_id]["status"] = "running"
        
        # Conduct research
        result = await research_agent.conduct_research(query, research_id)
        
        # Store result
        research_sessions[research_id].update({
            "status": "completed",
            "progress": 1.0,
            "current_step": "Complete",
            "result": result,
            "completed_at": datetime.utcnow()
        })
        
    except Exception as e:
        logger.error(f"Research execution failed: {str(e)}")
        research_sessions[research_id].update({
            "status": "failed",
            "current_step": "Error",
            "message": str(e)
        })

@app.get("/api/research/status/{research_id}", response_model=ResearchStatus)
async def get_research_status(research_id: str):
    """Get research status"""
    
    if research_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Research session not found")
    
    session = research_sessions[research_id]
    
    return ResearchStatus(
        id=research_id,
        status=session["status"],
        progress=session.get("progress", 0.0),
        current_step=session.get("current_step", "Unknown"),
        message=session.get("message", "")
    )

@app.get("/api/research/result/{research_id}", response_model=ResearchResponse)
async def get_research_result(research_id: str):
    """Get research results"""
    
    if research_id not in research_sessions:
        raise HTTPException(status_code=404, detail="Research session not found")
    
    session = research_sessions[research_id]
    
    if session["status"] != "completed":
        raise HTTPException(status_code=400, detail="Research not completed yet")
    
    result = session["result"]
    
    return ResearchResponse(
        id=research_id,
        query=result["query"],
        summary=result.get("analysis", ""),
        key_findings=result.get("key_findings", []),
        recommendations=result.get("recommendations", []),
        sources=result.get("sources", []),
        metadata=result.get("metadata", {}),
        timestamp=session.get("completed_at", datetime.utcnow())
    )

@app.websocket("/api/research/ws/{research_id}")
async def research_websocket(websocket: WebSocket, research_id: str):
    """WebSocket endpoint for real-time research updates"""
    await websocket.accept()
    
    try:
        while True:
            if research_id in research_sessions:
                session = research_sessions[research_id]
                
                status_update = {
                    "id": research_id,
                    "status": session["status"],
                    "progress": session.get("progress", 0.0),
                    "current_step": session.get("current_step", "Unknown"),
                    "message": session.get("message", "")
                }
                
                await websocket.send_json(status_update)
                
                # If completed or failed, send final message and close
                if session["status"] in ["completed", "failed"]:
                    break
                    
            await asyncio.sleep(1)  # Update every second
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for research {research_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")

@app.get("/api/research/sessions")
async def list_research_sessions():
    """List all research sessions"""
    return {
        "sessions": [
            {
                "id": session_id,
                "query": session["query"],
                "status": session["status"],
                "created_at": session["created_at"],
                "progress": session.get("progress", 0.0)
            }
            for session_id, session in research_sessions.items()
        ]
    }

@app.delete("/api/research/session/{research_id}")
async def delete_research_session(research_id: str):
    """Delete a research session"""
    if research_id in research_sessions:
        del research_sessions[research_id]
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Research session not found")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "active_sessions": len(research_sessions)
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

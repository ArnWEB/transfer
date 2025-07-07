from langgraph.graph import StateGraph, END

from models.state import SummaryState
from core.llm_utils import generate_summary_with_llm_node

# Dummy parse_disease and call_fastapi_endpoint for illustration
# Replace with your actual implementations

def parse_disease(state: SummaryState) -> SummaryState:
    # Example: extract disease name from user_input
    # In production, use an LLM or regex
    state["disease_name"] = state["user_input"].strip().title()
    return state

def call_fastapi_endpoint(state: SummaryState) -> SummaryState:
    # Example: call FastAPI endpoint and store response
    # In production, use requests or httpx
    # Here, we just mock a response
    state["raw_response"] = {
        "disease": state["disease_name"],
        "targets": [
            {"gene_symbol": "BRCA1", "uniprot_id": "P38398", "best_pdb": {"pdb_id": "1JNX", "organism": "Homo sapiens", "method": "X-ray Diffraction", "resolution": 2.4, "ligand_bound": True, "association_score": 0.96}},
            {"gene_symbol": "TP53", "uniprot_id": "P04637", "best_pdb": {"pdb_id": "2OCJ", "organism": "Homo sapiens", "method": "X-ray Diffraction", "resolution": 1.8, "ligand_bound": False, "association_score": 0.92}}
        ]
    }
    return state

# Build the workflow
graph = StateGraph(SummaryState)
graph.add_node("parse_disease", parse_disease)
graph.add_node("call_fastapi_endpoint", call_fastapi_endpoint)
graph.add_node("generate_summary_with_llm", generate_summary_with_llm_node)
graph.set_entry_point("parse_disease")
graph.add_edge("parse_disease", "call_fastapi_endpoint")
graph.add_edge("call_fastapi_endpoint", "generate_summary_with_llm")
graph.add_edge("generate_summary_with_llm", END)
compiled_graph = graph.compile()

def run_workflow(user_input: str) -> str:
    initial_state = {
        "user_input": user_input,
        "disease_name": None,
        "raw_response": None,
        "summary_markdown": None
    }
    # Ensure initial_state is of type SummaryState
    initial_state_typed = SummaryState(**initial_state)
    final_state = compiled_graph.invoke(initial_state_typed)
    return final_state["summary_markdown"]
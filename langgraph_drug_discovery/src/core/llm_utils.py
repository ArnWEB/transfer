import os
from langchain.prompts import PromptTemplate
from langchain_groq import ChatGroq
# from langchain.chains import LLMChain
import json
from models.state import SummaryState

os.environ["GROQ_API_KEY"] = "2TBbvIHJbXeNzRzEzRvGajgM4QOxETWhDYVkLkmLkHD1HjBxvdXqJQQJ99BFACAAAAAVUrFGAAASAZDO1uHW"

summary_prompt = PromptTemplate(
    input_variables=["json_data", "disease_name"],
    template="""
You are a domain-aware Bioinformatics AI Assistant tasked with summarizing protein target recommendations for drug discovery. 
Generate a Markdown-formatted summary suitable for scientists or researchers.

Use the following structure:

# [Disease Name] Target Recommendations

## Summary
- Total Targets: [X]
- With Experimental Structure: [Y]
- No Structure Available: [Z]

## Target-by-Target Recommendations
### GENE_SYMBOL (UNIPROT_ID)
- Best PDB ID: [PDB_LINK]
- Experimental Method: [METHOD]
- Resolution: [RESOLUTION] Å
- Organism: [ORGANISM]
- Ligand-bound: [Yes/No]
- Association Score: [SCORE]
- Rationale: [Why this target is recommended]

...

## Next Steps Suggestions
- Prioritize targets...
- Recommend pocket prediction where no ligand is bound...
- Suggest fallback options like AlphaFold if no experimental structure exists

Do not add explanations outside the requested format. Just return the summary.

Here is the JSON data:

{json_data}
"""
)

llm = ChatGroq(temperature=0, model="llama3-8b-8192")

# Node function for LangGraph: takes and returns dict state
# (not dataclass), as per new LangGraph docs

def generate_summary_with_llm_node(state: SummaryState) -> SummaryState:
    try:
        json_str = json.dumps(state["raw_response"], indent=2)
        prompt = summary_prompt.format(json_data=json_str, disease_name=state["disease_name"])
        # Use .invoke for LLM call as per new docs
        result = llm.invoke([{"role": "user", "content": prompt}])
        # Handle case where result.content may be a list (e.g., OpenAI function calling)
        if hasattr(result, "content"):
            summary = result.content
            if isinstance(summary, list):
                # Join list elements if they are strings or dicts
                summary = "\n".join(
                    s if isinstance(s, str) else json.dumps(s) for s in summary
                )
        else:
            summary = str(result)
        # Only call strip if summary is a string
        state["summary_markdown"] = summary.strip() if isinstance(summary, str) else summary
    except Exception as e:
        state["summary_markdown"] = f"❌ Failed to generate summary with LLM: {str(e)}"
    return state 
from fastapi import FastAPI
from pydantic import BaseModel
from core.langgraph_workflow import run_workflow

app = FastAPI()

class SummarizeRequest(BaseModel):
    user_input: str

@app.post("/summarize")
def summarize(req: SummarizeRequest):
    markdown = run_workflow(req.user_input)
    return {"summary_markdown": markdown} 
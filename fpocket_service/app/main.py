from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fpocket_utils import download_pdb, run_fpocket, cache_pockets, get_cached_pockets

app = FastAPI()

class PocketRequest(BaseModel):
    pdb_id: str

@app.post("/analyze_pocket")
def analyze_pocket(req: PocketRequest):
    pdb_id = req.pdb_id.upper()
    # Check cache first
    cached = get_cached_pockets(pdb_id)
    if cached:
        return {"pdb_id": pdb_id, "pockets": cached}
    try:
        pdb_file = download_pdb(pdb_id)
        pockets = run_fpocket(pdb_file)
        if pockets:
            pockets.sort(key=lambda x: x.get('druggability_score', 0), reverse=True)
        cache_pockets(pdb_id, pockets)
        return {"pdb_id": pdb_id, "pockets": pockets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
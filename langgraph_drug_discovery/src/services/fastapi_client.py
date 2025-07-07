import requests
from ..config.settings import FASTAPI_BASE_URL

def get_targets_with_best_pdb(disease_name: str, page_index: int = 0, page_size: int = 2):
    url = f"{FASTAPI_BASE_URL}/get_targets_with_best_pdb"
    params = {
        "disease_name": disease_name,
        "page_index": page_index,
        "page_size": page_size
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"FastAPI call failed: {response.status_code} {response.text}") 
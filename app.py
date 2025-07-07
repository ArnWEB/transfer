from fastapi import FastAPI, Query
import requests
from typing import Dict, List, Any, Union
from cache_utils import get_cached_pdbs, cache_uniprot_pdb, get_pdb_metadata_with_cache, fetch_chain_id_for_uniprot

app = FastAPI()

OPEN_TARGETS_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
OPEN_TARGETS_DISEASE_SEARCH_URL = "https://api.platform.opentargets.org/api/v4/platform/public/disease/search"

def get_pdb_metadata(pdb_id: str) -> Dict[str, Any]:
    """
    Fetches metadata for a given PDB ID from RCSB API.
    Returns dict with:
    - experimental_method
    - resolution
    - ligand_bound (True/False)
    - chain_ids
    - organism
    """
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"Failed to fetch {pdb_id}"}
    
    data = response.json()
    
    # Extract experimental method
    method = data["exptl"][0]["method"] if "exptl" in data and data["exptl"] else None

    # Extract resolution (if X-ray or cryo-EM)
    resolution = data["rcsb_entry_info"].get("resolution_combined", [None])[0]
    
    # Check ligands presence
    ligand_bound = "chem_comp" in data
    
    # Organism (if available)
    organism = data.get("rcsb_entry_container_identifiers", {}).get("ncbi_scientific_name")

    return {
        "pdb_id": pdb_id,
        "method": method,
        "resolution": resolution,
        "ligand_bound": ligand_bound,
        "organism": organism
    }

def score_pdb_structure(metadata: Dict[str, Any]) -> float:
    """
    Calculates a suitability score for docking based on metadata.
    Higher scores indicate better structures for drug discovery.
    """
    score = 0
    method = metadata.get("method", "").lower()
    resolution = metadata.get("resolution")
    
    # Experimental method scoring
    if "x-ray" in method:
        score += 2
    elif "electron microscopy" in method:
        score += 1
    
    # Resolution scoring
    if resolution:
        if resolution <= 2.5:
            score += 2
        elif resolution <= 3.0:
            score += 1

    # Ligand bound bonus
    if metadata.get("ligand_bound"):
        score += 2
    
    # Human organism bonus
    if metadata.get("organism") == "Homo sapiens":
        score += 1
    
    return score

def select_best_pdb_for_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """
    Selects the best PDB structure for a given target based on scoring.
    """
    best_pdb = None
    best_score = -1

    for pdb_id in target.get("pdb_ids", []):
        metadata = get_pdb_metadata_with_cache(pdb_id, get_pdb_metadata)
        metadata['organism'] = "Homo sapiens"
        if "error" in metadata:
            continue
        pdb_score = score_pdb_structure(metadata)
        if pdb_score > best_score:
            best_score = pdb_score
            best_pdb = metadata
    return {
        "gene_symbol": target["gene_symbol"],
        "uniprot_id": target.get("uniprot_id"),
        "best_pdb": best_pdb,
        "association_score": target["score"]
    }

def get_pdb_ids_for_targets(targets):
    """
    Enrich targets with PDB IDs from UniProt, using Redis cache for UniProt → PDB mapping.
    """
    results = []
    for target in targets:
        gene_symbol = target["target"]["approvedSymbol"]
        score = target["score"]

        # Step 1. Search UniProt for this gene symbol in human
        search_url = f"https://rest.uniprot.org/uniprotkb/search?query=gene_exact:{gene_symbol}+AND+organism_id:9606&fields=accession&format=json"
        response = requests.get(search_url)
        if response.status_code != 200:
            results.append({
                "gene_symbol": gene_symbol,
                "error": "Failed to search UniProt",
                "score": score
            })
            continue

        search_results = response.json()
        if not search_results.get("results"):
            results.append({
                "gene_symbol": gene_symbol,
                "error": "No UniProt ID found",
                "score": score
            })
            continue

        # Take first UniProt ID
        uniprot_id = search_results["results"][0]["primaryAccession"]

        # Check cache for PDB IDs
        cached_pdbs = get_cached_pdbs(uniprot_id)
        if cached_pdbs is not None:
            pdb_ids = cached_pdbs
        else:
            # Step 2. Get PDB IDs from entry
            entry_url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.json"
            entry_response = requests.get(entry_url)
            if entry_response.status_code != 200:
                results.append({
                    "gene_symbol": gene_symbol,
                    "uniprot_id": uniprot_id,
                    "error": "Failed to retrieve UniProt entry",
                    "score": score
                })
                continue

            entry_data = entry_response.json()
            pdb_ids = []
            for xref in entry_data.get("uniProtKBCrossReferences", []):
                if xref["database"] == "PDB":
                    pdb_ids.append(xref["id"])
            # Cache the result
            cache_uniprot_pdb(uniprot_id, pdb_ids)

        results.append({
            "gene_symbol": gene_symbol,
            "uniprot_id": uniprot_id,
            "pdb_ids": pdb_ids,
            "score": score
        })

    return results

@app.get("/get_targets")
def get_targets(
    disease_name: str = Query(..., description="Disease name to search, e.g. breast cancer"),
    page_index: int = Query(0, description="Page index (pagination)"),
    page_size: int = Query(10, description="Number of targets to return per page")
):
    """
    Get top targets for a given disease name using Open Targets Disease Search + GraphQL API.
    """

    # 1. Search for disease ID using GraphQL search API
    search_query = """
    query SearchQuery($queryString: String!, $size: Int!) {
      diseases: search(
        queryString: $queryString
        entityNames: ["disease"]
        page: {index: 0, size: $size}
      ) {
        hits {
          id
          entity
          object {
            ... on Disease {
              id
              name
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    """
    
    search_variables = {
        "queryString": disease_name,
        "size": 3
    }
    
    search_response = requests.post(
        OPEN_TARGETS_GRAPHQL_URL,
        json={
            "query": search_query,
            "variables": search_variables
        }
    )

    if search_response.status_code != 200:
        return {"error": f"Disease search failed with status code {search_response.status_code}"}

    search_data = search_response.json()
    print(search_data)
    
    if not search_data.get("data", {}).get("diseases", {}).get("hits"):
        return {"error": f"No disease ID found for disease name '{disease_name}'"}

    # Take the first matching disease ID
    disease_id = search_data["data"]["diseases"]["hits"][0]["id"]

    # 2. Construct GraphQL query with pagination
    query = """
    query diseaseTargets {
      disease(efoId: \"%s\") {
        id
        name
        associatedTargets(page: { index: %d, size: %d }) {
          count
          rows {
            target {
              id
              approvedSymbol
              biotype
            }
            score
          }
        }
      }
    }
    """ % (disease_id, page_index, page_size)

    # 3. Call GraphQL API
    graphql_response = requests.post(
        OPEN_TARGETS_GRAPHQL_URL,
        json={"query": query}
    )

    if graphql_response.status_code != 200:
        return {"error": f"GraphQL query failed with status code {graphql_response.status_code}"}

    data = graphql_response.json()
    return data

@app.get("/get_targets_with_pdb")
def get_targets_with_pdb(
    disease_name: str = Query(..., description="Disease name to search, e.g. breast cancer"),
    page_index: int = Query(0, description="Page index (pagination)"),
    page_size: int = Query(10, description="Number of targets to return per page")
):
    """
    Get top targets for a given disease name and enrich with PDB IDs from UniProt.
    """
    
    # First get the targets using the existing endpoint logic
    targets_response = get_targets(disease_name, page_index, page_size)
    
    # Check if there's an error in the response
    if isinstance(targets_response, dict) and "error" in targets_response:
        return targets_response
    
    # Extract targets from the response
    if not isinstance(targets_response, dict):
        return {"error": "Invalid response format from targets API"}
    
    targets_response_dict: Dict[str, Any] = targets_response
    targets = targets_response_dict.get("data", {}).get("disease", {}).get("associatedTargets", {}).get("rows", [])
    
    if not targets:
        return {"error": "No targets found for the given disease"}
    
    # Enrich targets with PDB IDs
    enriched_targets = get_pdb_ids_for_targets(targets)
    
    return {
        "disease": targets_response_dict.get("data", {}).get("disease", {}),
        "enriched_targets": enriched_targets
    }

@app.get("/get_targets_with_best_pdb")
def get_targets_with_best_pdb(
    disease_name: str = Query(..., description="Disease name to search, e.g. breast cancer"),
    page_index: int = Query(0, description="Page index (pagination)"),
    page_size: int = Query(10, description="Number of targets to return per page")
):
    """
    Get top targets for a given disease name and select the best PDB structure for each target.
    This provides the complete pipeline: Disease → Targets → Best PDB Structures for drug discovery.
    """
    
    # First get the targets with PDB IDs
    targets_response = get_targets_with_pdb(disease_name, page_index, page_size)
    
    # Check if there's an error in the response
    if isinstance(targets_response, dict) and "error" in targets_response:
        return targets_response
    
    # Extract enriched targets from the response
    if not isinstance(targets_response, dict):
        return {"error": "Invalid response format from targets API"}
    
    targets_response_dict: Dict[str, Any] = targets_response
    enriched_targets = targets_response_dict.get("enriched_targets", [])
    
    if not enriched_targets:
        return {"error": "No enriched targets found for the given disease"}
    
    # Select best PDB for each target
    final_recommendations = []
    for target in enriched_targets:
        if target.get("pdb_ids"):  # Only process targets with PDB IDs
            result = select_best_pdb_for_target(target)
            # Enrich with chain ID if best_pdb exists
            best_pdb = result.get("best_pdb")
            if best_pdb and best_pdb.get("pdb_id") and target.get("uniprot_id"):
                chain_id = fetch_chain_id_for_uniprot(best_pdb["pdb_id"], target["uniprot_id"])
                best_pdb["chain_id"] = chain_id
            final_recommendations.append(result)
        else:
            # Include targets without PDB IDs but mark them
            final_recommendations.append({
                "gene_symbol": target["gene_symbol"],
                "uniprot_id": target.get("uniprot_id"),
                "best_pdb": None,
                "association_score": target["score"],
                "note": "No PDB structures available"
            })
    
    return {
        "disease": targets_response_dict.get("disease", {}),
        "target_recommendations": final_recommendations,
        "summary": {
            "total_targets": len(enriched_targets),
            "targets_with_pdb": len([t for t in final_recommendations if t.get("best_pdb")]),
            "targets_without_pdb": len([t for t in final_recommendations if not t.get("best_pdb")])
        }
    } 
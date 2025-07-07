from cache_utils import get_cached_pdbs, cache_uniprot_pdb, get_pdb_metadata_with_cache, cache_chain_id, get_cached_chain_id
import requests

def get_pdb_metadata(pdb_id):
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"Failed to fetch {pdb_id}"}
    return response.json()

def fetch_chain_id_for_uniprot(pdb_id, uniprot_id):
    """
    Get chain ID from cache or RCSB GraphQL if not cached
    """
    chain_id = get_cached_chain_id(pdb_id, uniprot_id)
    if chain_id:
        print(f"Cache hit for chain {pdb_id} {uniprot_id}")
        return chain_id
    # If not cached, query GraphQL API
    query = """
    { entry(entry_id: \"%s\") { polymer_entities { uniprots { accession } polymer_entity_instances { asym_id } } } }""" % pdb_id
    response = requests.post("https://data.rcsb.org/graphql", json={"query": query})
    if response.status_code != 200:
        print(f"RCSB GraphQL error: {response.status_code}")
        return None
    data = response.json()
    entry = data.get('data', {}).get('entry')
    if not entry or 'polymer_entities' not in entry or not entry['polymer_entities']:
        print(f"No polymer_entities found for {pdb_id}")
        return None
    for entity in entry['polymer_entities']:
        for uniprot in entity.get('uniprots', []):
            if uniprot.get('accession') == uniprot_id:
                chains = entity.get('polymer_entity_instances', [])
                if chains:
                    chain_id = chains[0].get('asym_id')
                    if chain_id:
                        cache_chain_id(pdb_id, uniprot_id, chain_id)
                        print(f"Cached chain {pdb_id} {uniprot_id} -> {chain_id}")
                        return chain_id
    print(f"No chain found for {pdb_id} {uniprot_id}")
    return None

def fetch_organism_for_uniprot(pdb_id, uniprot_id):
    """
    Get organism scientific name for a given PDB ID and UniProt ID
    """
    entry_url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    entry_resp = requests.get(entry_url).json()

    polymer_entities = entry_resp.get('rcsb_entry_container_identifiers', {}).get('polymer_entity_ids', [])
    
    for entity_id in polymer_entities:
        # For each entity, check UniProt mapping
        entity_url = f"https://data.rcsb.org/rest/v1/core/polymer_entity/{pdb_id}/{entity_id}"
        entity_resp = requests.get(entity_url)
        if entity_resp.status_code != 200:
            continue
        entity_data = entity_resp.json()
        
        # Check uniprot mapping
        uniprots = entity_data.get('rcsb_polymer_entity_container_identifiers', {}).get('uniprots', [])
        if uniprot_id in uniprots:
            # Extract organism
            sources = entity_data.get('rcsb_entity_source_organism', [])
            if sources:
                return sources[0].get('scientific_name')
    
    return None

def fetch_pdb_metadata(pdb_id, uniprot_id=None):
    url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
    resp = requests.get(url)
    data = resp.json()

    # Extract experimental method and resolution
    exptl = data.get('exptl', [{}])[0]
    method = exptl.get('method')
    resolution = data.get('rcsb_entry_info', {}).get('resolution_combined', [None])[0]

    # Extract ligand info (bound ligands)
    ligand_bound = False
    nonpolymer_ids = data.get('rcsb_entry_container_identifiers', {}).get('nonpolymer_entity_ids')
    if nonpolymer_ids:
        ligand_bound = True

    # Extract organism name using robust UniProt mapping
    organism = None
    if uniprot_id:
        organism = fetch_organism_for_uniprot(pdb_id, uniprot_id)

    return {
        "pdb_id": pdb_id,
        "method": method,
        "resolution": resolution,
        "ligand_bound": ligand_bound,
        "organism": organism
    }

def main():
    print("Hello from transfer!")

def test_cache():
    uniprot_id = "P03905"  # Example UniProt ID
    # First, clear any existing cache for this ID
    from redis_client import get_redis_connection
    r = get_redis_connection()
    r.delete(uniprot_id)

    # Simulate fetching PDBs (normally from UniProt API)
    entry_url = f"https://rest.uniprot.org/uniprotkb/{uniprot_id}.json"
    entry_response = requests.get(entry_url)
    entry_data = entry_response.json()
    pdb_ids = [xref["id"] for xref in entry_data.get("uniProtKBCrossReferences", []) if xref["database"] == "PDB"]

    print("First call (should miss cache):")
    print(get_cached_pdbs(uniprot_id))
    cache_uniprot_pdb(uniprot_id, pdb_ids)
    print("After caching:")
    print(get_cached_pdbs(uniprot_id))
    print("Second call (should hit cache):")
    print(get_cached_pdbs(uniprot_id))

    # Test PDB metadata caching
    if pdb_ids:
        pdb_id = pdb_ids[0]
        print(f"\nTesting PDB metadata caching for {pdb_id}")
        r.delete(f"pdb:{pdb_id}")
        print("First metadata call (should miss cache):")
        meta1 = get_pdb_metadata_with_cache(pdb_id, get_pdb_metadata)
        print(meta1)
        print("Second metadata call (should hit cache):")
        meta2 = get_pdb_metadata_with_cache(pdb_id, get_pdb_metadata)
        print(meta2)

        # Test chain ID caching
        print(f"\nTesting chain ID caching for {pdb_id}, {uniprot_id}")
        r.delete(f"chain:{pdb_id}:{uniprot_id}")
        print("First chain ID call (should miss cache):")
        chain1 = fetch_chain_id_for_uniprot(pdb_id, uniprot_id)
        print(chain1)
        print("Second chain ID call (should hit cache):")
        chain2 = fetch_chain_id_for_uniprot(pdb_id, uniprot_id)
        print(chain2)

if __name__ == "__main__":
    test_cache()

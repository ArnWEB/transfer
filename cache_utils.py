import json
from redis_client import get_redis_connection
import requests

r = get_redis_connection()

def cache_uniprot_pdb(uniprot_id, pdb_list, ttl=604800):
    """
    Cache the list of PDBs for a UniProt ID
    :param uniprot_id: str
    :param pdb_list: list of PDB metadata dicts
    :param ttl: time to live in seconds (default 7 days)
    """
    print(f"[CACHE SET] {uniprot_id} -> {pdb_list}")
    r.setex(uniprot_id, ttl, json.dumps(pdb_list))

def get_cached_pdbs(uniprot_id):
    """
    Retrieve cached PDB list for UniProt ID if available
    :param uniprot_id: str
    :return: list or None
    """
    cached = r.get(uniprot_id)
    # If cached is an Awaitable, the Redis client is misconfigured (should be sync redis-py)
    if hasattr(cached, '__await__'):
        raise RuntimeError('Redis client returned an Awaitable. Ensure you are using the sync redis-py client, not aioredis or an async wrapper.')
    if cached is not None:
        print(f"[CACHE HIT] {uniprot_id}")
        if isinstance(cached, bytes):
            return json.loads(cached.decode())
        elif isinstance(cached, str):
            return json.loads(cached)
        else:
            raise TypeError(f"Unexpected cached value type: {type(cached)}")
    print(f"[CACHE MISS] {uniprot_id}")
    return None

def cache_pdb_metadata(pdb_id, metadata, ttl=604800):
    print(f"[CACHE SET] pdb:{pdb_id} -> {metadata}")
    r.setex(f"pdb:{pdb_id}", ttl, json.dumps(metadata))

def get_cached_pdb_metadata(pdb_id):
    cached = r.get(f"pdb:{pdb_id}")
    if hasattr(cached, '__await__'):
        raise RuntimeError('Redis client returned an Awaitable. Ensure you are using the sync redis-py client, not aioredis or an async wrapper.')
    if cached is not None:
        print(f"[CACHE HIT] pdb:{pdb_id}")
        if isinstance(cached, bytes):
            return json.loads(cached.decode())
        else:
            raise TypeError(f"Unexpected cached value type: {type(cached)}")
    print(f"[CACHE MISS] pdb:{pdb_id}")
    return None

# Wrapper for PDB metadata fetch with caching
def get_pdb_metadata_with_cache(pdb_id, fetch_func, ttl=604800):
    """
    Fetch PDB metadata with Redis caching.
    :param pdb_id: str
    :param fetch_func: function to fetch metadata if not cached
    :param ttl: cache TTL in seconds
    :return: dict
    """
    metadata = get_cached_pdb_metadata(pdb_id)
    if metadata:
        return metadata
    metadata = fetch_func(pdb_id)
    cache_pdb_metadata(pdb_id, metadata, ttl=ttl)
    return metadata

def cache_chain_id(pdb_id, uniprot_id, chain_id, ttl=604800):
    key = f"chain:{pdb_id}:{uniprot_id}"
    print(f"[CACHE SET] {key} -> {chain_id}")
    r.setex(key, ttl, chain_id)

def get_cached_chain_id(pdb_id, uniprot_id):
    key = f"chain:{pdb_id}:{uniprot_id}"
    cached = r.get(key)
    if hasattr(cached, '__await__'):
        raise RuntimeError('Redis client returned an Awaitable. Ensure you are using the sync redis-py client, not aioredis or an async wrapper.')
    if cached is not None:
        print(f"[CACHE HIT] {key}")
        if isinstance(cached, bytes):
            return cached.decode()
        else:
            raise TypeError(f"Unexpected cached value type: {type(cached)}")
    print(f"[CACHE MISS] {key}")
    return None

def fetch_chain_id_for_uniprot(pdb_id, uniprot_id, ttl=604800):
    """
    Get chain ID from cache or PDBe API if not cached.
    """
    chain_id = get_cached_chain_id(pdb_id, uniprot_id)
    if chain_id:
        print(f"Cache hit for chain {pdb_id} {uniprot_id}")
        return chain_id

    # Use PDBe API for mapping
    url = f"https://www.ebi.ac.uk/pdbe/api/mappings/uniprot/{pdb_id.lower()}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            print(f"PDBe API error: {resp.status_code}")
            return None
        data = resp.json()
        mappings = data.get(pdb_id.lower(), {}).get('UniProt', {})
        for up_id, info in mappings.items():
            if up_id == uniprot_id:
                for mapping in info['mappings']:
                    chain_id = mapping['chain_id']
                    cache_chain_id(pdb_id, uniprot_id, chain_id, ttl=ttl)
                    print(f"Cached chain {pdb_id} {uniprot_id} -> {chain_id}")
                    return chain_id
        print(f"No chain found for {pdb_id} {uniprot_id} in PDBe API")
        return None
    except Exception as e:
        print(f"Exception during PDBe API call: {e}")
        return None

def get_pdbs_with_organism(uniprot_id, ttl=604800):
    """
    Fetch PDB entries for a UniProt ID with organism info, using RCSB GraphQL API. Caches results in Redis.
    Returns a list of dicts with pdb_id and organism info.
    """
    cache_key = f"pdbs_with_organism:{uniprot_id}"
    cached = r.get(cache_key)
    if hasattr(cached, '__await__'):
        raise RuntimeError('Redis client returned an Awaitable. Ensure you are using the sync redis-py client, not aioredis or an async wrapper.')
    if cached:
        print(f"[CACHE HIT] {cache_key}")
        if isinstance(cached, bytes):
            return json.loads(cached.decode())
        else:
            raise TypeError(f"Unexpected cached value type: {type(cached)}")
    print(f"[CACHE MISS] {cache_key}")
    url = "https://data.rcsb.org/graphql"
    query = """
    query ($uniprotAcc: String!) {
      uniprot(uniprot_acc: $uniprotAcc) {
        pdbEntries {
          pdb_id
          entityUniprotOrganism {
            scientific_name
            common_name
            ncbi_taxonomy_id
          }
        }
      }
    }
    """
    variables = {"uniprotAcc": uniprot_id}
    try:
        response = requests.post(url, json={"query": query, "variables": variables}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            pdb_entries = data['data']['uniprot']['pdbEntries']
            # Cache result
            r.setex(cache_key, ttl, json.dumps(pdb_entries))
            return pdb_entries
        else:
            print(f"GraphQL query failed: {response.status_code} {response.text}")
            return []
    except Exception as e:
        print(f"Exception during GraphQL call: {e}")
        return []

def filter_pdbs_by_organism(pdb_entries, ncbi_taxid=9606):
    """
    Filter PDB entries by NCBI taxonomy ID (default: human).
    Returns a list of dicts with pdb_id and organism info.
    """
    return [
        {
            "pdb_id": entry["pdb_id"],
            "organism": entry["entityUniprotOrganism"]
        }
        for entry in pdb_entries
        if entry.get("entityUniprotOrganism", {}).get("ncbi_taxonomy_id") == ncbi_taxid
    ]
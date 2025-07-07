import subprocess
import os
import requests
import redis
import json

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

PDB_DIR = "/app/pdb_files"


def download_pdb(pdb_id, save_dir=PDB_DIR):
    """
    Download pdb file from RCSB
    """
    url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{pdb_id}.pdb")
    if os.path.exists(save_path):
        return save_path
    r_ = requests.get(url)
    if r_.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(r_.content)
        return save_path
    else:
        raise Exception(f"Failed to download PDB: {pdb_id}")

def run_fpocket(pdb_file_path):
    """
    Run fpocket on pdb file and parse results
    """
    pdb_basename = os.path.splitext(os.path.basename(pdb_file_path))[0]
    output_dir = os.path.join(os.path.dirname(pdb_file_path), f"{pdb_basename}_out")
    # Only run if not already run
    if not os.path.exists(output_dir):
        subprocess.run(['fpocket', '-f', pdb_file_path], check=True)
    pockets_info_path = os.path.join(output_dir, 'pockets_info.txt')
    pockets = []
    if os.path.exists(pockets_info_path):
        with open(pockets_info_path, 'r') as f:
            lines = f.readlines()
            current = {}
            for line in lines:
                if line.startswith("Pocket"):
                    if current:
                        pockets.append(current)
                        current = {}
                    current['pocket_id'] = line.split()[1]
                elif "Volume" in line:
                    current['volume'] = float(line.split()[-1])
                elif "Druggability Score" in line:
                    current['druggability_score'] = float(line.split()[-1])
            if current:
                pockets.append(current)
    return pockets

def cache_pockets(pdb_id, pockets, ttl=604800):
    key = f"fpocket:{pdb_id}"
    r.setex(key, ttl, json.dumps(pockets))

def get_cached_pockets(pdb_id):
    key = f"fpocket:{pdb_id}"
    cached = r.get(key)
    if hasattr(cached, '__await__'):
        raise RuntimeError('Redis client returned an Awaitable. Ensure you are using the sync redis-py client, not aioredis or an async wrapper.')
    if cached:
        if isinstance(cached, bytes):
            return json.loads(cached.decode())
        else:
            raise TypeError(f"Unexpected cached value type: {type(cached)}")
    return None 
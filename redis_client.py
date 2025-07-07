import redis
import os

def get_redis_connection():
    host = os.environ.get('REDIS_HOST', 'localhost')
    port = int(os.environ.get('REDIS_PORT', 6379))
    print(f"[REDIS CONNECT] host={host} port={port}")
    return redis.Redis(host=host, port=port, db=0) 
# fpocket_service

A Dockerized microservice for protein pocket detection using fpocket.

## Features
- Accepts PDB ID via REST API
- Downloads the corresponding PDB file from RCSB
- Runs fpocket to detect binding pockets
- Returns pocket scores and details as JSON
- Caches results in Redis for fast repeated queries

## API
### POST /analyze_pocket
**Request:**
```json
{
  "pdb_id": "1N0W"
}
```
**Response:**
```json
{
  "pdb_id": "1N0W",
  "pockets": [
    {
      "pocket_id": "1",
      "volume": 510.2,
      "druggability_score": 0.85
    },
    ...
  ]
}
```

## Usage
1. Build and run with Docker Compose:
   ```bash
   docker compose up --build
   ```
2. Call the API:
   ```bash
   curl -X POST http://localhost:8000/analyze_pocket -H 'Content-Type: application/json' -d '{"pdb_id": "1N0W"}'
   ``` 
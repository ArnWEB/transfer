# LangGraph Drug Discovery Pipeline

A modular, LLM-powered drug discovery workflow using FastAPI, LangGraph, and modern Python best practices.

## Features
- Disease name extraction from natural language
- Calls FastAPI endpoints for protein target recommendations
- LLM-powered Markdown summary generation
- Modular, testable, and extensible architecture

## Project Structure

```
langgraph_drug_discovery/
│
├── src/
│   ├── main.py                  # FastAPI + LangGraph app entry point
│   ├── config/
│   │   └── settings.py          # Configuration (e.g., API keys, URLs)
│   │
│   ├── core/
│   │   ├── langgraph_workflow.py  # Main LangGraph workflow definition
│   │   └── llm_utils.py           # LLM chain utilities (prompt templates, chains)
│   │
│   ├── services/
│   │   └── fastapi_client.py      # Client to call your FastAPI endpoints
│   │
│   ├── models/
│   │   └── state.py               # State definitions for LangGraph
│   │
│   └── utils/
│       └── logger.py              # Custom logging setup
│
├── tests/                         # Unit and integration tests
│   ├── test_langgraph_workflow.py
│   ├── test_fastapi_client.py
│   └── ...
│
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
└── README.md                      # Project documentation
```

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up your `.env` file with API keys and config.
3. Run the app:
   ```bash
   python src/main.py
   ``` 
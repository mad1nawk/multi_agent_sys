import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from mem0 import Memory

DATA_DIR = Path("workspace/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


# Returns a LangGraph checkpointer for short-term memory
def get_short_term_checkpointer() -> SqliteSaver:
    db_path = DATA_DIR / "checkpoints.sqlite"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


# Initializes local Mem0 using Ollama and a local Qdrant
def get_long_term_memory() -> Memory:
    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen3.5:4b",
                "temperature": 0.0,
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "student_memory",
                "path": str(DATA_DIR / "qdrant_db"),
                "embedding_model_dims": 768,
            },
        },
        "history_db_path": str(DATA_DIR / "mem0_history.db"),
    }
    return Memory.from_config(config)

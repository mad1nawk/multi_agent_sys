import sqlite3
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver
from mem0 import Memory

DATA_DIR = Path("workspace/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_short_term_checkpointer() -> SqliteSaver:
    """
    Возвращает чекпоинтер LangGraph для краткосрочной памяти (сессии по thread_id).
    """
    db_path = DATA_DIR / "checkpoints.sqlite"
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    return SqliteSaver(conn)


def get_long_term_memory() -> Memory:
    """
    Инициализирует локальный Mem0 с использованием Ollama (Qwen 3.5 4B + nomic-embed-text)
    и локального Qdrant без внешних облачных API.
    """
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

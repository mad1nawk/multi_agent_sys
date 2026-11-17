import logging
import socket
from pathlib import Path
from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.otel import register

LOG_DIR = Path("workspace/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("socrates.observability")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(LOG_DIR / "agent.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def _is_port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def init_tracing(project_name: str = "socrates-study-assistant"):
    if not _is_port_open("localhost", 6006):
        logger.info("Arize Phoenix server is not running on port 6006; tracing skipped.")
        return

    try:
        tracer_provider = register(
            project_name=project_name,
            endpoint="http://localhost:6006/v1/traces",
        )
        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("Arize Phoenix tracing initialized (http://localhost:6006)")
    except Exception as e:
        logger.warning(f"Arize Phoenix unavailable: {e}")


def trigger_alert(alert_type: str, details: str):
    alert_msg = f"[ALERT: {alert_type}] {details}"
    print(f"\n {alert_msg}\n")
    logger.error(alert_msg)

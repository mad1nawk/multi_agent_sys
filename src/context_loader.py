from datetime import datetime
from pathlib import Path

PROMPTS_DIR = Path("prompts")
WORKSPACE_DIR = Path("workspace")


def _read_md(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return ""

# Loads the appropriate SKILL.md depending on the router branch.
def load_skill(route: str) -> str:
    skill_map = {
        "MATH": WORKSPACE_DIR / "skills" / "math-proof" / "SKILL.md",
        "PLAN": WORKSPACE_DIR / "skills" / "study-plan" / "SKILL.md",
        "QUIZ": WORKSPACE_DIR / "skills" / "quiz-generator" / "SKILL.md",
    }
    path = skill_map.get(route)
    if path and path.exists():
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) == 3:
                return parts[2].strip()
        return text.strip()
    return ""

# For Gemma 3 270M – only a pure classifier without extra context
def build_router_prompt() -> str:
    return _read_md(PROMPTS_DIR / "router.md")

# Assembling the system prompt for the Solver
def build_solver_prompt(route: str, retrieved_notes: str = "", verifier_errors: list = None) -> str:
    parts = [
        _read_md(PROMPTS_DIR / "_common.md"),
        _read_md(WORKSPACE_DIR / "SOUL.md"),
        _read_md(PROMPTS_DIR / "solver.md"),
    ]

    skill_text = load_skill(route)
    if skill_text:
        parts.append(f"# LOADED SKILL\n{skill_text}")

    if retrieved_notes and "No specific memory" not in retrieved_notes:
        parts.append(f"# MEMORY CONTEXT\n{retrieved_notes}")

    if verifier_errors:
        parts.append(f"# [VERIFIER_ERRORS]\n{verifier_errors}")

    return "\n\n---\n\n".join(p for p in parts if p)

# System prompt for the Planner
def build_planner_prompt(route: str, retrieved_notes: str = "", verifier_errors: list = None) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    planner_raw = _read_md(PROMPTS_DIR / "planner.md").replace("{current_date}", current_date)

    parts = [
        _read_md(PROMPTS_DIR / "_common.md"),
        _read_md(WORKSPACE_DIR / "SOUL.md"),
        _read_md(WORKSPACE_DIR / "USER.md"),
        _read_md(WORKSPACE_DIR / "MEMORY.md"),
        planner_raw,
        f"# ACTIVE ROUTE\nactive_mode: {route}",
    ]

    skill_text = load_skill(route)
    if skill_text:
        parts.append(f"# LOADED SKILL\n{skill_text}")

    if retrieved_notes:
        parts.append(f"# RETRIEVED MEMORY & NOTES\n{retrieved_notes}")

    if verifier_errors:
        parts.append(f"# [VERIFIER_ERRORS] FROM PREVIOUS ATTEMPT\n{verifier_errors}")

    return "\n\n---\n\n".join(p for p in parts if p)

# System prompt for the Verifier
def build_verifier_prompt() -> str:
    return "\n\n---\n\n".join([
        _read_md(WORKSPACE_DIR / "AGENTS.md"),
        _read_md(PROMPTS_DIR / "verifier.md"),
    ])


# System prompt for the Memory Manager
def build_memory_prompt(mode: str) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    raw = _read_md(PROMPTS_DIR / "memory.md").replace("{current_date}", current_date)
    return f"{raw}\n\n# ACTIVE CALLER INSTRUCTION\nExecute strictly in MODE: {mode}."

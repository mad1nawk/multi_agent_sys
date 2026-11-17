import json
from datetime import datetime
from pathlib import Path
from typing import List, Literal

import sympy as sp
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Folder where completed plans and quizzes will be saved
OUTPUT_DIR = Path("workspace/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Tool for solver: Mathematical Calculator (SymPy)
class CalculatorInput(BaseModel):
    operation: Literal["evaluate", "simplify", "solve", "diff", "integrate", "limit"] = Field(
        description="Тип математической операции."
    )
    expression: str = Field(
        description="Математическое выражение в синтаксисе Python/SymPy (например: 'x**2 + 2*x - 3', 'x * exp(x)')."
    )
    variable: str = Field(
        default="x",
        description="Переменная, по которой выполняется операция (по умолчанию 'x')."
    )
    point: str = Field(
        default="0",
        description="Точка для вычисления предела (используется только если operation == 'limit', например '0' или 'oo')."
    )


@tool("calculator", args_schema=CalculatorInput)
def calculator(operation: str, expression: str, variable: str = "x", point: str = "0") -> str:
    try:
        var = sp.Symbol(variable)
        expr = sp.sympify(expression)

        if operation == "evaluate":
            result = expr.evalf()
        elif operation == "simplify":
            result = sp.simplify(expr)
        elif operation == "solve":
            result = sp.solve(expr, var)
        elif operation == "diff":
            result = sp.diff(expr, var)
        elif operation == "integrate":
            result = sp.integrate(expr, var)
        elif operation == "limit":
            pt = sp.sympify(point)
            result = sp.limit(expr, var, pt)
        else:
            return f"Error: Unsupported operation '{operation}'."

        return f"SymPy Result ({operation}): {str(result)}"

    except Exception as e:
        return f"Calculator Error: {str(e)}. Check expression syntax (use ** for power, * for multiplication)."


# Tool for planer: Saving a diagnostic test (JSON)
class QuizQuestion(BaseModel):
    question: str = Field(description="Question text")
    options: List[str] = Field(min_length=4, max_length=4, description="Exactly 4 answer options (A, B, C, D)")
    correct_letter: Literal["A", "B", "C", "D"] = Field(description="Letter of the correct answer")
    explanation: str = Field(description="Explanation of why the answer is correct")
    difficulty: Literal["recall", "application", "analysis"] = Field(description="Difficulty level")


class MakeQuizInput(BaseModel):
    topic: str = Field(description="Test topic")
    questions: List[QuizQuestion] = Field(min_length=5, max_length=5, description="Exactly 5 questions")


# saves a test of 5 questions with 4 answer options to a JSON file
@tool("make_quiz", args_schema=MakeQuizInput)
def make_quiz(topic: str, questions: List[QuizQuestion]) -> str:
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c if c.isalnum() else "_" for c in topic).strip("_")
        quiz_path = OUTPUT_DIR / f"quiz_{safe_topic}_{timestamp}.json"

        payload = {
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "questions": [q.model_dump() for q in questions]
        }
        quiz_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

        return f"Success: Quiz with 5 questions saved to '{quiz_path}'."

    except Exception as e:
        return f"Error saving quiz: {str(e)}"


SOLVER_TOOLS = [calculator]
PLANNER_TOOLS = [make_quiz]

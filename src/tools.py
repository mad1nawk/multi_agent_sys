import json
from datetime import datetime
from pathlib import Path
from typing import List, Literal

import sympy as sp
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Папка, куда будут сохраняться готовые планы и тесты
OUTPUT_DIR = Path("workspace/outputs")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =====================================================================
# 1. ИНСТРУМЕНТ ДЛЯ SOLVER: Математический калькулятор (SymPy)
# =====================================================================

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
    """
    Детерминированный символьный и числовой калькулятор на базе SymPy.
    Используется для точных вычислений, упрощения выражений, решения уравнений,
    нахождения производных, интегралов и пределов.
    """
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


# =====================================================================
# 2. ИНСТРУМЕНТ ДЛЯ PLANNER: Экспорт учебного плана (.md и .ics)
# =====================================================================

class StudyTaskItem(BaseModel):
    day_number: int = Field(description="Номер дня (1, 2, 3...)")
    date_str: str = Field(description="Дата в формате YYYY-MM-DD")
    topic: str = Field(description="Название темы или подтемы")
    duration_minutes: int = Field(ge=15, le=180, description="Длительность занятия в минутах (обычно 25-50)")
    repetition_of: str = Field(default="-", description="Повторение какой темы (или '-' если новая тема)")


class WritePlanInput(BaseModel):
    course_title: str = Field(description="Название курса или экзамена")
    tasks: List[StudyTaskItem] = Field(description="Список учебных задач по дням")
    checkpoints: List[str] = Field(description="Список еженедельных контрольных точек")


@tool("write_plan", args_schema=WritePlanInput)
def write_plan(course_title: str, tasks: List[StudyTaskItem], checkpoints: List[str]) -> str:
    """
    Сохраняет структурированный учебный план в формате Markdown (.md)
    и экспортирует его в формат календаря iCalendar (.ics).
    """
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in course_title).strip("_")
        md_path = OUTPUT_DIR / f"plan_{safe_title}_{timestamp}.md"
        ics_path = OUTPUT_DIR / f"plan_{safe_title}_{timestamp}.ics"

        # 1. Формируем Markdown-файл
        md_lines = [
            f"# Study Plan: {course_title}\n",
            "| Day | Date | Topic | Tasks (min) | Repetition of |",
            "| :--- | :--- | :--- | :--- | :--- |"
        ]
        for t in tasks:
            md_lines.append(f"| {t.day_number} | {t.date_str} | {t.topic} | {t.duration_minutes} | {t.repetition_of} |")

        md_lines.append("\n## Weekly Checkpoints")
        for cp in checkpoints:
            md_lines.append(f"- {cp}")

        md_path.write_text("\n".join(md_lines), encoding="utf-8")

        # 2. Формируем iCalendar (.ics) для импорта в Google/Apple Calendar
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//StudyAssistant//Socrates//EN"
        ]
        for idx, t in enumerate(tasks, start=1):
            clean_date = t.date_str.replace("-", "")
            ics_lines.extend([
                "BEGIN:VEVENT",
                f"UID:study-{timestamp}-{idx}@socrates.local",
                f"DTSTAMP:{datetime.now().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART;VALUE=DATE:{clean_date}",
                f"SUMMARY:[Study] {t.topic} ({t.duration_minutes} min)",
                f"DESCRIPTION:Course: {course_title} | Repetition of: {t.repetition_of}",
                "END:VEVENT"
            ])
        ics_lines.append("END:VCALENDAR")
        ics_path.write_text("\n".join(ics_lines), encoding="utf-8")

        return f"Success: Plan exported to '{md_path}' and '{ics_path}'."

    except Exception as e:
        return f"Error saving study plan: {str(e)}"


# =====================================================================
# 3. ИНСТРУМЕНТ ДЛЯ PLANNER: Сохранение диагностического теста (JSON)
# =====================================================================

class QuizQuestion(BaseModel):
    question: str = Field(description="Текст вопроса")
    options: List[str] = Field(min_length=4, max_length=4, description="Ровно 4 варианта ответа (A, B, C, D)")
    correct_letter: Literal["A", "B", "C", "D"] = Field(description="Буква правильного ответа")
    explanation: str = Field(description="Объяснение, почему ответ верный и почему остальные неверны")
    difficulty: Literal["recall", "application", "analysis"] = Field(description="Уровень сложности по Блуму")


class MakeQuizInput(BaseModel):
    topic: str = Field(description="Тема теста")
    questions: List[QuizQuestion] = Field(min_length=5, max_length=5, description="Ровно 5 вопросов")


@tool("make_quiz", args_schema=MakeQuizInput)
def make_quiz(topic: str, questions: List[QuizQuestion]) -> str:
    """
    Валидирует и сохраняет тест из 5 вопросов с 4 вариантами ответа в JSON-файл.
    """
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


# Списки инструментов для привязки к конкретным узлам (bind_tools)
SOLVER_TOOLS = [calculator]
PLANNER_TOOLS = [write_plan, make_quiz]

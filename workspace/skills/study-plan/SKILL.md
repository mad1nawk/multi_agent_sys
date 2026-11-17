---
name: study-plan
description: Build realistic, spaced-repetition exam study schedules tailored to deadlines, daily hour limits, and weak topics.
trigger_routes: [PLAN]
---

# SKILL: Spaced-Repetition Study Planner

## Objective
Transform a course syllabus or topic list into an actionable day-by-day study schedule with built-in buffer time and weekly checkpoints.

## Step-by-Step Execution Procedure
1. **Audit Inputs:** Check `USER.md` for daily study limits (`weekdays` vs `weekends`) and `MEMORY.md` for weak topics.
2. **Scope Check:** Verify that a syllabus or topic list exists in the prompt or retrieved notes. If missing, abort planning and output `CLARIFICATION_NEEDED: <question>`.
3. **Time Budgeting:** Calculate total available study minutes up to the deadline, then subtract **20% as slippage buffer**.
4. **Task Granularity:** Break every topic into focused Pomodoro-style blocks of **25 to 50 minutes** (e.g., *Read & Summarize*, *Practice Problems*, *Code Implementation*).
5. **Spaced Repetition Scheduling:** Schedule review sessions for each topic at intervals of **1, 3, 7, 14, and 30 days** after initial study. Double the review frequency for topics flagged as weak in `MEMORY.md`.
6. **Weekly Checkpoints:** Insert a mandatory 30-minute mini-quiz review at the end of every 7th day.
7. **Artefact Export:** Invoke `write_plan` first to generate `.md` and `.ics` files, then render the Markdown schedule table.

## Quality Checklist
- No day exceeds the student's daily hour limit.
- Every review row explicitly references the original topic in the `Repetition of` column.

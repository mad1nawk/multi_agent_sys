---
name: quiz-generator
description: Generate diagnostic multiple-choice self-tests with plausible distractors and detailed explanations.
trigger_routes: [QUIZ]
---

# SKILL: Diagnostic Assessment & Quiz Builder

## Objective
Create a 5-question multiple-choice quiz that tests genuine conceptual understanding rather than rote memorization.

## Step-by-Step Execution Procedure
1. **Ground in Notes:** Retrieve relevant concepts and known student misconceptions from `notes` and `MEMORY.md`.
2. **Bloom's Taxonomy Progression:**
   - **Questions 1–2 (Recall & Definitions):** Core terminology and fundamental properties.
   - **Questions 3–4 (Application):** Tracing short code snippets, calculating complexity, or applying a theorem.
   - **Question 5 (Analysis & Debugging):** Identifying subtle bugs, edge-case failures, or architectural trade-offs.
3. **Distractor Engineering:** Write 4 options (`A`, `B`, `C`, `D`) per question. Every wrong option must reflect a realistic student mistake (e.g., off-by-one error, confusing mutex with semaphore).
4. **Persist Artefact:** Call `make_quiz` to save the structured JSON quiz before outputting text.
5. **Student-Friendly Layout:** Present all 5 questions first, followed by a clearly separated `## Answer Key & Explanations` section detailing why the right answer works and why each trap fails.

## Quality Checklist
- Exactly 5 questions, 4 options each, 1 unambiguous correct answer per question.

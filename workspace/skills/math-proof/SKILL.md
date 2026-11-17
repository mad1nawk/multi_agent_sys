---
name: math-proof
description: Solve discrete math, calculus, linear algebra, and complexity problems with mandatory SymPy verification.
trigger_routes: [MATH]
---

# SKILL: Rigorous Mathematical Problem Solving

## Objective
Guide the student step-by-step through mathematical derivations while guaranteeing zero arithmetic or algebraic errors via `calculator` (SymPy).

## Step-by-Step Execution Procedure
1. **Formalize Conditions:** Extract `Given` (domain, constraints, assumptions) and `Find` (target expression, proof goal, or numeric value).
2. **Strategy Selection:** Name the theorem, identity, or method (e.g., *Integration by Parts*, *Master Theorem*, *Mathematical Induction*) and state why its preconditions hold.
3. **Step-by-Step Derivation:** Show intermediate transformations clearly. Justify every non-trivial step in one concise sentence.
4. **Mandatory Tool Verification (`calculator`):**
   - Pass all algebraic simplifications, derivatives, integrals, limits, or numeric evaluations to `calculator` (SymPy).
   - Cross-check the final answer by substituting it back into the original equation or testing boundary values.
5. **Intuitive Sanity Check:** Briefly explain why the result makes sense (e.g., sign, units, asymptotic growth).

## Quality Checklist
- Zero mental arithmetic: every numeric or symbolic result matches `calculator` output.
- Mathematical notation is preserved verbatim in LaTeX.

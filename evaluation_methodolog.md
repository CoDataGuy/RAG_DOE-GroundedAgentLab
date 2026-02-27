
---

# 📄 `docs/00_story.md` — Project Narrative


# Project Evolution: From Prototype to Evaluation Framework

## Motivation

RAG systems are often tuned heuristically.  
This project treats RAG performance as a measurement problem under controlled experimental design.

The game instruction mimic domain knowledge providing:
- Fixed authoritative document
- Objective correctness criteria
- Clear out-of-scope boundary cases

---

## Phase 1 — Notebook POC

- All logic in Jupyter
- Retrieval + agent + scoring co-located
- Manual evaluation

Limitations:
- Tight coupling
- No reproducibility structure
- Hard to scale experiments

---

## Phase 2 — Randomized Complete Block Design (RCBD)

- Treatment: Temperature
- Blocking factor: Question Type
- 93 total runs (balanced design)
- ANOVA with blocking

Finding:
Temperature did not materially affect RGS.

---

## Phase 3 — Modularization

- Extracted retrieval and agent helpers into Python modules
- Introduced separation of concerns
- Externalized prompts into JSON
- Config-driven execution

Outcome:
Reusable experimental framework.

---

## Phase 4 — Prompt Caching

Goal:
Reduce cost while preserving deterministic evaluation.

Introduced:
- Cache keys based on prompt + retrieved chunks
- Batch execution
- Cost logging

---

## Phase 5 — LLM-as-Judge

- Replaced manual scoring
- Batch evaluation pipeline
- Structured rubric scoring
- Calibration against human scores

---

## Phase 6 — Fractional Factorial DOE

Factors considered:
- Temperature
- Retrieval depth (k)
- Chunk size
- Prompt constraint strictness

Goal:
Identify main effects and interactions driving groundedness.

---

## Future Direction

- Multi-game agents (generalization test)
- Migration from LLM to SLM
- Cost-performance tradeoff analysis
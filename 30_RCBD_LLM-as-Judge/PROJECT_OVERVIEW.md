## Executive Summary

This project evaluates RAG (Retrieval-Augmented Generation) answer quality using the board game Clue as a bounded knowledge domain. An LLM agent answers a 31-question bank against a hybrid retriever, with Extended Thinking enabled throughout. A second and third LLM call — split into two independent judges — then score every answer for **quality** and for **refusal behaviour**, writing results back into a single CSV.

- **Design:** Completely Randomized Design (CRD) — 31 questions × 2 replicates = 62 runs, fully randomized order. Temperature is fixed at 1.0 (an API constraint of Extended Thinking), not a treatment variable.
- **Stack:** Python 3, Jupyter, Anthropic Claude API, VoyageAI embeddings. No database — retrieval and vector storage are in-memory, rebuilt every notebook session.
- **Branch:** `feature/llm-judge-scoring-split` — reworked the Judge subsystem from an async Anthropic-Batches design into two synchronous, per-row scripts.
- **Diagrams:** see [Solution Documentation/diagrams/](Solution%20Documentation/diagrams/README.md) for full C4 (context/container/component) and UML (sequence, state, class, ER, data-flow) diagrams. Start with [sequence-experiment-workflow.md](Solution%20Documentation/diagrams/sequence-experiment-workflow.md) for the end-to-end flow.

## Pipeline — 3 Phases, Run Manually and in Order

```
Phase 1 (Notebook)              Phase 2 (Script)              Phase 3 (Script)
──────────────────────          ──────────────────────        ──────────────────────
Build hybrid retriever          Read Output/*.csv             Read same CSV
  (chunk → contextualize        For each row: Claude call     Hard-fails unless Phase 2
   → embed → BM25 + Vector)       with QUESTION+ANSWER+CHUNKS   has already run
Load 31 questions, build        Parse JSON, write C1-C5 +     For each row: Claude call
  62-run CRD design matrix        reasoning + judge_thinking     with QUESTION+ANSWER+
Run agent per row (tool-use     Rewrite CSV after EVERY row     AGENT_THINKING (not chunks)
  loop, retries, thinking)                                    Write refusal flags + reasoning
Write one row per run to CSV                                  Rewrite CSV after EVERY row

python Judge/AgentJudge.py           →           python Judge/RefusalJudge.py
```

There is no orchestrator — the researcher runs the notebook, then `AgentJudge.py`, then `RefusalJudge.py`, by hand. All three phases read and write **one file**: `Output/Ext_ClueRag_CRD.csv`.

## Key Modules

| File | Role |
|------|------|
| `Notebooks/Ext_ClueRag_CRD.ipynb` | Phase 1 — full 62-run experiment (`10qExt_ClueRag_CRD.ipynb` is a 10-question smoke test) |
| `Judge/AgentJudge.py` | Phase 2 — quality scoring (C1 correctness, C2 coverage, C3 citation presence, C4 citation valid, C5 clarity) |
| `Judge/RefusalJudge.py` | Phase 3 — refusal scoring (CorrectRefusal, ImproperRefusal, ShouldHaveRefused); requires Phase 2's `C1_correctness` to be populated |
| `retriever_implementation.py` | Hybrid retrieval: hand-rolled BM25 + cosine-similarity VectorIndex, fused via Reciprocal Rank Fusion, optional LLM rerank |
| `rag_helpers.py` / `llm_helpers.py` | Retriever factory, chunking/contextualizing, and the Anthropic API wrapper (with prompt caching) used by the notebook |


See [Solution Documentation/diagrams/README.md](Solution%20Documentation/diagrams/README.md) and [Judge Design/README.md](Solution%20Documentation/diagrams/Judge%20Design/README.md) for full architectural detail.

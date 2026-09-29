# LLM Judge — Design Overview

**Component of:** Clue RAG Evaluation Pipeline
**Role:** Automated quality and refusal-behaviour evaluation of RAG agent responses, using a second LLM as evaluator

> This document previously described an async, two-phase, Batches-API design (`judge_submit.py`/`judge_retrieve.py`). That design was removed in commit `4c71a15` ("Judge logic split Agent/Refusal; single scoring sheet, synchronous now"). This is a full rewrite against the current code: `Judge/AgentJudge.py` + `Judge/RefusalJudge.py`.

---

## 1. Purpose

The LLM Judge is an automated scoring subsystem that scores each RAG agent answer twice, using two separate Claude calls per row with two separate rubrics:

1. **Quality** (`AgentJudge.py`) — is the answer correct, complete, cited, and clear?
2. **Refusal behaviour** (`RefusalJudge.py`) — did the agent correctly refuse out-of-scope questions, and correctly answer in-scope ones?

Splitting these into two independent judges (rather than one judge scoring 8 metrics at once) was a deliberate design change on this branch — see commit `4c71a15`. The rationale, per `JudgeAgentPrompt.json`: "A separate evaluator handles all refusal logic," reducing the chance that a judge's view of refusal contaminates its view of quality, and vice versa.

---

## 2. System Context

```
┌───────────────────────────────────────────────────┐
│                RAG Experiment (Notebook)            │
│  Input: ClueQuestions.csv + ClueRules.md            │
│  Output: Output/Ext_ClueRag_CRD.csv                 │
└───────────────────────┬────────────────────────────┘
                        │ produces the scoring sheet
                        ▼
┌───────────────────────────────────────────────────┐
│                     LLM Judge                       │
│                                                      │
│  AgentJudge.py  ────────►  Claude API (per row)     │
│        │                                             │
│        ▼ writes C1-C5 in place                       │
│  Output/Ext_ClueRag_CRD.csv                          │
│        │                                             │
│        ▼ read again, gated on C1_correctness         │
│  RefusalJudge.py ───────►  Claude API (per row)      │
│        │                                             │
│        ▼ writes refusal flags in place                │
│  Output/Ext_ClueRag_CRD.csv  (final state)            │
└───────────────────────────────────────────────────┘
```

The Judge is a **downstream, offline** component — it consumes the CSV the notebook produces and enriches it further. It does not interact with the RAG agent or the retriever directly, and it does not read `ClueRules.md` — only the `retrieved_chunks` and `agent_thinking` text already captured in the CSV.

---

## 3. Architecture — Two-Phase Synchronous Design

| Phase | Script | Action |
|-------|--------|--------|
| **Quality** | `AgentJudge.py` | Reads CSV → for each row, calls Claude with QUESTION+ANSWER+CHUNKS → parses JSON → writes C1-C5 + reasoning + judge_thinking → **rewrites the whole CSV to disk after every row** |
| **Refusal** | `RefusalJudge.py` | Reads CSV → **hard-fails if `C1_correctness` is entirely null** → for each row, calls Claude with QUESTION+ANSWER+AGENT_THINKING → parses JSON → writes 3 refusal flags + reasoning → rewrites the CSV after every row |

**Why synchronous, not batched?** The earlier design used the Anthropic Batches API for cost savings on bulk scoring. The current design calls `client.messages.create()` directly, once per row, with no batching. This is simpler and gives per-row feedback in real time, at the cost of the ~50% Batches API discount and of not benefiting from `llm_helpers`'s automatic prompt-caching wrapper (both judge scripts instantiate `anthropic.Anthropic()` directly rather than going through `llm_helpers.chat()`).

**Why rewrite the whole CSV after every row?** Durability over throughput — a crash or rate-limit failure partway through a 62-row run loses at most the in-progress row's scores, not the whole run.

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Split Agent/Refusal into two scripts | Isolates quality judgement from refusal judgement — each rubric explicitly excludes the other's concern |
| RefusalJudge uses `agent_thinking`, not `retrieved_chunks` | Scope determination benefits from seeing the agent's own reasoning about whether it found relevant material, as supplementary (not authoritative) evidence |
| RefusalJudge hard-fails without AgentJudge scores | Encodes the required run order in code, not just documentation |
| Chain-of-thought XML tags before JSON | Both rubrics require `<evaluate_cN>` / `<scope_determination>` etc. before the final JSON — reduces metric contamination |
| Single CSV, mutated in place | No separate input/output file split; simpler at the cost of losing the original unscored data unless it's backed up first |

---

## 4. Scoring at a Glance

| Metric | Script | Type | What it measures |
|--------|--------|------|-------------------|
| `C1_correctness` | AgentJudge | Lenient (0/1) | Factual accuracy and usefulness |
| `C2_coverage` | AgentJudge | Lenient (0/1) | Completeness — would a reasonable person be left confused? |
| `C3_citation_presence` | AgentJudge | Deterministic-in-principle (0/1) | Does the answer contain a `CHUNK_N` reference? (rubric wording currently being loosened — see §6) |
| `C4_citation_valid` | AgentJudge | Deterministic-in-principle (0/1) | Do the cited chunks actually support the claims? |
| `C5_clarity` | AgentJudge | Lenient (0/1) | Fluency and readability |
| `CorrectRefusal` | RefusalJudge | Refusal (0/1) | Answer is a refusal AND question was out-of-scope |
| `ImproperRefusal` | RefusalJudge | Refusal (0/1) | Answer is a refusal AND question was in-scope |
| `ShouldHaveRefused` | RefusalJudge | Refusal (0/1) | Answer was NOT a refusal AND question was out-of-scope |

See [scoring-rubric.md](scoring-rubric.md) for full rubric text and the RGS formula.

### Rule Grounding Score (RGS) — defined, but not computed on this branch

```
RGS = C1 × (C2 + C3 + C4 + C5) / 4
```

This formula exists only in `scoring_helper.merge_scores()`, which both notebooks `import` but **never call**. Neither `AgentJudge.py` nor `RefusalJudge.py` computes RGS. The `RGS`/`groundedness` columns in the CSV are written blank at Phase 1 and stay blank. Treat this as an open item, not a documentation gap — the code path genuinely does not exist on this branch.

---

## 5. File Structure

```
Judge/
├── AgentJudge.py               ← Phase: quality scoring (C1-C5)
├── RefusalJudge.py              ← Phase: refusal scoring (3 flags), run after AgentJudge
├── JudgeAgentPrompt.json        ← AgentJudge rubric (uncommitted edit in progress on C3/C4)
├── JudgeRefusalPrompt.json      ← RefusalJudge rubric
└── JudgeScoringPrompt.json      ← orphaned duplicate of an older rubric — not loaded by any code

Output/
└── Ext_ClueRag_CRD.csv          ← single scoring sheet, read AND written by both scripts

Solution Documentation/diagrams/Judge Design/
├── README.md                    ← this file
├── scoring-rubric.md            ← full rubric text, metric definitions, RGS formula/gap
└── c4-diagrams.md               ← C4 context, container, and component diagrams (Mermaid)
```

> Note: earlier versions of this README referenced `uml-diagrams.md` and `operations.md` in this folder — neither file exists in the repository. The end-to-end sequence diagram now lives at [/Solution Documentation/diagrams/sequence-experiment-workflow.md](../sequence-experiment-workflow.md), which covers Phase 1 (notebook) through Phase 3 (RefusalJudge) in one diagram.

---

## 6. Open Items on This Branch

- **RGS is never computed** (see §4). `merge_scores()` would need to be called explicitly, or the notebooks/judges updated to call it.
- **`JudgeAgentPrompt.json` has an uncommitted edit** loosening C3 (citation presence) and C4 (citation valid) from a purely mechanical `CHUNK_N` format check toward a content-support judgement — this blurs the "deterministic vs. lenient" distinction the rubric otherwise draws. Worth a deliberate decision before merging.
- **`JudgeScoringPrompt.json` is orphaned** (added in `b9b13c3`, superseded by `JudgeAgentPrompt.json` in `4c71a15`, never deleted, not loaded by any code).
- **`.env`'s `REFUSAL_JUDGE_MODEL_NAME` key has a space before `=`** — worth confirming this resolves correctly via `python-dotenv` rather than silently returning `None`.

---

## 7. Related Documentation

- [/Solution Documentation/diagrams/](../README.md) — full-system diagrams (C4, sequence, ER, class, data-flow) for the whole pipeline, not just the Judge
- [/PROJECT_OVERVIEW.md](../../../PROJECT_OVERVIEW.md) — 1-page solution summary

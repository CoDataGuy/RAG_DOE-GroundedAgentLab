# Entity-Relationship Diagram - Experiment Data Model

> All entities below map onto a **single physical file**, `Output/Ext_ClueRag_CRD.csv` — there is no database and no separate "judged" CSV. The ER model is logical, showing how the 35 columns group conceptually and are populated by three different phases at three different times.

```mermaid
erDiagram
    QUESTION {
        int number PK
        string text
        string type "S, M, or F"
    }

    DESIGN_MATRIX_ENTRY {
        int run_id PK
        int question_number FK
        int replicate "1 or 2"
    }

    EXPERIMENT_RUN {
        int run_id PK
        string timestamp
        float temperature_value "always 1.0"
        string answer
        string agent_thinking
        string retrieved_chunks
        string status "SUCCESS, ERROR"
        string error_message
        int iteration_count
        int retry_count
        int tool_calls_count
        string search_queries
    }

    QUALITY_SCORE {
        int run_id PK, FK
        int C1_correctness "0 or 1"
        int C2_coverage "0 or 1"
        int C3_citation_presence "0 or 1"
        int C4_citation_valid "0 or 1"
        int C5_clarity "0 or 1"
        string reasoning_C1
        string reasoning_C2
        string reasoning_C3
        string reasoning_C4
        string reasoning_C5
        string judge_thinking
        string scored_by "AgentJudge"
        string scoring_notes "error text if the row failed"
    }

    REFUSAL_SCORE {
        int run_id PK, FK
        int CorrectRefusal "0 or 1"
        int ImproperRefusal "0 or 1"
        int ShouldHaveRefused "0 or 1"
        string reasoning_refusal
    }

    DERIVED_METRIC {
        int run_id PK, FK
        float RGS "defined, never populated on this branch"
        string groundedness "defined, never populated on this branch"
    }

    CHUNK {
        int chunk_number PK
        string content
        string contextualized_content
        blob embedding
    }

    QUESTION ||--o{ DESIGN_MATRIX_ENTRY : "tested (x2 replicates)"
    DESIGN_MATRIX_ENTRY ||--|| EXPERIMENT_RUN : "produces (Phase 1)"
    EXPERIMENT_RUN ||--o| QUALITY_SCORE : "scored by AgentJudge (Phase 2)"
    QUALITY_SCORE ||--o| REFUSAL_SCORE : "scored by RefusalJudge (Phase 3, gated on QUALITY_SCORE existing)"
    EXPERIMENT_RUN ||--o| DERIVED_METRIC : "would be computed by merge_scores() — not currently invoked"
    EXPERIMENT_RUN }o--o{ CHUNK : "cites via retrieved_chunks / CHUNK_N"
```

## Entity Descriptions

| Entity | Description | Cardinality | Populated by |
|--------|-------------|-------------|---------------|
| QUESTION | 31 questions loaded from `ClueQuestions.csv` | 31 records | input data, not written to output CSV directly |
| DESIGN_MATRIX_ENTRY | Randomized CRD run spec | 62 records (31 x 2 replicates) | `run_CRD_experiment()` |
| EXPERIMENT_RUN | Agent execution result | 62 records | Phase 1 (notebook) |
| QUALITY_SCORE | C1–C5 + reasoning + judge thinking | up to 62 records | Phase 2 (`AgentJudge.py`) |
| REFUSAL_SCORE | 3 refusal flags + reasoning | up to 62 records | Phase 3 (`RefusalJudge.py`), requires QUALITY_SCORE to exist first |
| DERIVED_METRIC | RGS / groundedness | **0 records on this branch** | nothing — `merge_scores()` is dead code |
| CHUNK | Document chunks with embeddings | ~8 records | Phase 1 setup, in-memory only (not persisted to CSV) |

## Full CSV Schema (`Output/Ext_ClueRag_CRD.csv`, 35 columns)

```
run_id | timestamp | replicate | question_number | question_type | question_text | temperature_value |
answer | agent_thinking | retrieved_chunks |
status | error_message | iteration_count | retry_count | tool_calls_count | search_queries |
C1_correctness | C2_coverage | C3_citation_presence | C4_citation_valid | C5_clarity |
CorrectRefusal | ImproperRefusal | ShouldHaveRefused |
reasoning_C1 | reasoning_C2 | reasoning_C3 | reasoning_C4 | reasoning_C5 | reasoning_refusal |
judge_thinking | scored_by | scoring_notes |
RGS | groundedness
```

## Relationship Cardinality

| Relationship | Type | Description |
|--------------|------|--------------|
| QUESTION → DESIGN_MATRIX_ENTRY | 1:2 | Each question appears exactly twice (2 replicates) |
| DESIGN_MATRIX_ENTRY → EXPERIMENT_RUN | 1:1 | Each design entry executes exactly once |
| EXPERIMENT_RUN → QUALITY_SCORE | 1:0..1 | Populated only after `AgentJudge.py` runs; failed API calls leave it null with an error in `scoring_notes` |
| QUALITY_SCORE → REFUSAL_SCORE | 1:0..1 | `RefusalJudge.py` raises `RuntimeError` if `C1_correctness` is entirely null — this is a hard precondition, not just an ordering convention |
| EXPERIMENT_RUN → DERIVED_METRIC | 1:0 | No code path currently populates this — documented as a known gap |

## Design Verification (CRD, not RCBD)

```mermaid
flowchart LR
    subgraph DesignCheck["Design Matrix Validation"]
        Q["31 Questions"]
        Rp["2 Replicates"]

        Q --> DM["62 Runs"]
        Rp --> DM

        DM --> V1["Each question appears exactly 2x"]
        DM --> V2["Run order fully randomized"]
        DM --> V3["No treatment factor — temperature fixed at 1.0"]
    end
```

| Validation | Expected | Formula |
|------------|----------|---------|
| Total runs | 62 | 31 questions x 2 replicates |
| Runs per question | 2 | fixed replicate count |
| Treatment levels | 0 | temperature is fixed, not varied — this is a CRD with no active treatment factor |
| RGS bounds | n/a on this branch | RGS is never computed by the current pipeline |

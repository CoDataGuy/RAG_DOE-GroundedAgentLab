# Sequence Diagram - End-to-End Evaluation Flow

This is the primary behavioural diagram for the pipeline: one continuous run from indexing through Phase 1 (RAG agent), Phase 2 (`AgentJudge.py`) and Phase 3 (`RefusalJudge.py`). All three phases are run manually and sequentially by the researcher — there is no orchestrator, and each phase reads/writes the same CSV file (`Output/Ext_ClueRag_CRD.csv`).

```mermaid
sequenceDiagram
    autonumber
    participant R as Researcher
    participant NB as Notebook (Phase 1)
    participant RET as Retriever
    participant VA as VoyageAI API
    participant CL as Claude API
    participant CSV as Output/Ext_ClueRag_CRD.csv
    participant AJ as AgentJudge.py (Phase 2)
    participant RJ as RefusalJudge.py (Phase 3)

    rect rgb(230, 245, 255)
        Note over R,CSV: Phase 1a — Setup & Indexing (once per notebook session)
        R->>NB: Run setup cells
        NB->>NB: chunk_by_section(ClueRules.md) -> ~8 chunks
        loop for each chunk
            NB->>CL: add_context(chunk) — contextual retrieval
            CL-->>NB: situating sentence
        end
        loop for each contextualized chunk
            NB->>VA: embed(chunk)  [voyage-3-large]
            VA-->>NB: embedding vector
        end
        NB->>RET: VectorIndex.add_documents() / BM25Index.add_documents()
    end

    rect rgb(255, 245, 230)
        Note over R,CSV: Phase 1b — CRD Design (fixed temperature = 1.0, required by Extended Thinking)
        R->>NB: Run experiment cell
        NB->>NB: load 31 questions from ClueQuestions.csv
        NB->>NB: build design matrix: 31 questions x 2 replicates = 62 runs
        NB->>NB: random.shuffle(design_matrix)
        NB->>CSV: open Ext_ClueRag_CRD.csv, write header (35 columns)
    end

    rect rgb(230, 255, 230)
        Note over R,CSV: Phase 1c — Execution (per run, x62)
        loop for each randomized run
            NB->>CL: chat(question, system=GroundedSystemPrompt, thinking enabled, temperature=1.0)
            alt stop_reason == "tool_use"
                CL-->>NB: tool_use request (search_clue_instructions)
                NB->>RET: search_clue_instructions(query)
                RET->>RET: BM25Index.search() + VectorIndex.search()
                RET->>RET: Reciprocal Rank Fusion (k_rrf=60)
                RET->>CL: reranker_fn(fused_docs, query)
                CL-->>RET: reordered/filtered chunk ids
                RET-->>NB: top-k chunks (CHUNK_N + content)
                NB->>CL: chat(messages + tool_result)
                CL-->>NB: final answer + thinking block
            else stop_reason == "end_turn"
                CL-->>NB: answer + thinking block (no tool call)
            end
            NB->>CSV: append row (run_id, answer, agent_thinking, retrieved_chunks, status, etc - all judge/RGS columns blank)
        end
    end

    rect rgb(255, 230, 245)
        Note over R,AJ: Phase 2 — Quality Scoring (separate process, run after Phase 1 completes)
        R->>AJ: python Judge/AgentJudge.py
        AJ->>CSV: pd.read_csv() — load all 62 rows
        loop for each row
            AJ->>AJ: build "QUESTION + ANSWER + CHUNKS" message
            AJ->>CL: messages.create(system=JudgeAgentPrompt, thinking enabled)
            alt HTTP 429 RateLimitError
                CL-->>AJ: rate limited
                AJ->>AJ: sleep(60s), retry once
                AJ->>CL: messages.create() (retry)
            end
            CL-->>AJ: evaluate_c1..c5 reasoning tags, then trailing JSON
            AJ->>AJ: extract_json() — regex last-brace-match + json.loads
            AJ->>CSV: write C1-C5, reasoning_C1-C5, judge_thinking, scored_by="AgentJudge" (row rewritten to disk immediately)
        end
        AJ-->>R: print pass/fail summary, "Run RefusalJudge when ready"
    end

    rect rgb(235, 235, 210)
        Note over R,RJ: Phase 3 — Refusal Scoring (separate process, run after Phase 2 completes)
        R->>RJ: python Judge/RefusalJudge.py
        RJ->>CSV: pd.read_csv()
        RJ->>RJ: assert C1_correctness is not entirely null (else raise RuntimeError)
        loop for each row
            RJ->>RJ: build "QUESTION + ANSWER + AGENT_THINKING" message
            Note right of RJ: Uses the RAG agent's own extended-thinking trace as scope evidence — not the retrieved chunks
            RJ->>CL: messages.create(system=JudgeRefusalPrompt, thinking enabled)
            alt HTTP 429 RateLimitError
                CL-->>RJ: rate limited
                RJ->>RJ: sleep(60s), retry once
                RJ->>CL: messages.create() (retry)
            end
            CL-->>RJ: scope_determination / refusal_detection / evaluate_flags tags, then trailing JSON
            RJ->>RJ: extract_json()
            RJ->>CSV: write CorrectRefusal, ImproperRefusal, ShouldHaveRefused, reasoning_refusal (row rewritten to disk immediately)
        end
        RJ-->>R: print pass/fail summary, "Review Output/Ext_ClueRag_CRD.csv for full results"
    end

    Note over R,CSV: RGS is NOT computed by any step above — the RGS/groundedness columns remain blank unless a human runs scoring_helper.merge_scores() manually
    R->>R: (manual/out-of-repo) import CSV into JMP for analysis
```

## Workflow Phases

### Phase 1a — Setup & Indexing (once per notebook session)
Load `ClueRules.md` → chunk on `## ` headers → contextualize each chunk via Claude → embed via VoyageAI → build `Retriever(BM25Index, VectorIndex, reranker_fn)`. All in-memory; rebuilt every kernel restart.

### Phase 1b — CRD Design
This is a **Completely Randomized Design**, not the earlier RCBD/temperature design: temperature is fixed at `1.0` (an API constraint of Extended Thinking, not a treatment), 31 questions are each run twice (2 replicates), and the 62 runs are fully randomized. `question_type` (S/M/F) is recorded but is not a blocking factor in the current notebook logic.

### Phase 1c — Execution (per run)
`answer_clue_question()` drives up to 5 tool-use iterations per run, retries transient network errors up to 3 times, and writes one CSV row per run with the judge/RGS columns left blank.

### Phase 2 — AgentJudge.py (quality)
Runs standalone after Phase 1 finishes. Reads the whole CSV into a DataFrame, scores every row synchronously against `JudgeAgentPrompt.json` (C1 correctness, C2 coverage, C3 citation presence, C4 citation valid, C5 clarity), and **rewrites the entire CSV to disk after every single row** — durability over throughput. On a 429 it sleeps 60s and retries once; any other exception nulls the score columns for that row and records the error in `scoring_notes`.

### Phase 3 — RefusalJudge.py (refusal)
Refuses to start unless `AgentJudge.py` has already populated `C1_correctness`. Uses the **agent's own extended-thinking trace** (not the retrieved chunks) as supplementary scope evidence, and produces three flags: `CorrectRefusal`, `ImproperRefusal`, `ShouldHaveRefused`. Same per-row overwrite and retry-once-on-429 behaviour as Phase 2.

### Known gap — RGS
`RGS = C1 × (C2+C3+C4+C5) / 4` is defined in `scoring_helper.merge_scores()`, which is imported by both notebooks but **never called** anywhere in the current pipeline. The `RGS` and `groundedness` CSV columns exist in the header but are written as empty strings and never populated by `AgentJudge.py` or `RefusalJudge.py`. Any downstream statistical analysis currently has no RGS values to consume unless a human runs `merge_scores()` by hand.

## Audit Trail

| Checkpoint | Data Captured |
|------------|----------------|
| Run Start | `run_id`, `timestamp`, `replicate`, `question_number`, `question_type`, `question_text` |
| Tool Call | `search_queries`, `retrieved_chunks`, `tool_calls_count` |
| Run End (Phase 1) | `answer`, `agent_thinking`, `iteration_count`, `retry_count`, `status`, `error_message` |
| Quality Scoring (Phase 2) | `C1-C5`, `reasoning_C1-C5`, `judge_thinking`, `scored_by`, `scoring_notes` |
| Refusal Scoring (Phase 3) | `CorrectRefusal`, `ImproperRefusal`, `ShouldHaveRefused`, `reasoning_refusal` |
| Analysis (manual, not automated) | `RGS`, `groundedness` — currently always blank |

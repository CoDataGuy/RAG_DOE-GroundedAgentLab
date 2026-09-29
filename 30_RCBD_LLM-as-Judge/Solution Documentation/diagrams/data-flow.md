# Data Flow Diagram - Clue RAG Evaluation Pipeline

```mermaid
flowchart TB
    subgraph Inputs["Input Data Sources"]
        RULES[("ClueRules.md<br/>~8 sections, git-ignored")]
        QUESTIONS[("ClueQuestions.csv<br/>31 questions")]
        ENV[(".env<br/>API keys + per-role model config")]
    end

    subgraph Indexing["Document Indexing Pipeline (notebook, once per session)"]
        CHUNK["chunk_by_section()"]
        CONTEXT["add_context()<br/>LLM enhancement"]
        EMBED["generate_embedding()<br/>voyage-3-large"]
        VIDX[("VectorIndex<br/>in-memory embeddings")]
        BIDX[("BM25Index<br/>in-memory tokens")]
    end

    subgraph Design["CRD Design (notebook)"]
        LOAD_Q["load_questions_from_csv()"]
        MATRIX["build design matrix<br/>31 x 2 replicates = 62 runs"]
        RANDOM["random.shuffle()<br/>complete randomization"]
    end

    subgraph Execution["Phase 1 — Experiment Execution Loop"]
        RUN["run_CRD_experiment()"]
        AGENT["answer_clue_question()<br/>temperature fixed at 1.0"]
        SEARCH["search_clue_instructions()"]
        RETRIEVER["Retriever.search()<br/>RRF fusion + LLM rerank"]
        LLM["Claude API"]
    end

    subgraph JudgePhases["Phase 2 + 3 — Judge Scripts (separate processes, run manually in order)"]
        AJ["AgentJudge.py<br/>C1-C5 quality scoring"]
        RJ["RefusalJudge.py<br/>refusal flags — gated on AgentJudge having run"]
    end

    subgraph Outputs["Output Data"]
        MAIN_CSV[("Output/Ext_ClueRag_CRD.csv<br/>single scoring sheet, enriched in place")]
        TEMPLATE_CSV[("Output/scoring_template_CRD.csv<br/>vestigial — unused downstream")]
    end

    subgraph Analysis["Analysis (manual, out of repo)"]
        MERGE["scoring_helper.merge_scores()<br/>dead code — never called"]
        JMP["JMP ANOVA / descriptive stats"]
    end

    %% Flow connections
    ENV --> CHUNK
    RULES --> CHUNK
    CHUNK --> CONTEXT
    CONTEXT --> EMBED
    EMBED --> VIDX
    CHUNK --> BIDX

    QUESTIONS --> LOAD_Q
    LOAD_Q --> MATRIX
    MATRIX --> RANDOM
    RANDOM --> RUN

    VIDX --> RETRIEVER
    BIDX --> RETRIEVER

    RUN --> AGENT
    AGENT --> LLM
    LLM -->|tool_use| SEARCH
    SEARCH --> RETRIEVER
    RETRIEVER -->|chunks| LLM
    LLM -->|answer + thinking| AGENT
    AGENT --> MAIN_CSV
    RUN --> TEMPLATE_CSV

    MAIN_CSV --> AJ
    AJ -->|rewrites in place| MAIN_CSV
    MAIN_CSV --> RJ
    RJ -->|rewrites in place| MAIN_CSV

    MAIN_CSV -.->|would feed, if called| MERGE
    MERGE -.-> JMP
    MAIN_CSV ==>|actually happens: manual export, no RGS| JMP

    classDef input fill:#e1f5fe
    classDef process fill:#fff3e0
    classDef storage fill:#e8f5e9
    classDef output fill:#fce4ec
    classDef dead fill:#eeeeee,stroke-dasharray: 5 5

    class RULES,QUESTIONS,ENV input
    class CHUNK,CONTEXT,EMBED,LOAD_Q,MATRIX,RANDOM,RUN,AGENT,SEARCH,RETRIEVER,LLM,AJ,RJ process
    class VIDX,BIDX storage
    class MAIN_CSV,TEMPLATE_CSV output
    class MERGE,JMP dead
```

## Data Transformation Summary

### Input Files

| File | Format | Contents |
|------|--------|----------|
| `ClueRules.md` | Markdown (git-ignored) | Official Clue game rules, chunked on `## ` headers |
| `ClueQuestions.csv` | CSV | 31 questions: `Number, Question, Type` (S/M/F) |
| `.env` | Dotenv | API keys + per-role `MODEL_NAME`/`MAX_TOKENS`/`THINKING_BUDGET_TOKENS` for agent, AgentJudge, and RefusalJudge |

### Intermediate Data Structures

| Structure | Type | Contents |
|-----------|------|----------|
| chunks | List[str] | ~8 raw text chunks |
| contextualized_chunks | List[str] | ~8 chunks with LLM-generated situating sentence prepended |
| embeddings | List[float[]] | ~8 voyage-3-large vectors, in-memory only |
| design_matrix | List[dict] | 62 randomized run specifications |

### Output Files

| File | Rows | Notes |
|------|------|-------|
| `Output/Ext_ClueRag_CRD.csv` | 62 | The single file enriched in place across all 3 phases — no separate "judged" file exists |
| `Output/scoring_template_CRD.csv` | ~successful rows | Written by `create_scoring_template()`; **nothing downstream reads it** |

## Data Quality Checkpoints

```mermaid
flowchart LR
    subgraph Validation
        V1["31 questions loaded<br/>from ClueQuestions.csv"]
        V2["Design matrix = 62 runs<br/>31 x 2 replicates"]
        V3["Status tracking<br/>SUCCESS vs ERROR"]
        V4["AgentJudge precondition:<br/>C1_correctness populated<br/>before RefusalJudge runs"]
        V5["RGS bounds — N/A,<br/>never computed on this branch"]
    end

    V1 --> V2 --> V3 --> V4 --> V5
```

| Checkpoint | Validation |
|------------|-------------|
| Question Load | Count by type printed (`S=.., M=.., F=..`) |
| Design Matrix | Total runs = questions x replicates = 62 |
| Execution | Track success/failure by question type |
| Judge Ordering | `RefusalJudge.py` raises `RuntimeError` if `C1_correctness` is entirely null |
| Scoring | RGS/groundedness left blank — no automated validation exists because nothing populates them |

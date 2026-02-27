# Data Flow Diagram - RAG Temperature Experiment

```mermaid
flowchart TB
    subgraph Inputs["Input Data Sources"]
        RULES[("ClueRules.md<br/>8 sections")]
        QUESTIONS[("ClueQuestions.csv<br/>31 questions")]
        ENV[(".env<br/>API keys")]
    end

    subgraph Indexing["Document Indexing Pipeline"]
        CHUNK["chunk_by_section()"]
        CONTEXT["add_context()<br/>LLM enhancement"]
        EMBED["generate_embedding()<br/>voyage-3-large"]
        VIDX[("VectorIndex<br/>embeddings")]
        BIDX[("BM25Index<br/>tokens")]
    end

    subgraph Design["RCBD Design"]
        LOAD_Q["Load questions"]
        MATRIX["Create design matrix<br/>31 x 3 = 93 runs"]
        RANDOM["random.shuffle()<br/>complete randomization"]
    end

    subgraph Execution["Experiment Execution Loop"]
        RUN["run_RCBD_temperature_experiment()"]
        AGENT["answer_clue_question()"]
        SEARCH["search_clue_instructions()"]
        RETRIEVER["Retriever.search()"]
        LLM["Claude API<br/>temperature={0.3, 0.5, 0.8}"]
    end

    subgraph Outputs["Output Data"]
        RAW_CSV[("clue_temperature_RCBD.csv<br/>raw results")]
        SCORE_CSV[("responses_to_score_RCBD.csv<br/>scoring template")]
        FINAL_CSV[("final_RCBD_with_rgs.csv<br/>scored with RGS")]
    end

    subgraph Analysis["Statistical Analysis"]
        MANUAL["Manual/LLM Scoring<br/>C1-C5"]
        RGS["Calculate RGS<br/>C1*(C2+C3+C4+C5)/4"]
        JMP["JMP ANOVA<br/>with blocking"]
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
    LLM -->|answer| AGENT
    AGENT --> RAW_CSV

    RAW_CSV --> SCORE_CSV
    SCORE_CSV --> MANUAL
    MANUAL --> RGS
    RGS --> FINAL_CSV
    FINAL_CSV --> JMP

    classDef input fill:#e1f5fe
    classDef process fill:#fff3e0
    classDef storage fill:#e8f5e9
    classDef output fill:#fce4ec

    class RULES,QUESTIONS,ENV input
    class CHUNK,CONTEXT,EMBED,LOAD_Q,MATRIX,RANDOM,RUN,AGENT,SEARCH,RETRIEVER,LLM,MANUAL,RGS,JMP process
    class VIDX,BIDX storage
    class RAW_CSV,SCORE_CSV,FINAL_CSV output
```

## Data Transformation Summary

### Input Files

| File | Format | Contents |
|------|--------|----------|
| `ClueRules.md` | Markdown | Official Clue game rules (8 sections) |
| `ClueQuestions.csv` | CSV | 31 questions: Number, Question, Type (S/M/F) |
| `.env` | Dotenv | `VOYAGE_API_KEY`, `MODEL_NAME`, `MAX_TOKENS` |

### Intermediate Data Structures

| Structure | Type | Contents |
|-----------|------|----------|
| chunks | List[str] | 8 raw text chunks |
| contextualized_chunks | List[str] | 8 enhanced chunks with LLM context |
| embeddings | List[float[]] | 8 x 1024-dim vectors |
| design_matrix | List[dict] | 93 run specifications |

### Output Files

| File | Rows | Key Columns |
|------|------|-------------|
| `clue_temperature_RCBD.csv` | 93 | run_id, block, temp, answer, status |
| `responses_to_score_RCBD.csv` | ~93 | question, answer, C1-C5 (empty) |
| `final_RCBD_with_rgs.csv` | ~93 | All columns + RGS calculated |

## Data Quality Checkpoints

```mermaid
flowchart LR
    subgraph Validation
        V1["31 questions loaded<br/>S=10, M=10, F=11"]
        V2["Design matrix = 93 runs<br/>31 x 3 temps"]
        V3["Blocking structure<br/>S/M/F balanced"]
        V4["Status tracking<br/>SUCCESS vs ERROR"]
        V5["RGS bounds<br/>0.0 to 1.0"]
    end

    V1 --> V2 --> V3 --> V4 --> V5
```

| Checkpoint | Validation |
|------------|------------|
| Question Load | Count by type: S=10, M=10, F=11 |
| Design Matrix | Total runs = questions x temperatures |
| Blocking | Each block has equal treatment coverage |
| Execution | Track success/failure by block and temp |
| Scoring | RGS in valid range, no missing C1-C5 |

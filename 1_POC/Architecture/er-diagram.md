# Entity-Relationship Diagram - Experiment Data Model

```mermaid
erDiagram
    QUESTION {
        int number PK
        string text
        string type "S, M, or F"
    }

    TEMPERATURE_LEVEL {
        string label PK "low, medium, high"
        float value "0.3, 0.5, 0.8"
    }

    BLOCK {
        string type PK "S, M, F"
        string description "Simple, Medium, Full"
    }

    DESIGN_MATRIX_ENTRY {
        int run_id PK
        int question_number FK
        string temperature_level FK
        string block FK
    }

    EXPERIMENT_RUN {
        int run_id PK
        string timestamp
        string answer
        string status "SUCCESS, ERROR"
        string error_message
        int iteration_count
        int retry_count
        int tool_calls_count
        string search_queries
    }

    SCORING {
        int run_id PK, FK
        float C1_correctness "0 or 1"
        float C2_coverage "0-1"
        float C3_citation_presence "0-1"
        float C4_citation_valid "0-1"
        float C5_clarity "0-1"
        float RGS "calculated"
        string scored_by
        string scoring_notes
    }

    CHUNK {
        int chunk_number PK
        string content
        string contextualized_content
        blob embedding
    }

    TOOL_CALL {
        int id PK
        int run_id FK
        string tool_name
        string query
        string result_chunk_ids
    }

    QUESTION ||--o{ DESIGN_MATRIX_ENTRY : "tested at"
    TEMPERATURE_LEVEL ||--o{ DESIGN_MATRIX_ENTRY : "applied to"
    BLOCK ||--o{ DESIGN_MATRIX_ENTRY : "groups"
    QUESTION }o--|| BLOCK : "belongs to"
    DESIGN_MATRIX_ENTRY ||--|| EXPERIMENT_RUN : "produces"
    EXPERIMENT_RUN ||--o| SCORING : "scored as"
    EXPERIMENT_RUN ||--o{ TOOL_CALL : "invokes"
    TOOL_CALL }o--o{ CHUNK : "retrieves"
```

## Entity Descriptions

### Core Entities

| Entity | Description | Cardinality |
|--------|-------------|-------------|
| QUESTION | Experimental questions loaded from CSV | 31 records |
| TEMPERATURE_LEVEL | Treatment factor levels | 3 records |
| BLOCK | Blocking factor (question types) | 3 records |
| DESIGN_MATRIX_ENTRY | Full factorial RCBD design | 93 records |
| EXPERIMENT_RUN | Execution results per run | 93 records |
| SCORING | Manual C1-C5 scores and RGS | 93 records |

### Supporting Entities

| Entity | Description | Cardinality |
|--------|-------------|-------------|
| CHUNK | Document chunks with embeddings | 8 records |
| TOOL_CALL | Search queries made during runs | Variable |

## CSV Schema Mapping

### clue_temperature_RCBD.csv

```
run_id | timestamp | block | question_number | question_type | question_text |
temperature_level | temperature_value | answer | status | error_message |
iteration_count | retry_count | tool_calls_count | search_queries |
C1_correctness | C2_coverage | C3_citation_presence | C4_citation_valid |
C5_clarity | RGS | scored_by | scoring_notes
```

### Relationships Cardinality

| Relationship | Type | Description |
|--------------|------|-------------|
| QUESTION to DESIGN_MATRIX_ENTRY | 1:N | Each question tested 3 times |
| TEMPERATURE_LEVEL to DESIGN_MATRIX_ENTRY | 1:N | Each temp applied 31 times |
| DESIGN_MATRIX_ENTRY to EXPERIMENT_RUN | 1:1 | Each entry run exactly once |
| EXPERIMENT_RUN to SCORING | 1:0..1 | Successful runs scored |
| EXPERIMENT_RUN to TOOL_CALL | 1:N | Each run may have multiple tool calls |

## RCBD Design Verification

```mermaid
flowchart LR
    subgraph DesignCheck["Design Matrix Validation"]
        Q["31 Questions"]
        T["3 Temperatures"]
        B["3 Blocks (S/M/F)"]

        Q --> DM["93 Runs"]
        T --> DM
        B --> |"groups"| Q

        DM --> V1["Each Q appears 3x"]
        DM --> V2["Each T appears 31x"]
        DM --> V3["Each block has ~31 runs"]
    end
```

| Validation | Expected | Formula |
|------------|----------|---------|
| Total runs | 93 | 31 questions x 3 temperatures |
| Runs per question | 3 | 1 per temperature level |
| Runs per temperature | 31 | 1 per question |
| Runs per block | ~31 | Depends on question distribution |

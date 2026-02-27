# Class Diagram - RAG Temperature Experiment

```mermaid
classDiagram
    class VectorIndex {
        -embedding_fn: Callable
        -embeddings: List~float[]~
        -documents: List~dict~
        +__init__(embedding_fn)
        +add_documents(documents)
        +search(query, k) List~Tuple~
    }

    class BM25Index {
        -tokenized_docs: List~List~str~~
        -documents: List~dict~
        -bm25: BM25Okapi
        +__init__()
        +add_documents(documents)
        +search(query, k) List~Tuple~
    }

    class Retriever {
        -bm25_index: BM25Index
        -vector_index: VectorIndex
        -reranker_fn: Callable
        +__init__(bm25_index, vector_index, reranker_fn)
        +add_documents(documents)
        +search(query, k) List~Tuple~
    }

    class AnthropicClient {
        <<external>>
        +messages.create(model, max_tokens, messages, temperature, tools)
    }

    class VoyageAIClient {
        <<external>>
        +embed(texts, model, input_type) EmbedResponse
    }

    class ExperimentConfig {
        <<dataclass>>
        +temperatures: dict
        +model: str
        +max_tokens: int
        +delay_seconds: int
    }

    class DesignMatrixEntry {
        <<dataclass>>
        +question_number: int
        +question_text: str
        +question_type: str
        +block: str
        +temperature_level: str
        +temperature_value: float
    }

    class RunResult {
        <<dataclass>>
        +answer: str
        +iterations: int
        +retries: int
        +error: str | None
        +tool_calls: List~dict~
    }

    class ExperimentOutput {
        <<dataclass>>
        +run_id: int
        +timestamp: str
        +block: str
        +question_number: int
        +question_type: str
        +question_text: str
        +temperature_level: str
        +temperature_value: float
        +answer: str
        +status: str
        +error_message: str
        +iteration_count: int
        +retry_count: int
        +tool_calls_count: int
        +search_queries: str
        +C1_correctness: float
        +C2_coverage: float
        +C3_citation_presence: float
        +C4_citation_valid: float
        +C5_clarity: float
        +RGS: float
        +scored_by: str
        +scoring_notes: str
    }

    class ToolSchema {
        <<interface>>
        +name: str
        +description: str
        +input_schema: JSONSchema
    }

    Retriever --> BM25Index : uses
    Retriever --> VectorIndex : uses
    VectorIndex --> VoyageAIClient : embeddings
    Retriever --> AnthropicClient : reranking

    ExperimentConfig --> DesignMatrixEntry : generates
    DesignMatrixEntry --> RunResult : produces
    RunResult --> ExperimentOutput : writes
```

## Class Descriptions

### Retrieval Classes (from retriever_implementation.py)

| Class | Purpose |
|-------|---------|
| `VectorIndex` | Stores embeddings and performs cosine similarity search |
| `BM25Index` | Stores tokenized documents for BM25 keyword matching |
| `Retriever` | Orchestrates hybrid search with optional reranking |

### External Client Classes

| Class | Purpose |
|-------|---------|
| `AnthropicClient` | Official Anthropic SDK for Claude API calls |
| `VoyageAIClient` | VoyageAI SDK for embedding generation |

### Data Classes (Implicit in Notebook)

| Class | Purpose |
|-------|---------|
| `ExperimentConfig` | Temperature levels, model settings |
| `DesignMatrixEntry` | Single row in RCBD design matrix |
| `RunResult` | Return value from `answer_clue_question()` |
| `ExperimentOutput` | CSV row schema for experiment results |

### Tool Schema

| Field | Description |
|-------|-------------|
| `name` | "search_clue_instructions" |
| `description` | Tool purpose for Claude |
| `input_schema` | JSON Schema with `query` parameter |

## RGS Calculation

```
RGS = C1 x (C2 + C3 + C4 + C5) / 4
```

| Criterion | Description |
|-----------|-------------|
| C1 | Correctness (0 or 1) - Gates the entire score |
| C2 | Coverage (0-1) - Completeness of answer |
| C3 | Citation Presence (0-1) - Whether chunks are cited |
| C4 | Citation Valid (0-1) - Whether citations match content |
| C5 | Clarity (0-1) - Answer readability |

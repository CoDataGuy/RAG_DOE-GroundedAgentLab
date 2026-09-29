# Class Diagram - Clue RAG Evaluation Pipeline

```mermaid
classDiagram
    class VectorIndex {
        -embedding_fn: Callable
        -vectors: List~float[]~
        -documents: List~dict~
        +__init__(embedding_fn)
        +add_documents(documents)
        +search(query, k) List~Tuple~
    }

    class BM25Index {
        -tokenized_docs: List~List~str~~
        -documents: List~dict~
        -idf: dict
        -avg_doc_length: float
        +__init__(k1, b)
        +add_documents(documents)
        +search(query, k) List~Tuple~
    }

    class Retriever {
        -indexes: List~SearchIndex~
        -reranker_fn: Callable
        -k_rrf: int
        +__init__(indexes, reranker_fn)
        +search(query, k) List~Tuple~
    }

    class AnthropicClient {
        <<external>>
        +messages.create(model, max_tokens, messages, system, tools, thinking)
    }

    class VoyageAIClient {
        <<external>>
        +embed(texts, model, input_type) EmbedResponse
    }

    class DesignMatrixEntry {
        <<dict>>
        +question_number: int
        +question_text: str
        +question_type: str
        +replicate: int
    }

    class AgentRunResult {
        <<dict>>
        +answer: str
        +agent_thinking: str
        +iterations: int
        +retries: int
        +error: str
        +tool_calls: List~dict~
        +retrieved_chunks: str
    }

    class ExperimentCsvRow {
        <<CSV row>>
        +run_id: int
        +timestamp: str
        +replicate: int
        +question_number: int
        +question_type: str
        +question_text: str
        +temperature_value: float
        +answer: str
        +agent_thinking: str
        +retrieved_chunks: str
        +status: str
        +error_message: str
        +iteration_count: int
        +retry_count: int
        +tool_calls_count: int
        +search_queries: str
        +C1_correctness: int
        +C2_coverage: int
        +C3_citation_presence: int
        +C4_citation_valid: int
        +C5_clarity: int
        +CorrectRefusal: int
        +ImproperRefusal: int
        +ShouldHaveRefused: int
        +reasoning_C1_to_C5: str
        +reasoning_refusal: str
        +judge_thinking: str
        +scored_by: str
        +scoring_notes: str
        +RGS: float
        +groundedness: str
    }

    class ToolSchema {
        <<interface>>
        +name: str
        +description: str
        +input_schema: JSONSchema
    }

    class AgentJudgeScript {
        <<script>>
        +AGENT_COLS: list
        +extract_json(text) dict
        +run_agent_judge(csv_path)
    }

    class RefusalJudgeScript {
        <<script>>
        +REFUSAL_COLS: list
        +extract_json(text) dict
        +run_refusal_judge(csv_path)
    }

    Retriever --> BM25Index : fuses (RRF)
    Retriever --> VectorIndex : fuses (RRF)
    VectorIndex --> VoyageAIClient : embeddings
    Retriever --> AnthropicClient : reranking (reranker_fn)

    DesignMatrixEntry --> AgentRunResult : answer_clue_question() produces
    AgentRunResult --> ExperimentCsvRow : written by run_CRD_experiment()

    AgentJudgeScript --> ExperimentCsvRow : reads all rows, writes C1-C5 + reasoning + judge_thinking
    AgentJudgeScript --> AnthropicClient : messages.create() per row
    RefusalJudgeScript --> ExperimentCsvRow : reads all rows (gated on C1_correctness), writes refusal flags + reasoning
    RefusalJudgeScript --> AnthropicClient : messages.create() per row
    RefusalJudgeScript ..> AgentJudgeScript : must run after (precondition check)
```

## Class / Structure Descriptions

### Retrieval Classes (`retriever_implementation.py`)

| Class | Purpose |
|-------|---------|
| `VectorIndex` | Stores embeddings; cosine/Euclidean similarity search |
| `BM25Index` | Hand-rolled BM25 keyword search, no external library |
| `Retriever` | Orchestrates hybrid search: RRF fusion of any number of indexes, then optional LLM rerank |

### External Client Classes

| Class | Purpose |
|-------|---------|
| `AnthropicClient` | Official Anthropic SDK — used directly (agent/reranker/contextualizer via `llm_helpers`; both judges via a raw client, no caching wrapper) |
| `VoyageAIClient` | VoyageAI SDK for `voyage-3-large` embeddings |

### Data Structures (all plain dicts / DataFrame rows — no dataclasses in the codebase)

| Structure | Where | Purpose |
|-----------|-------|---------|
| `DesignMatrixEntry` | notebook | One randomized run spec: question + replicate |
| `AgentRunResult` | return of `answer_clue_question()` | Answer + thinking + iteration/retry/error metadata |
| `ExperimentCsvRow` | `Output/Ext_ClueRag_CRD.csv` | The full 35-column schema shared and mutated by all three phases |
| `ToolSchema` | `rag_helpers.tools` | The single tool (`search_clue_instructions`) exposed to the agent |

### Judge Scripts

| Script | Purpose |
|--------|---------|
| `AgentJudge.py` (`run_agent_judge`) | Phase 2 — quality scoring, synchronous, per-row CSV overwrite |
| `RefusalJudge.py` (`run_refusal_judge`) | Phase 3 — refusal scoring; hard-fails if Phase 2 hasn't run |

## RGS Calculation (defined, but dead on this branch)

```
RGS = C1 x (C2 + C3 + C4 + C5) / 4
```

This formula lives only in `scoring_helper.merge_scores()`, which is imported by both notebooks but **never called**. No script in the current pipeline populates the `RGS` column.

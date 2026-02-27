# C4 Component Diagram - RAG Temperature RCBD Experiment

```mermaid
C4Component
    title Component Diagram - RAG Agent Container

    Container_Boundary(rag_agent, "RAG Agent") {
        Component(answer_fn, "answer_clue_question()", "Python Function", "Main agent loop with retry logic, handles tool use cycles")

        Component(system_prompt, "System Prompt", "XML-structured prompt", "Defines agent role, capabilities, and response format")

        Component(chat_fn, "chat()", "Python Function", "Claude API wrapper with timeout and temperature params")

        Component(tool_handler, "Tool Handler", "Python Logic", "Processes tool_use responses, executes search, returns results")
    }

    Container_Boundary(retriever_container, "Retriever Module") {
        Component(retriever_class, "Retriever", "Python Class", "Orchestrates hybrid search: BM25 + Vector + Rerank")

        Component(search_fn, "search_clue_instructions()", "Python Function", "Tool wrapper that formats retrieval results with chunk IDs")

        Component(vector_index, "VectorIndex", "Python Class", "Cosine similarity search on voyage-3-large embeddings")

        Component(bm25_index, "BM25Index", "Python Class", "BM25 keyword matching on tokenized chunks")

        Component(reranker_fn, "reranker_fn()", "Python Function", "LLM-based document reranking via Claude")
    }

    Container_Boundary(embedding_container, "Embedding Pipeline") {
        Component(chunk_fn, "chunk_by_section()", "Python Function", "Splits document by ## markdown headers")

        Component(context_fn, "add_context()", "Python Function", "Enhances chunks with contextual snippets via LLM")

        Component(embed_fn, "generate_embedding()", "Python Function", "VoyageAI API wrapper for voyage-3-large")
    }

    Container_Boundary(experiment_container, "Experiment Runner") {
        Component(rcbd_fn, "run_RCBD_temperature_experiment()", "Python Function", "Creates design matrix, randomizes, executes 90 runs")

        Component(scoring_fn, "create_scoring_template()", "Python Function", "Extracts successful runs for manual scoring")

        Component(merge_fn, "merge_scores()", "Python Function", "Combines scores, calculates RGS = C1*(C2+C3+C4+C5)/4")
    }

    Rel(answer_fn, chat_fn, "Calls with temperature")
    Rel(answer_fn, tool_handler, "Processes tool_use")
    Rel(tool_handler, search_fn, "Executes search")
    Rel(search_fn, retriever_class, "Retrieves chunks")
    Rel(retriever_class, vector_index, "Semantic search")
    Rel(retriever_class, bm25_index, "Keyword search")
    Rel(retriever_class, reranker_fn, "Reranks results")
    Rel(rcbd_fn, answer_fn, "Executes per run")
    Rel(scoring_fn, rcbd_fn, "Uses output CSV")
    Rel(merge_fn, scoring_fn, "Uses scored CSV")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

## Description

This component diagram details the internal components within the RAG Agent and supporting containers.

### RAG Agent Components

| Component | Responsibility |
|-----------|----------------|
| `answer_clue_question()` | Main agent loop with max 5 iterations, 3 retries, timeout handling |
| System Prompt | XML-structured prompt defining agent behavior, citing requirements |
| `chat()` | Anthropic API wrapper accepting temperature, tools, timeout |
| Tool Handler | Processes `tool_use` stop reasons, routes to search function |

### Retriever Components

| Component | Responsibility |
|-----------|----------------|
| `Retriever` | Hybrid search orchestration (imported from retriever_implementation.py) |
| `search_clue_instructions()` | Tool interface returning JSON with chunk_id, content, score |
| `VectorIndex` | Cosine similarity on embeddings |
| `BM25Index` | Keyword frequency matching |
| `reranker_fn()` | LLM-based reranking using Claude |

### Embedding Pipeline Components

| Component | Responsibility |
|-----------|----------------|
| `chunk_by_section()` | Regex split on `\n## ` headers |
| `add_context()` | LLM-generated contextual prefixes |
| `generate_embedding()` | VoyageAI API call for voyage-3-large |

### Experiment Runner Components

| Component | Responsibility |
|-----------|----------------|
| `run_RCBD_temperature_experiment()` | Design matrix creation, randomization, execution loop |
| `create_scoring_template()` | Filters successful runs, creates scoring CSV |
| `merge_scores()` | Calculates RGS, generates final analysis CSV |

# C4 Component Diagram - Clue RAG Evaluation Pipeline

> Covers the **Phase 1 (notebook)** containers only. For the Judge subsystem's components (AgentJudge.py / RefusalJudge.py), see [Judge Design/c4-diagrams.md](Judge%20Design/c4-diagrams.md).

```mermaid
C4Component
    title Component Diagram - Notebook Containers (Phase 1)

    Container_Boundary(rag_agent, "RAG Agent (in-notebook)") {
        Component(answer_fn, "answer_clue_question()", "Python Function", "Main agent loop: tool-use cycles (max 5), retry on transient errors (max 3), captures extended-thinking text")

        Component(system_prompt, "Grounded System Prompt", "AgentPrompts/GroundedSystemPrompt.json", "Forces answers to come only from retrieved chunks; instructs refusal when the tool doesn't return a direct answer")

        Component(chat_fn, "llm_helpers.chat()", "Python Function", "Anthropic Messages API wrapper; applies prompt-caching to the system prompt; accepts tools + thinking params")

        Component(tool_handler, "Tool Handler", "Python Logic (inline in answer_clue_question)", "Processes tool_use responses, invokes search_clue_instructions, appends tool_result and loops")
    }

    Container_Boundary(retriever_container, "Retriever Module (retriever_implementation.py)") {
        Component(retriever_class, "Retriever", "Python Class", "Fuses BM25 + Vector results via Reciprocal Rank Fusion (k_rrf=60), then optionally reranks via LLM")

        Component(search_fn, "search_clue_instructions()", "Python Closure (rag_helpers.build_clue_retriever)", "Tool-callable wrapper; returns top-k chunks as JSON with CHUNK_N ids")

        Component(vector_index, "VectorIndex", "Python Class", "Cosine/Euclidean similarity search over VoyageAI embeddings")

        Component(bm25_index, "BM25Index", "Python Class", "From-scratch BM25 (k1=1.5, b=0.75) keyword search")

        Component(reranker_fn, "reranker_fn()", "Python Function (rag_helpers.py)", "Asks Claude to pick/re-order the k most relevant candidate chunk IDs")
    }

    Container_Boundary(embedding_container, "Embedding / Indexing Pipeline (rag_helpers.py)") {
        Component(chunk_fn, "chunk_by_section()", "Python Function", "Splits ClueRules.md on \\n## headers into ~8 chunks")

        Component(context_fn, "add_context()", "Python Function", "Asks Claude to prepend a short situating sentence per chunk (contextual retrieval)")

        Component(embed_fn, "generate_embedding() closure", "Python Function (notebook)", "VoyageAI API call (voyage-3-large); used both at index-build time and at query time")
    }

    Container_Boundary(experiment_container, "CRD Experiment Runner (notebook)") {
        Component(crd_fn, "run_CRD_experiment()", "Python Function", "Builds the 62-run design matrix (31 questions x 2 replicates), randomizes order, streams one CSV row per run with all judge/RGS columns blank")

        Component(template_fn, "create_scoring_template()", "Python Function (scoring_helper.py)", "Vestigial: writes a manual-scoring CSV that nothing downstream reads")

        Component(merge_fn, "merge_scores()", "Python Function (scoring_helper.py)", "Dead code on this branch: imported but never called. The only place RGS = C1*(C2+C3+C4+C5)/4 is computed anywhere in the codebase")
    }

    Rel(answer_fn, chat_fn, "Calls with temperature=1.0 and thinking enabled")
    Rel(answer_fn, tool_handler, "Delegates on stop_reason == tool_use")
    Rel(tool_handler, search_fn, "Executes search")
    Rel(search_fn, retriever_class, "retriever.search(query, k=3)")
    Rel(retriever_class, vector_index, "Semantic search")
    Rel(retriever_class, bm25_index, "Keyword search")
    Rel(retriever_class, reranker_fn, "Reranks fused top-k")
    Rel(crd_fn, answer_fn, "Calls once per randomized run")
    Rel(crd_fn, template_fn, "Notebook also calls (output unused downstream)")
    Rel(merge_fn, template_fn, "Imported alongside, never invoked")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

## Description

### RAG Agent Components

| Component | Responsibility |
|-----------|----------------|
| `answer_clue_question()` | Main agent loop: max 5 tool-use iterations, 3 retries on transient network errors, captures the `thinking` content block each turn |
| Grounded System Prompt | Defines `<answer_rules>` (source / no_answer / no_training_data / authority) — the active variant (`USE_GROUNDED_PROMPT = True`) |
| `llm_helpers.chat()` | Anthropic API wrapper; wraps `system` text in a `cache_control: ephemeral` block automatically |
| Tool Handler | Inline logic in `answer_clue_question()` that processes `tool_use` blocks and appends `tool_result` messages |

### Retriever Components

| Component | Responsibility |
|-----------|----------------|
| `Retriever` | RRF fusion of any number of `SearchIndex`-protocol sources, optional `reranker_fn` pass |
| `search_clue_instructions()` | The one tool exposed to the agent; returns JSON chunks with `CHUNK_N` ids |
| `VectorIndex` | Distance-based ranking over in-memory embeddings (lost on kernel restart — no vector DB) |
| `BM25Index` | Hand-rolled BM25 with a regex tokenizer |
| `reranker_fn()` | LLM call asking Claude to select/reorder candidate chunk ids |

### Embedding / Indexing Pipeline Components

| Component | Responsibility |
|-----------|----------------|
| `chunk_by_section()` | Regex split of `ClueRules.md` on `## ` headers |
| `add_context()` | LLM-generated contextual prefix per chunk, written to `Output/ContextualizedChunkedInstructions.txt` |
| `generate_embedding()` | VoyageAI `voyage-3-large` embedding call |

### CRD Experiment Runner Components

| Component | Responsibility |
|-----------|----------------|
| `run_CRD_experiment()` | Builds and randomizes the 62-run design matrix, streams the initial CSV (35 columns, judge/RGS columns blank) |
| `create_scoring_template()` | Still called every run; **output is not read by anything downstream** on this branch — treat as vestigial |
| `merge_scores()` | **Dead code**: imported in both notebooks, never called. It is the only code in the repository that computes RGS |

> For `AgentJudge.py` and `RefusalJudge.py` component-level detail (env/config loading, prompt loading, CSV row iteration, JSON extraction, retry-on-429 handling), see [Judge Design/c4-diagrams.md](Judge%20Design/c4-diagrams.md).

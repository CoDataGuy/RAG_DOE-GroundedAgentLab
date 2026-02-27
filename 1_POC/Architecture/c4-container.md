# C4 Container Diagram - RAG Temperature RCBD Experiment

```mermaid
C4Container
    title Container Diagram - RAG Temperature Experiment System

    Person(researcher, "Researcher", "Runs experiment and scores responses")

    System_Boundary(experiment_system, "RAG Temperature Experiment") {
        Container(notebook, "Jupyter Notebook", "Python/IPython", "Orchestrates RCBD experiment workflow, manages API calls, collects results")

        Container(retriever, "Retriever Module", "Python", "Hybrid search using BM25 + Vector similarity with LLM reranking")

        Container(rag_agent, "RAG Agent", "Python", "Tool-using LLM agent that answers Clue game questions with citations")

        ContainerDb(vector_index, "Vector Index", "In-Memory", "Stores document embeddings for semantic search")

        ContainerDb(bm25_index, "BM25 Index", "In-Memory", "Stores document terms for keyword search")

        ContainerDb(csv_output, "Experiment CSV", "CSV Files", "Stores run results, scores, and RGS calculations")
    }

    System_Ext(anthropic_api, "Anthropic Claude API", "LLM for answers and reranking")
    System_Ext(voyageai_api, "VoyageAI API", "Embedding generation")
    System_Ext(clue_rules, "Clue Rules Document", "Source knowledge base (ClueRules.md)")
    System_Ext(questions_csv, "Questions CSV", "Experimental questions (ClueQuestions.csv)")

    Rel(researcher, notebook, "Executes cells, reviews output")
    Rel(notebook, retriever, "Retrieves relevant chunks")
    Rel(notebook, rag_agent, "Runs question-answer cycles")
    Rel(retriever, vector_index, "Semantic search")
    Rel(retriever, bm25_index, "Keyword search")
    Rel(rag_agent, csv_output, "Writes results")
    Rel(rag_agent, anthropic_api, "LLM completions at varied temps")
    Rel(retriever, anthropic_api, "LLM reranking")
    Rel(retriever, voyageai_api, "Generates embeddings")
    Rel(notebook, clue_rules, "Loads and chunks")
    Rel(notebook, questions_csv, "Loads experiment questions")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Description

This container diagram shows the internal containers within the RAG Temperature Experiment system.

### Containers

| Container | Technology | Purpose |
|-----------|------------|---------|
| Jupyter Notebook | Python/IPython | Main orchestration layer for the RCBD experiment |
| Retriever Module | Python | Hybrid retrieval combining BM25 and vector search |
| RAG Agent | Python | Tool-using agent that answers questions with citations |
| Vector Index | In-Memory | Stores voyage-3-large embeddings for semantic similarity |
| BM25 Index | In-Memory | Stores tokenized documents for keyword matching |
| Experiment CSV | CSV Files | Persists experiment results and scoring data |

### External Dependencies

| System | Purpose |
|--------|---------|
| Anthropic Claude API | claude-haiku-4-5 model for Q&A and reranking |
| VoyageAI API | voyage-3-large model for embeddings |
| Clue Rules Document | Source knowledge base (8 chunks) |
| Questions CSV | 31 experimental questions (S/M/F types) |

### Data Flow Summary
1. Notebook loads and chunks Clue rules
2. Chunks are embedded via VoyageAI and indexed
3. Questions are loaded from CSV
4. RCBD design matrix is created and randomized
5. RAG Agent processes each question at assigned temperature
6. Results are written to CSV for scoring and analysis

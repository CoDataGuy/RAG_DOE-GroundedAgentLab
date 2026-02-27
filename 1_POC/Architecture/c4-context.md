# C4 Context Diagram - RAG Temperature RCBD Experiment

```mermaid
C4Context
    title System Context Diagram - RAG Temperature Experiment

    Person(researcher, "Researcher", "Conducts RCBD experiment to evaluate LLM temperature effects on RAG accuracy")

    System(rag_experiment, "RAG Temperature Experiment", "Jupyter notebook-based experimental system that tests LLM temperature effects on Rule Grounding Score using RCBD methodology")

    System_Ext(anthropic_api, "Anthropic Claude API", "Large Language Model API providing claude-haiku-4-5 for question answering and reranking")

    System_Ext(voyageai_api, "VoyageAI API", "Embedding service providing voyage-3-large model for semantic vector generation")

    System_Ext(jmp_stats, "JMP Statistical Software", "Statistical analysis tool for ANOVA with blocking")

    Rel(researcher, rag_experiment, "Runs experiment, scores responses", "Jupyter/Python")
    Rel(rag_experiment, anthropic_api, "Sends prompts, receives completions", "HTTPS/REST")
    Rel(rag_experiment, voyageai_api, "Generates embeddings", "HTTPS/REST")
    Rel(researcher, jmp_stats, "Imports results, runs ANOVA", "CSV import")
    Rel(rag_experiment, jmp_stats, "Exports experiment data", "CSV files")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## Description

This context diagram shows the RAG Temperature RCBD Experiment system and its interactions with external systems and users.

### Actors
- **Researcher**: The human operator who designs and runs the experiment, manually scores responses, and performs statistical analysis

### Systems
- **RAG Temperature Experiment**: The core Jupyter notebook system that orchestrates the RCBD experiment
- **Anthropic Claude API**: External LLM service for generating answers and reranking documents
- **VoyageAI API**: External embedding service for semantic search
- **JMP Statistical Software**: External tool for ANOVA analysis with blocking

### Key Relationships
1. Researcher interacts with the notebook to configure and run experiments
2. System calls Anthropic API for LLM completions at varying temperatures
3. System calls VoyageAI for document embeddings
4. Results are exported to CSV for JMP analysis

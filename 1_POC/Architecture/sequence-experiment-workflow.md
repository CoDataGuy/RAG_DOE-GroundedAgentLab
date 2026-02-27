# Sequence Diagram - RCBD Experiment Workflow

```mermaid
sequenceDiagram
    autonumber
    participant R as Researcher
    participant NB as Notebook
    participant RET as Retriever
    participant VA as VoyageAI API
    participant AGT as RAG Agent
    participant CL as Claude API
    participant CSV as CSV Output

    rect rgb(230, 245, 255)
        Note over R,CSV: Phase 1: Setup & Indexing
        R->>NB: Execute setup cells
        NB->>NB: Load ClueRules.md
        NB->>NB: chunk_by_section() -> 8 chunks

        loop For each chunk
            NB->>CL: add_context() - enhance chunk
            CL-->>NB: Contextual prefix
        end

        loop For each contextualized chunk
            NB->>VA: generate_embedding()
            VA-->>NB: Embedding vector
        end

        NB->>RET: add_documents(chunks)
        RET->>RET: Build VectorIndex
        RET->>RET: Build BM25Index
    end

    rect rgb(255, 245, 230)
        Note over R,CSV: Phase 2: RCBD Design
        R->>NB: Execute RCBD cell
        NB->>NB: Load ClueQuestions.csv (31 questions)
        NB->>NB: Create design matrix (93 runs)
        Note right of NB: 31 questions x 3 temperatures
        NB->>NB: random.shuffle(design_matrix)
        Note right of NB: Complete randomization
    end

    rect rgb(230, 255, 230)
        Note over R,CSV: Phase 3: Experiment Execution
        loop For each of 93 runs (randomized order)
            NB->>AGT: answer_clue_question(question, temperature)
            AGT->>CL: chat(messages, temperature=T)

            alt stop_reason == "tool_use"
                CL-->>AGT: Tool use request
                AGT->>RET: search_clue_instructions(query)
                RET->>RET: BM25 search
                RET->>RET: Vector search
                RET->>CL: reranker_fn(docs, query)
                CL-->>RET: Ranked doc IDs
                RET-->>AGT: Top-k chunks with scores
                AGT->>CL: chat(messages + tool_result)
                CL-->>AGT: Final answer with citations
            else stop_reason == "end_turn"
                CL-->>AGT: Direct answer
            end

            AGT-->>NB: {answer, iterations, error, tool_calls}
            NB->>CSV: Write row (run_id, block, temp, answer, ...)
            NB->>NB: time.sleep(3s)
        end
    end

    rect rgb(255, 230, 245)
        Note over R,CSV: Phase 4: Scoring & Analysis
        NB->>CSV: create_scoring_template()
        R->>CSV: Manual scoring (C1-C5)
        NB->>CSV: merge_scores() -> Calculate RGS
        R->>R: Import to JMP for ANOVA
    end
```

## Workflow Phases

### Phase 1: Setup & Indexing
- Load Clue rules document (ClueRules.md)
- Split into 8 chunks by `## ` headers
- Enhance each chunk with LLM-generated context
- Generate embeddings via VoyageAI
- Build hybrid index (Vector + BM25)

### Phase 2: RCBD Design
- Load 31 experimental questions from CSV
- Create full factorial design matrix (31 x 3 = 93 runs)
- Apply complete randomization to eliminate order effects

### Phase 3: Experiment Execution (per run)
1. Call RAG Agent with question and assigned temperature
2. Agent queries Claude API
3. If tool use requested:
   - Execute hybrid search
   - Rerank results with LLM
   - Return to Claude with context
4. Record answer, metadata, tool calls to CSV
5. Delay 3 seconds between runs

### Phase 4: Scoring & Analysis
1. Create scoring template (successful runs only)
2. Manual scoring: C1-C5 criteria
3. Calculate RGS = C1 x (C2+C3+C4+C5) / 4
4. Import to JMP for blocked ANOVA

## Audit Trail

| Checkpoint | Data Captured |
|------------|---------------|
| Run Start | timestamp, run_id, block, question, temperature |
| Tool Call | search query, retrieved chunks |
| Run End | answer, iterations, retries, error status |
| Scoring | C1-C5 values, scorer identity, notes |
| Analysis | RGS calculation, statistical model |

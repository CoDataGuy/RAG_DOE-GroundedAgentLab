# State Diagram - RAG Agent Tool Use Loop

```mermaid
stateDiagram-v2
    [*] --> Initializing: answer_clue_question() called

    state Initializing {
        [*] --> LoadSystemPrompt
        LoadSystemPrompt --> PrepareMessages
        PrepareMessages --> [*]
    }

    Initializing --> AwaitingResponse: Send to Claude API

    state AwaitingResponse {
        [*] --> WaitingForLLM
        WaitingForLLM --> CheckTimeout: Response or timeout
    }

    AwaitingResponse --> ProcessingResponse: Response received
    AwaitingResponse --> RetryLogic: Timeout/Connection Error

    state RetryLogic {
        [*] --> CheckRetryCount
        CheckRetryCount --> Wait5s: retries < 3
        Wait5s --> [*]: Retry
        CheckRetryCount --> Failed: retries >= 3
    }

    RetryLogic --> AwaitingResponse: Retry attempt
    RetryLogic --> [*]: Max retries exceeded

    state ProcessingResponse {
        [*] --> CheckStopReason
        CheckStopReason --> EndTurn: stop_reason == "end_turn"
        CheckStopReason --> ToolUse: stop_reason == "tool_use"
    }

    ProcessingResponse --> Success: End turn
    ProcessingResponse --> ExecutingTool: Tool use requested

    state ExecutingTool {
        [*] --> ParseToolCall
        ParseToolCall --> SearchClueInstructions: tool == "search_clue_instructions"
        SearchClueInstructions --> HybridSearch
        HybridSearch --> BM25Search
        HybridSearch --> VectorSearch
        BM25Search --> MergeResults
        VectorSearch --> MergeResults
        MergeResults --> LLMRerank
        LLMRerank --> FormatResults
        FormatResults --> [*]
    }

    ExecutingTool --> AwaitingResponse: Return tool result
    ExecutingTool --> CheckIterations: Iteration complete

    state CheckIterations {
        [*] --> CountCheck
        CountCheck --> Continue: iterations < 5
        CountCheck --> MaxIterations: iterations >= 5
    }

    CheckIterations --> AwaitingResponse: Continue loop
    CheckIterations --> [*]: Max iterations

    Success --> [*]: Return answer

    note right of AwaitingResponse
        Parameters:
        - temperature: {0.3, 0.5, 0.8}
        - timeout: 60s
        - max_iterations: 5
        - max_retries: 3
    end note

    note right of ExecutingTool
        Tool: search_clue_instructions
        Returns: JSON with chunk_id,
        content, score
    end note
```

## Agent States

| State | Description |
|-------|-------------|
| **Initializing** | Load system prompt, prepare message list |
| **AwaitingResponse** | Waiting for Claude API response with timeout |
| **ProcessingResponse** | Check stop_reason to determine next action |
| **ExecutingTool** | Run search_clue_instructions with hybrid retrieval |
| **RetryLogic** | Handle timeout/connection errors with backoff |
| **CheckIterations** | Enforce max 5 tool use cycles |
| **Success** | Return complete answer with citations |

## Error Handling Matrix

| Error Type | Action | Recovery |
|------------|--------|----------|
| APITimeoutError | Retry if iteration=0 | Up to 3 retries |
| APIConnectionError | Retry if iteration=0 | Up to 3 retries |
| RateLimitError | Return error | No retry |
| Mid-conversation timeout | Return error | Cannot retry (state lost) |
| Tool execution error | Return JSON error | Continue iteration |
| Max iterations | Return apology | Graceful degradation |

## Tool Call Flow

```mermaid
flowchart LR
    subgraph ToolExecution["Tool Execution Detail"]
        A["Parse tool_use block"] --> B["Extract query"]
        B --> C["search_clue_instructions(query)"]
        C --> D["Retriever.search(query, k=3)"]
        D --> E["Format JSON response"]
        E --> F["Add tool_result to messages"]
        F --> G["Send back to Claude"]
    end
```

## Return Value Structure

```json
{
    "answer": "According to CHUNK_X, ...",
    "iterations": 2,
    "retries": 0,
    "error": null,
    "tool_calls": [
        {"tool": "search_clue_instructions", "query": "player count"}
    ]
}
```

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
    AwaitingResponse --> RetryLogic: Timeout/Connection Error (only if iteration_count == 0)

    state RetryLogic {
        [*] --> CheckRetryCount
        CheckRetryCount --> Wait5s: retries < 3
        Wait5s --> [*]: Retry
        CheckRetryCount --> Failed: retries >= 3
    }

    RetryLogic --> AwaitingResponse: Retry attempt
    RetryLogic --> [*]: Max retries exceeded

    state ProcessingResponse {
        [*] --> ExtractThinking
        ExtractThinking --> CheckStopReason: capture "thinking" content block
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
    CheckIterations --> [*]: Max iterations -> apology answer, error="max_iterations_reached"

    Success --> [*]: Return {answer, agent_thinking, iterations, retries, error, tool_calls, retrieved_chunks}

    note right of AwaitingResponse
        Parameters:
        - temperature: 1.0 (fixed — required by Extended Thinking)
        - thinking: {"type":"enabled","budget_tokens":THINKING_BUDGET_TOKENS}
        - timeout: 120s
        - max_iterations: 5
        - max_retries: 3
    end note

    note right of ExecutingTool
        Tool: search_clue_instructions
        Returns JSON: CHUNK_N id, content
        (via Retriever RRF fusion + LLM rerank)
    end note
```

## Agent States

| State | Description |
|-------|-------------|
| **Initializing** | Load system prompt (Grounded variant), prepare message list |
| **AwaitingResponse** | Waiting for Claude API response with 120s timeout |
| **ProcessingResponse** | Extract `thinking` block, check `stop_reason` to determine next action |
| **ExecutingTool** | Run `search_clue_instructions` with hybrid retrieval + rerank |
| **RetryLogic** | Handle timeout/connection errors — only retryable if no iteration has started yet (mid-conversation timeouts cannot be retried, state is lost) |
| **CheckIterations** | Enforce max 5 tool-use cycles |
| **Success** | Return complete result dict including `agent_thinking` |

## Error Handling Matrix

| Error Type | Action | Recovery |
|------------|--------|----------|
| `APITimeoutError` / `APIConnectionError` | Retry only if `iteration_count == 0` | Up to 3 retries, 5s delay |
| Same errors mid-conversation (`iteration_count > 0`) | Return error immediately | Cannot retry — conversation state would be lost |
| `RateLimitError` | Return error immediately | No retry inside the agent loop |
| Tool execution error | Return JSON error as the tool_result | Continue the iteration loop |
| Max iterations (5) reached | Return apology answer | `error = "max_iterations_reached"` |

## Tool Call Flow

```mermaid
flowchart LR
    subgraph ToolExecution["Tool Execution Detail"]
        A["Parse tool_use block"] --> B["Extract query"]
        B --> C["search_clue_instructions(query)"]
        C --> D["Retriever.search(query, k=3)"]
        D --> E["Format JSON response with CHUNK_N ids"]
        E --> F["Append tool_result to messages"]
        F --> G["Send back to Claude"]
    end
```

## Return Value Structure

```json
{
    "answer": "According to CHUNK_2, ...",
    "agent_thinking": "The user is asking about ...",
    "iterations": 2,
    "retries": 0,
    "error": null,
    "tool_calls": [
        {"tool": "search_clue_instructions", "query": "player count"}
    ],
    "retrieved_chunks": "..."
}
```

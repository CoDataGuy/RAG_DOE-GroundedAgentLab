# LLM Judge — C4 Architecture Diagrams

> Rewritten for the current synchronous design (`AgentJudge.py` + `RefusalJudge.py`). The previous version of this file described the deleted async `judge_submit.py`/`judge_retrieve.py` Batches-API design — that design no longer exists in the codebase.

All diagrams use [Mermaid](https://mermaid.js.org/) and render in GitHub, VS Code (with Markdown Preview Mermaid Support), and [mermaid.live](https://mermaid.live).

---

## Level 1 — C4 Context

```mermaid
C4Context
    title LLM Judge — System Context

    Person(researcher, "Researcher", "Runs AgentJudge.py, then RefusalJudge.py, and reviews the scored CSV")

    System(judge, "LLM Judge", "Two sequential, synchronous scripts that score each RAG agent response for quality (C1-C5) and refusal behaviour, one Claude call per row")

    System_Ext(rag_experiment, "RAG Experiment (Notebook)", "Produces Output/Ext_ClueRag_CRD.csv with agent answers, thinking, and retrieved chunks")

    System_Ext(anthropic_api, "Anthropic Claude API", "Real-time Messages API (messages.create), not the Batches API. Extended thinking enabled on every call")

    Rel(researcher, judge, "python Judge/AgentJudge.py, then python Judge/RefusalJudge.py", "CLI / Python")
    Rel(rag_experiment, judge, "Produces input data", "Output/Ext_ClueRag_CRD.csv")
    Rel(judge, anthropic_api, "One messages.create() call per CSV row, per script", "HTTPS / Anthropic Python SDK")
    Rel(judge, researcher, "Enriches the same CSV in place with scores + reasoning", "Output/Ext_ClueRag_CRD.csv")
```

---

## Level 2 — C4 Container

```mermaid
C4Container
    title LLM Judge — Container Diagram

    Person(researcher, "Researcher", "Runs both scripts, in order")

    System_Ext(anthropic_api, "Anthropic Claude API", "Real-time Messages API")

    System_Boundary(judge_system, "LLM Judge") {

        Container(agent_judge, "AgentJudge.py", "Python script", "Reads the CSV, sends QUESTION+ANSWER+CHUNKS per row to the quality rubric, writes C1-C5 + reasoning + judge_thinking back, one row at a time")

        Container(refusal_judge, "RefusalJudge.py", "Python script", "Reads the CSV (after checking AgentJudge has run), sends QUESTION+ANSWER+AGENT_THINKING per row to the refusal rubric, writes 3 flags + reasoning back")

        ContainerDb(agent_prompt, "JudgeAgentPrompt.json", "JSON config", "Quality rubric: C1 correctness, C2 coverage, C3 citation presence, C4 citation valid, C5 clarity — refusal explicitly out of scope")

        ContainerDb(refusal_prompt, "JudgeRefusalPrompt.json", "JSON config", "Scope definition + refusal detection heuristics + 3 mutually-near-exclusive flags")

        ContainerDb(scoring_sheet, "Output/Ext_ClueRag_CRD.csv", "CSV (read AND written by both scripts)", "The single scoring sheet — no separate input/output file split")
    }

    Rel(researcher, agent_judge, "Runs first", "python Judge/AgentJudge.py")
    Rel(researcher, refusal_judge, "Runs second", "python Judge/RefusalJudge.py")

    Rel(agent_judge, agent_prompt, "Reads, joins system_prompt list")
    Rel(agent_judge, scoring_sheet, "pd.read_csv() all rows; pd.to_csv() after every row")
    Rel(agent_judge, anthropic_api, "messages.create(), thinking enabled, retry once on 429")

    Rel(refusal_judge, refusal_prompt, "Reads, joins system_prompt list")
    Rel(refusal_judge, scoring_sheet, "pd.read_csv(); asserts C1_correctness not all-null; pd.to_csv() after every row")
    Rel(refusal_judge, anthropic_api, "messages.create(), thinking enabled, retry once on 429")

    Rel(refusal_judge, agent_judge, "Hard precondition: raises RuntimeError if AgentJudge has not run", "reads C1_correctness column")
```

**No `batch_id.txt`, no Batches API, no separate `judged_*.csv`.** Both scripts open the *same* file for both read and write, and the file is rewritten to disk after every single row (durability over throughput) rather than once at the end.

---

## Level 3 — C4 Component: AgentJudge.py

```mermaid
C4Component
    title AgentJudge.py — Component Diagram

    System_Ext(anthropic_api, "Anthropic Claude API")

    Container_Boundary(agent_judge, "AgentJudge.py") {

        Component(env_loader, "Env Loader", "dotenv / os.getenv", "ANTHROPIC_API_KEY, AGENT_JUDGE_MODEL_NAME, AGENT_JUDGE_MAX_TOKENS (default 3000), AGENT_JUDGE_THINKING_BUDGET_TOKENS (default 8000)")

        Component(prompt_loader, "Prompt Loader", "json.load", "Reads JudgeAgentPrompt.json, joins system_prompt list into one string")

        Component(csv_io, "CSV Reader/Writer", "pandas", "read_csv() once; _ensure_columns() adds any missing AGENT_COLS; to_csv() after every row")

        Component(row_loop, "Row Iterator", "for idx, row in df.iterrows()", "Builds 'QUESTION + ANSWER + CHUNKS' user message per row")

        Component(api_call, "Messages API Call", "client.messages.create()", "Real-time call, thinking enabled, no tools; direct anthropic.Anthropic client (no llm_helpers, no prompt-cache wrapper)")

        Component(retry_handler, "Retry/Rate-limit Handler", "except anthropic.RateLimitError", "On 429: sleep 60s, retry once; on any other exception: null the score columns, record error in scoring_notes")

        Component(json_extractor, "JSON Extractor", "extract_json() — regex + json.loads", "Regex matches one level of nested braces, takes the LAST match, tolerating <evaluate_cN> reasoning preamble before the JSON")

        Component(column_writer, "Column Writer", "df.loc[df.run_id==run_id, col] = ...", "Writes C1-C5, reasoning_C1-C5, judge_thinking, scored_by='AgentJudge', scoring_notes back into the shared DataFrame, keyed by run_id")
    }

    Rel(env_loader, api_call, "Provides API key + model config")
    Rel(prompt_loader, api_call, "Provides system prompt")
    Rel(csv_io, row_loop, "Provides rows to iterate")
    Rel(row_loop, api_call, "Sends one request per row")
    Rel(api_call, retry_handler, "On RateLimitError")
    Rel(retry_handler, api_call, "Retries once after 60s sleep")
    Rel(api_call, json_extractor, "Passes response text block")
    Rel(json_extractor, column_writer, "Passes parsed score dict")
    Rel(column_writer, csv_io, "Triggers to_csv() after every row")
```

---

## Level 3 — C4 Component: RefusalJudge.py

```mermaid
C4Component
    title RefusalJudge.py — Component Diagram

    System_Ext(anthropic_api, "Anthropic Claude API")

    Container_Boundary(refusal_judge, "RefusalJudge.py") {

        Component(env_loader2, "Env Loader", "dotenv / os.getenv", "ANTHROPIC_API_KEY, REFUSAL_JUDGE_MODEL_NAME, REFUSAL_AGENT_JUDGE_MAX_TOKENS (default 3000), REFUSAL_AGENT_JUDGE_THINKING_BUDGET_TOKENS (default 8000)")

        Component(precondition, "Precondition Check", "df['C1_correctness'].isnull().all()", "Raises RuntimeError('AgentJudge scores not found. Run AgentJudge first.') if AgentJudge has not populated any scores")

        Component(prompt_loader2, "Prompt Loader", "json.load", "Reads JudgeRefusalPrompt.json, joins system_prompt list")

        Component(csv_io2, "CSV Reader/Writer", "pandas", "read_csv() once (after the precondition check); _ensure_columns() adds REFUSAL_COLS; to_csv() after every row")

        Component(row_loop2, "Row Iterator", "for idx, row in df.iterrows()", "Builds 'QUESTION + ANSWER + AGENT_THINKING' user message per row — uses the agent's own thinking trace, not retrieved_chunks")

        Component(api_call2, "Messages API Call", "client.messages.create()", "Real-time call, thinking enabled, no tools")

        Component(retry_handler2, "Retry/Rate-limit Handler", "except anthropic.RateLimitError", "On 429: sleep 60s, retry once; on any other exception: null the 3 flags, record error in reasoning_refusal")

        Component(json_extractor2, "JSON Extractor", "extract_json() — same regex as AgentJudge", "Extracts CorrectRefusal/ImproperRefusal/ShouldHaveRefused + nested reasoning object")

        Component(column_writer2, "Column Writer", "df.loc[...] = ...", "Writes CorrectRefusal, ImproperRefusal, ShouldHaveRefused, and a flattened reasoning_refusal string ('SCOPE: .. | REFUSAL: .. | FLAGS: ..')")
    }

    Rel(csv_io2, precondition, "Runs check immediately after read_csv()")
    Rel(precondition, prompt_loader2, "Proceeds only if C1_correctness has at least one value")
    Rel(row_loop2, api_call2, "Sends one request per row")
    Rel(api_call2, retry_handler2, "On RateLimitError")
    Rel(api_call2, json_extractor2, "Passes response text block")
    Rel(json_extractor2, column_writer2, "Passes parsed flags + reasoning")
    Rel(column_writer2, csv_io2, "Triggers to_csv() after every row")
```

---

## Diagram Notes

- Both scripts are near-duplicates of each other in structure; the meaningful differences are: (1) which prompt/rubric they load, (2) what evidence goes in the user message (`retrieved_chunks` for AgentJudge vs. `agent_thinking` for RefusalJudge), and (3) RefusalJudge's hard precondition on AgentJudge having already run.
- Neither script uses `llm_helpers.chat()` — they instantiate `anthropic.Anthropic()` directly, so they do **not** get the automatic prompt-caching wrapper that the notebook's agent/reranker/contextualizer calls get, even though the rubric system prompts are long and reused across all 62 rows.
- Config note to verify: `.env` defines the key as `REFUSAL_JUDGE_MODEL_NAME ` with a space before `=` (`REFUSAL_JUDGE_MODEL_NAME = claude-sonnet-4-6`). Most `python-dotenv` versions trim this correctly, but it's worth confirming `os.getenv("REFUSAL_JUDGE_MODEL_NAME")` actually resolves rather than silently returning `None` (which would pass `model=None` to `messages.create()` and fail loudly at call time, not silently).
- For the RAG agent, retriever, and notebook side of the pipeline, see [/Solution Documentation/diagrams/](../c4-context.md).

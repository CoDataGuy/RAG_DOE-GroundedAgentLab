# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A RAG (Retrieval-Augmented Generation) evaluation pipeline. An LLM agent answers a bank of questions about the rules of the board game Clue using a hybrid retriever, and two separate LLM-as-judge scripts then score every answer for quality and for refusal behaviour. See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for a 1-page summary and [Solution Documentation/diagrams/](Solution%20Documentation/diagrams/README.md) for full C4 and UML (sequence/state/class/ER) diagrams — consult those before re-deriving architecture from scratch.

There is no test suite, linter, or dependency manifest (`requirements.txt`/`pyproject.toml`) in this repo.

## Commands

Install dependencies manually (no manifest file exists):
```
pip install anthropic voyageai pandas python-dotenv
```

Run the 3 phases **in order** — there is no orchestrator, each is run manually:

```bash
# Phase 1 — open and run cells in Jupyter (writes Output/Ext_ClueRag_CRD.csv)
# Notebooks/10qExt_ClueRag_CRD.ipynb   — 10-question smoke test
# Notebooks/Ext_ClueRag_CRD.ipynb      — full 62-run experiment

# Phase 2 — quality scoring (must run before Phase 3)
python Judge/AgentJudge.py

# Phase 3 — refusal scoring (hard-fails if Phase 2 hasn't populated C1_correctness)
python Judge/RefusalJudge.py
```

Required `.env` variables: `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `MODEL_NAME`, `MAX_TOKENS`, `THINKING_BUDGET_TOKENS` (agent), `AGENT_JUDGE_MODEL_NAME`/`AGENT_JUDGE_MAX_TOKENS`/`AGENT_JUDGE_THINKING_BUDGET_TOKENS`, `REFUSAL_JUDGE_MODEL_NAME`/`REFUSAL_AGENT_JUDGE_MAX_TOKENS`/`REFUSAL_AGENT_JUDGE_THINKING_BUDGET_TOKENS`.

## Architecture

**Single shared CSV, no orchestrator.** All three phases read and write the *same* file, `Output/Ext_ClueRag_CRD.csv`, in place — there is no separate input/output file split. `Judge/RefusalJudge.py` enforces phase ordering in code, not just convention: it reads the CSV and raises `RuntimeError` if `C1_correctness` is entirely null (i.e. `AgentJudge.py` hasn't run yet).

**Phase 1 (notebook) builds an in-memory retriever every session.** `rag_helpers.build_clue_retriever()` loads `References/ClueRules.md`, splits it into ~8 chunks on `## ` headers, asks Claude to prepend a contextual sentence to each chunk (contextual retrieval), embeds them via VoyageAI, and constructs a `Retriever` (`retriever_implementation.py`) that fuses `BM25Index` + `VectorIndex` results via Reciprocal Rank Fusion before an optional LLM rerank pass. There is no vector database — everything lives in a Python list for the life of the kernel.

**The experiment is a CRD, not an RCBD, and has no active treatment.** `run_CRD_experiment()` builds a 62-run design matrix (31 questions × 2 replicates), fully randomizes run order, and calls `answer_clue_question()` per run. Temperature is fixed at `1.0` for every run — this is an API constraint of Claude's extended thinking, not an experimental treatment. `question_type` (S/M/F) is recorded but not used as a blocking factor by the current code.

**The agent's tool-use loop and both judge scripts each implement their own bespoke retry logic** — there's no shared retry/backoff utility, even though `.env` defines `MAX_RETRIES`/`INITIAL_BACKOFF_SECONDS`/`MAX_BACKOFF_SECONDS` that nothing actually reads. `answer_clue_question()` retries transient network errors (not rate limits) up to 3 times, but only if no tool-use iteration has started yet (mid-conversation state can't be replayed). `AgentJudge.py`/`RefusalJudge.py` each sleep 60s and retry exactly once on a 429, then give up and null out that row's scores.

**Judge scripts bypass the shared LLM helper.** `llm_helpers.chat()` (used by the notebook for the agent, reranker, and chunk-contextualizer) automatically wraps the system prompt in a `cache_control: ephemeral` block for prompt caching. `AgentJudge.py` and `RefusalJudge.py` instead instantiate `anthropic.Anthropic()` directly and call `messages.create()` — they do **not** get prompt caching, despite resending the same long rubric system prompt on every one of the 62 rows.

**The two judges use different evidence.** `AgentJudge.py` (rubric: `Judge/JudgeAgentPrompt.json`) sees `QUESTION + ANSWER + retrieved_chunks` and scores C1–C5 (correctness/coverage/citation presence/citation validity/clarity). `RefusalJudge.py` (rubric: `Judge/JudgeRefusalPrompt.json`) sees `QUESTION + ANSWER + agent_thinking` — the agent's own extended-thinking trace, not the chunks — as supplementary (not authoritative) scope evidence, and scores three flags: `CorrectRefusal`, `ImproperRefusal`, `ShouldHaveRefused`. Both scripts extract JSON from the response via the same regex (`extract_json()`): match one level of nested braces, take the **last** match, `json.loads()` it — this tolerates the `<evaluate_cN>`/`<scope_determination>` chain-of-thought XML tags both rubrics require before the final JSON.

**`scoring_helper.py` is mostly dead/vestigial on this branch.** `create_scoring_template()` is still called by both notebooks but its output CSV isn't read by anything downstream. `merge_scores()` — the *only* place in the codebase that computes `RGS = C1 × (C2+C3+C4+C5) / 4` — is imported by both notebooks but never called. The `RGS`/`groundedness` CSV columns exist in the schema but are always blank; do not assume RGS is populated anywhere.

**Two agent system prompts exist; only one is active.** `AgentPrompts/GroundedSystemPrompt.json` (active, `USE_GROUNDED_PROMPT = True` in both notebooks) adds strict `<answer_rules>` forcing answers to come only from retrieved chunks and refusal otherwise. `AgentPrompts/systemPrompt.json` is the looser base variant, currently unused.

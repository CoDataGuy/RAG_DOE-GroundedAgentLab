# RAG_DOE_TestEval — Project Overview

## Executive Summary

This project is a controlled experiment evaluating how Claude's **temperature parameter** affects RAG (Retrieval-Augmented Generation) answer quality. Using the board game Clue as a bounded knowledge domain, a 3-phase pipeline runs an LLM agent against a question bank, then uses a second LLM-as-Judge to score the answers on grounding, correctness, and citation quality.

**Design:** Randomized Complete Block Design (RCBD) — temperature is the treatment, question type is the blocking factor.
**Stack:** Python 3, Jupyter, Anthropic Claude API, VoyageAI embeddings.
**Models:** `claude-haiku-4-5` (agent), `claude-sonnet-4-6` (judge), `voyage-3-large` (embeddings).
**Status:** v1, single `main` branch, clean working tree.

---

## Solution Architecture — 3-Phase Pipeline

```
Phase 1 (Notebook)           Phase 2 (Script)           Phase 3 (Script)
────────────────────         ─────────────────          ────────────────
Load ClueQuestions.csv       Read raw CSV               Read batch_id.txt
Build Hybrid RAG Index       Build batch payload        Poll Anthropic status
Run Agent Loop (Haiku)       Submit Batch to Anthropic  Download & parse scores
  └─ tool: search_clue()     Save batch_id.txt          Merge scores into CSV
Write raw results CSV                                   Compute RGS metric
                                                        Write judged CSV
```

---

## File & Folder Structure

```
RAG_DOE_TestEval/
│
├── Notebooks/
│   ├── Ext_ClueRag_CRD.ipynb         # Phase 1 — full run (93 trials)
│   └── 10qExt_ClueRag_CRD.ipynb      # Phase 1 — smoke test (10 trials)
│
├── Judge/
│   ├── judge_submit.py               # Phase 2 — submits Anthropic batch job
│   ├── judge_retrieve.py             # Phase 3 — retrieves & merges scores
│   ├── JudgeSystemPrompt.json        # Scoring rubric (6 binary metrics)
│   ├── batch_id.txt                  # Stateless handoff: Phase 2 → Phase 3 (prod)
│   └── 10q_batch_id.txt              # Stateless handoff: Phase 2 → Phase 3 (test)
│
├── Output/
│   ├── Ext_ClueRag_CRD.csv           # Phase 1 raw output (production)
│   ├── 10q_Ext_ClueRag_CRD.csv       # Phase 1 raw output (test)
│   └── judged_Ext_ClueRag_CRD.csv    # Phase 3 final output with scores
│
├── References/
│   ├── ClueRules.md                  # RAG source document (chunked at runtime)
│   ├── ClueQuestions.csv             # 30 questions (S=straightforward, M=marginal, F=fabricated)
│   ├── 10q_Pipeline_Guide.md         # Detailed technical guide with C4 diagrams
│   └── GameInstructions/             # Original Clue rule text variants
│
├── Solution Documentation/
│   └── diagrams/                     # Mermaid diagrams: C4, sequence, ER, state machine
│       ├── README.md
│       ├── c4-context.md
│       ├── c4-container.md
│       ├── c4-component.md
│       ├── sequence-experiment-workflow.md
│       ├── state-rag-agent.md
│       ├── class-diagram.md
│       ├── data-flow.md
│       ├── er-diagram.md
│       └── Judge Design/             # Judge-specific C4 & scoring rubric docs
│
├── AgentPrompts/
│   ├── systemPrompt.json             # Base agent system prompt
│   └── GroundedSystemPrompt.json     # Grounded variant system prompt
│
├── archive/                          # Prior notebook experiments (not active)
│
├── llm_helpers.py                    # Claude API wrapper (chat, messages, extended thinking)
├── rag_helpers.py                    # RAG setup: chunking, context, retriever factory
├── retriever_implementation.py       # VectorIndex, BM25Index, Retriever (RRF fusion)
│
├── .env                              # API keys — git-ignored, never committed
├── .gitignore
└── README.md                         # Minimal changelog (placeholder)
```

---

## Core Python Modules

| File | Purpose | Key Exports |
|---|---|---|
| `llm_helpers.py` | Claude API abstraction | `init()`, `chat()`, `text_from_message()` |
| `rag_helpers.py` | RAG setup & retriever factory | `build_clue_retriever()`, `reranker_fn()` |
| `retriever_implementation.py` | Hybrid retrieval engine | `VectorIndex`, `BM25Index`, `Retriever` |

### Retrieval Design
- **VectorIndex** — semantic search via VoyageAI embeddings (cosine similarity)
- **BM25Index** — keyword search (custom implementation, no external library)
- **Retriever** — fuses both via Reciprocal Rank Fusion (RRF), then optional Claude reranking

### Extended Thinking
Both agent (Phase 1) and judge (Phase 3) use `extended thinking`. Thinking blocks are captured as separate CSV columns for downstream analysis.

---

## Data Model

**Phase 1 CSV** (`Ext_ClueRag_CRD.csv`) — 19 columns including:
`run_id`, `question_type`, `temperature_value`, `answer`, `agent_thinking`, `retrieved_chunks`, `tool_calls_count`

**Phase 3 CSV** (`judged_Ext_ClueRag_CRD.csv`) — Phase 1 + 10 score columns:
`C1_correctness`, `C2_coverage`, `C3_citation_presence`, `C4_citation_valid`, `C5_clarity`, 3 refusal flags, `RGS`

**RGS (Retrieval-Grounded Score):**
```
RGS = C1 × (C2 + C3 + C4 + C5) / 4
```
C1 (correctness) gates the score — a wrong answer yields RGS = 0.

---

## Experimental Design

| Factor | Values |
|---|---|
| Treatment (Temperature) | 0.3, 0.5, 0.8 |
| Block (Question Type) | S (straightforward), M (marginal), F (fabricated/out-of-scope) |
| Questions | 30 total (+ 1 duplicate) |
| Replicates | 1 per question per temperature |
| Total Trials | 93 (production), 10 (smoke test) |

Statistical analysis is done externally in JMP (ANOVA).

---

## GitHub Usage Guide

### Current State
- One branch: `main`
- One commit: `4585133 Initial Commit of v1 project`
- Clean working tree

### Recommended Git Workflow

#### Branch Strategy
Use feature branches for each distinct change or experiment run:

```bash
# Start a new experiment run or code change
git checkout -b experiment/temp-variation-v2
git checkout -b fix/judge-retrieve-parsing
git checkout -b docs/update-diagrams
```

#### What to Commit (and What Not To)

| Include | Exclude (already in .gitignore) |
|---|---|
| `*.py`, `*.ipynb`, `*.json` prompts | `.env` (API keys) |
| `References/*.md`, `*.csv` (questions) | `Output/*.csv` (generated data) |
| `Solution Documentation/` | `__pycache__/` |
| `.gitignore`, `README.md` | `batch_id.txt` (transient state) |

> **Note:** Output CSVs are generated artifacts. Consider whether to track them — they are large and regenerable. If you want reproducibility evidence, commit them on experiment completion only.

#### Typical Commit Sequence

```bash
# After editing code
git add llm_helpers.py rag_helpers.py
git commit -m "fix: handle empty thinking blocks in text_from_message"

# After completing an experiment run
git add Output/judged_Ext_ClueRag_CRD.csv
git commit -m "data: add scored results for v1 temp=0.3/0.5/0.8 run"

# After updating docs
git add "Solution Documentation/"
git commit -m "docs: add ER diagram for judged CSV schema"
```

#### Recommended .gitignore Additions
Consider adding these if not already present:
```
Output/*.csv          # generated — commit selectively
Judge/batch_id.txt    # transient pipeline state
Judge/10q_batch_id.txt
```

#### Useful Git Commands for This Project

```bash
git log --oneline                          # See commit history
git diff HEAD                              # See all uncommitted changes
git status                                 # Check working tree state
git add -p                                 # Stage changes interactively (recommended)
git stash                                  # Temporarily shelve work-in-progress
git tag v1-results                         # Tag a completed experiment milestone
```

#### Milestones Worth Tagging

```bash
git tag -a v1-phase1-complete -m "Phase 1 raw results, all 93 trials"
git tag -a v1-judged -m "Phase 3 complete, judged CSV with RGS scores"
```

---

## Environment Setup

```bash
# 1. Clone repo
git clone <repo-url>
cd RAG_DOE_TestEval

# 2. Install dependencies (no requirements.txt yet — install manually)
pip install anthropic voyageai pandas python-dotenv

# 3. Create .env (never commit this)
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
MODEL_NAME=claude-haiku-4-5-20251001
JUDGE_MODEL_NAME=claude-sonnet-4-6
MAX_TOKENS=2000
THINKING_BUDGET_TOKENS=1500
JUDGE_MAX_TOKENS=5000
JUDGE_THINKING_BUDGET_TOKENS=2000

# 4. Run pipeline
#   Phase 1: Open and run Notebooks/10qExt_ClueRag_CRD.ipynb (smoke test)
#   Phase 2: python Judge/judge_submit.py T
#   Phase 3: python Judge/judge_retrieve.py T  (run after batch completes)
```

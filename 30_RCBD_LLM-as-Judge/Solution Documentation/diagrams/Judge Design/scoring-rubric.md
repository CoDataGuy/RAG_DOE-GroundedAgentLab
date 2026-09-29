# LLM Judge — Scoring Rubric

## 1. Overview

There are two independent rubrics now, one per script:

- [`Judge/JudgeAgentPrompt.json`](../../../Judge/JudgeAgentPrompt.json) — loaded by `AgentJudge.py`. Evaluates 5 quality metrics (C1–C5). Explicitly excludes refusal: *"A separate evaluator handles all refusal logic."*
- [`Judge/JudgeRefusalPrompt.json`](../../../Judge/JudgeRefusalPrompt.json) — loaded by `RefusalJudge.py`. Evaluates 3 refusal flags.

`AgentJudge.py` sees three inputs per row: **QUESTION**, **ANSWER**, **CHUNKS** (`retrieved_chunks`).
`RefusalJudge.py` sees a different three: **QUESTION**, **ANSWER**, **AGENT_THINKING** (`agent_thinking`) — it does not see the retrieved chunks at all.

---

## 2. Quality Metrics (`AgentJudge.py` / `JudgeAgentPrompt.json`)

All metrics are scored **0 or 1 only** — no partial credit.

### 2.1 Lenient Metrics

Apply a *reasonable person standard*: would a reasonable person find the answer useful, true, and natural?

#### C1 — Correctness
| Score | Condition |
|-------|-----------|
| 1 | Answer is factually correct and useful to the user |
| 0 | Answer contains factual errors or is unhelpful |

> Minor omissions are not penalised here — that is C2's responsibility.

#### C2 — Coverage
| Score | Condition |
|-------|-----------|
| 1 | Answer is complete enough for the user to understand the rule or situation |
| 0 | A critical piece of context is missing that would leave a reasonable person confused |

#### C5 — Clarity
| Score | Condition |
|-------|-----------|
| 1 | Answer is written in fluent, natural, idiomatic English |
| 0 | Answer is awkward, confusing, or unnatural to read |

### 2.2 Citation Metrics

Historically framed as purely mechanical/deterministic checks. **The working tree currently has an uncommitted edit** to `JudgeAgentPrompt.json` that adds looser, content-support language to both — see the "in progress" note below.

#### C3 — Citation Presence
| Score | Condition |
|-------|-----------|
| 1 | Answer contains at least one explicit chunk reference in the format `CHUNK_N` |
| 1 *(added, uncommitted)* | The retrieved chunk in `retrieved_chunks` addresses the question |
| 0 | No such reference exists |

#### C4 — Citation Valid
| Score | Condition |
|-------|-----------|
| 1 | The text of every cited `CHUNK_N` supports the claims made in the answer |
| 0 | Any cited chunk does not support the answer, or a cited chunk's text was not provided |

> **In progress on this branch:** the current `JudgeAgentPrompt.json` adds "Score 1 if the retrieved chunk... addresses the question" (C3) and duplicates the content-support line under C3 as well as C4. This moves C3/C4 away from a pure format/mechanical check toward a judgement call, which is a meaningful rubric change worth a deliberate review before merging — it changes what "deterministic" means for these two metrics.

---

## 3. Refusal Metrics (`RefusalJudge.py` / `JudgeRefusalPrompt.json`)

Scope is defined explicitly in the prompt:

- **In scope:** rules, setup, gameplay mechanics, turn structure, win/loss conditions, cards/tokens/rooms/weapons/suspects as components, how to make suggestions/accusations, special rules and edge cases.
- **Out of scope:** design history/intent, strategy/probability/optimal play, cultural commentary, anything not grounded in the retrieved chunks.

The judge makes two independent determinations before scoring: **scope** (question text is the primary source of truth; `agent_thinking` is supplementary, not authoritative) and **refusal detection** (declining to answer, or "I cannot find that in the rules," counts as a refusal; answering a related-but-different question does not).

#### CorrectRefusal
| Score | Condition |
|-------|-----------|
| 1 | Answer **is** a refusal AND the question was genuinely out of scope |
| 0 | Any other case |

#### ImproperRefusal
| Score | Condition |
|-------|-----------|
| 1 | Answer **is** a refusal AND the question was in scope |
| 0 | Any other case |

#### ShouldHaveRefused
| Score | Condition |
|-------|-----------|
| 1 | Answer is **not** a refusal AND the question was out of scope |
| 0 | Any other case |

**Mutual exclusivity:** at most one flag should be 1; all three can be 0 (in-scope question, non-refusal answer — the normal case). The prompt instructs the judge to re-evaluate scope/refusal determinations if it finds itself scoring more than one flag as 1.

---

## 4. Reasoning Process

Both rubrics require chain-of-thought reasoning in XML tags before the final JSON, to reduce metric contamination:

```xml
<!-- AgentJudge -->
<evaluate_c1>...</evaluate_c1>
<evaluate_c2>...</evaluate_c2>
<evaluate_c3>...</evaluate_c3>
<evaluate_c4>...</evaluate_c4>
<evaluate_c5>...</evaluate_c5>
```

```xml
<!-- RefusalJudge -->
<scope_determination>...</scope_determination>
<refusal_detection>...</refusal_detection>
<evaluate_flags>...</evaluate_flags>
```

Both scripts also enable Claude's **extended thinking** on top of this — the `thinking` content block is captured separately into `judge_thinking` by `AgentJudge.py` (not re-captured by `RefusalJudge.py`, since that column is already filled).

---

## 5. Output Format (as actually parsed by the code)

`extract_json()` (identical in both scripts) finds `\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}` matches (one level of nested braces) in the response text and `json.loads()`s the **last** match — tolerating any XML reasoning preamble before it.

**AgentJudge JSON contract:**
```json
{
  "C1_correctness": 0,
  "C2_coverage": 1,
  "C3_citation_presence": 1,
  "C4_citation_valid": 1,
  "C5_clarity": 1,
  "reasoning": {
    "C1": "...", "C2": "...", "C3": "...", "C4": "...", "C5": "..."
  }
}
```

**RefusalJudge JSON contract:**
```json
{
  "CorrectRefusal": 0,
  "ImproperRefusal": 0,
  "ShouldHaveRefused": 0,
  "reasoning": {
    "scope": "...", "refusal_detection": "...", "flags": "..."
  }
}
```
`RefusalJudge.py` flattens the `reasoning` object into one string column, `reasoning_refusal`, formatted as `"SCOPE: {scope} | REFUSAL: {refusal_detection} | FLAGS: {flags}"`.

---

## 6. Rule Grounding Score (RGS) — defined, not wired up

```
RGS = C1 × (C2 + C3 + C4 + C5) / 4
```

This is the intended response variable, but it is **not computed anywhere in the current pipeline**. It exists only inside `scoring_helper.merge_scores()`, which is `import`ed by both notebooks and never called. Neither `AgentJudge.py` nor `RefusalJudge.py` touches the `RGS` column — it is written blank by `run_CRD_experiment()` and stays blank.

### Properties (as designed, once/if wired up)

| Property | Detail |
|----------|--------|
| Range | 0.0 to 1.0 |
| C1 as gate | If C1 = 0 (factually wrong), RGS = 0 regardless of other scores |
| Maximum | C1=1, C2=C3=C4=C5=1 → RGS = 1.0 |
| Partial example | C1=1, C2=1, C3=0, C4=0, C5=1 → RGS = 1 × (1+0+0+1)/4 = 0.5 |

---

## 7. Rubric Tradeoffs and Design Notes

| Design choice | Rationale |
|---------------|-----------|
| Binary scores only (0/1) | Reduces evaluator subjectivity; a clear binary boundary is more reproducible than a 1–5 scale |
| Separation of C3/C4 | Citation *presence* and citation *validity* are intentionally separate — an agent may cite chunks without those chunks supporting the answer (currently being reconsidered, see §2.2) |
| Independent refusal flags | Detects all three failure modes simultaneously: correct behaviour, over-refusal, and under-refusal |
| Two separate scripts/rubrics instead of one combined judge | Prevents a strong/weak refusal judgement from unconsciously shifting the quality scores, and vice versa |
| RefusalJudge sees `agent_thinking`, not chunks | Scope determination is meant to reflect what the agent itself believed it found, as supplementary evidence only |

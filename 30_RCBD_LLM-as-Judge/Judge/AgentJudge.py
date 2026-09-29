import os, json, re, time, pandas as pd
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("AGENT_JUDGE_MODEL_NAME")
MAX_TOKENS = int(os.getenv("AGENT_JUDGE_MAX_TOKENS", 3000))
THINKING_BUDGET = int(os.getenv("AGENT_JUDGE_THINKING_BUDGET_TOKENS", 8000))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)

AGENT_COLS = [
    "C1_correctness", "C2_coverage", "C3_citation_presence", "C4_citation_valid",
    "C5_clarity", "reasoning_C1", "reasoning_C2", "reasoning_C3", "reasoning_C4",
    "reasoning_C5", "judge_thinking", "scored_by", "scoring_notes",
]


def extract_json(text: str) -> dict:
    matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL))
    if not matches:
        raise ValueError("No JSON object found in text block")
    return json.loads(matches[-1].group())


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in AGENT_COLS:
        if col not in df.columns:
            df[col] = None
    return df


def run_agent_judge(csv_path: str = None) -> None:
    """Score all rows. Callable from notebook or standalone."""
    if csv_path is None:
        csv_path = os.path.join(_PROJECT_DIR, "Output", "Ext_ClueRag_CRD.csv")

    prompt_path = os.path.join(_SCRIPT_DIR, "JudgeAgentPrompt.json")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    system_prompt = "\n".join(prompt_data["system_prompt"])

    df = pd.read_csv(csv_path)
    df = _ensure_columns(df)

    total = len(df)
    passed = 0
    failed = 0

    for idx, row in df.iterrows():
        run_id = row["run_id"]
        n = idx + 1

        user_message = (
            f"QUESTION: {row['question_text']}\n\n"
            f"ANSWER: {row['answer']}\n\n"
            f"CHUNKS:\n{row['retrieved_chunks']}"
        )

        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET},
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )

            thinking_text = ""
            text_block = ""
            for block in response.content:
                if block.type == "thinking":
                    thinking_text = block.thinking
                elif block.type == "text":
                    text_block = block.text

            parsed = extract_json(text_block)

            df.loc[df["run_id"] == run_id, "C1_correctness"] = parsed["C1_correctness"]
            df.loc[df["run_id"] == run_id, "C2_coverage"] = parsed["C2_coverage"]
            df.loc[df["run_id"] == run_id, "C3_citation_presence"] = parsed["C3_citation_presence"]
            df.loc[df["run_id"] == run_id, "C4_citation_valid"] = parsed["C4_citation_valid"]
            df.loc[df["run_id"] == run_id, "C5_clarity"] = parsed["C5_clarity"]
            df.loc[df["run_id"] == run_id, "reasoning_C1"] = parsed["reasoning"]["C1"]
            df.loc[df["run_id"] == run_id, "reasoning_C2"] = parsed["reasoning"]["C2"]
            df.loc[df["run_id"] == run_id, "reasoning_C3"] = parsed["reasoning"]["C3"]
            df.loc[df["run_id"] == run_id, "reasoning_C4"] = parsed["reasoning"]["C4"]
            df.loc[df["run_id"] == run_id, "reasoning_C5"] = parsed["reasoning"]["C5"]
            df.loc[df["run_id"] == run_id, "judge_thinking"] = thinking_text
            df.loc[df["run_id"] == run_id, "scored_by"] = "AgentJudge"
            df.loc[df["run_id"] == run_id, "scoring_notes"] = ""

            df.to_csv(csv_path, index=False)
            passed += 1
            print(f"[Row {n}/{total}] run_id={run_id} — PASSED")

        except anthropic.RateLimitError as e:
            print(f"[Row {n}/{total}] run_id={run_id} — 429 rate limit, waiting 60s...")
            time.sleep(60)
            try:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    thinking={"type": "enabled", "budget_tokens": THINKING_BUDGET},
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                )

                thinking_text = ""
                text_block = ""
                for block in response.content:
                    if block.type == "thinking":
                        thinking_text = block.thinking
                    elif block.type == "text":
                        text_block = block.text

                parsed = extract_json(text_block)

                df.loc[df["run_id"] == run_id, "C1_correctness"] = parsed["C1_correctness"]
                df.loc[df["run_id"] == run_id, "C2_coverage"] = parsed["C2_coverage"]
                df.loc[df["run_id"] == run_id, "C3_citation_presence"] = parsed["C3_citation_presence"]
                df.loc[df["run_id"] == run_id, "C4_citation_valid"] = parsed["C4_citation_valid"]
                df.loc[df["run_id"] == run_id, "C5_clarity"] = parsed["C5_clarity"]
                df.loc[df["run_id"] == run_id, "reasoning_C1"] = parsed["reasoning"]["C1"]
                df.loc[df["run_id"] == run_id, "reasoning_C2"] = parsed["reasoning"]["C2"]
                df.loc[df["run_id"] == run_id, "reasoning_C3"] = parsed["reasoning"]["C3"]
                df.loc[df["run_id"] == run_id, "reasoning_C4"] = parsed["reasoning"]["C4"]
                df.loc[df["run_id"] == run_id, "reasoning_C5"] = parsed["reasoning"]["C5"]
                df.loc[df["run_id"] == run_id, "judge_thinking"] = thinking_text
                df.loc[df["run_id"] == run_id, "scored_by"] = "AgentJudge"
                df.loc[df["run_id"] == run_id, "scoring_notes"] = ""

                df.to_csv(csv_path, index=False)
                passed += 1
                print(f"[Row {n}/{total}] run_id={run_id} — PASSED (retry)")

            except Exception as retry_err:
                df.loc[df["run_id"] == run_id, "scored_by"] = "AgentJudge"
                df.loc[df["run_id"] == run_id, "scoring_notes"] = str(retry_err)
                for col in ["C1_correctness", "C2_coverage", "C3_citation_presence",
                            "C4_citation_valid", "C5_clarity", "reasoning_C1",
                            "reasoning_C2", "reasoning_C3", "reasoning_C4",
                            "reasoning_C5", "judge_thinking"]:
                    df.loc[df["run_id"] == run_id, col] = None
                df.to_csv(csv_path, index=False)
                failed += 1
                print(f"[Row {n}/{total}] run_id={run_id} — FAILED (retry): {retry_err}")

        except Exception as e:
            df.loc[df["run_id"] == run_id, "scored_by"] = "AgentJudge"
            df.loc[df["run_id"] == run_id, "scoring_notes"] = str(e)
            for col in ["C1_correctness", "C2_coverage", "C3_citation_presence",
                        "C4_citation_valid", "C5_clarity", "reasoning_C1",
                        "reasoning_C2", "reasoning_C3", "reasoning_C4",
                        "reasoning_C5", "judge_thinking"]:
                df.loc[df["run_id"] == run_id, col] = None
            df.to_csv(csv_path, index=False)
            failed += 1
            print(f"[Row {n}/{total}] run_id={run_id} — FAILED: {e}")

        if idx < total - 1:
            time.sleep(1)

    print(f"\nAgentJudge complete.")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"CSV written to: {csv_path}")
    print("Run RefusalJudge when ready.")


if __name__ == "__main__":
    run_agent_judge()

import os, json, re, time, pandas as pd
from dotenv import load_dotenv
import anthropic

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("REFUSAL_JUDGE_MODEL_NAME")
MAX_TOKENS = int(os.getenv("REFUSAL_AGENT_JUDGE_MAX_TOKENS", 3000))
THINKING_BUDGET = int(os.getenv("REFUSAL_AGENT_JUDGE_THINKING_BUDGET_TOKENS", 8000))

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)

REFUSAL_COLS = [
    "CorrectRefusal", "ImproperRefusal", "ShouldHaveRefused", "reasoning_refusal",
]


def extract_json(text: str) -> dict:
    matches = list(re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL))
    if not matches:
        raise ValueError("No JSON object found in text block")
    return json.loads(matches[-1].group())


def _ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in REFUSAL_COLS:
        if col not in df.columns:
            df[col] = None
    return df


def run_refusal_judge(csv_path: str = None) -> None:
    """Score all rows. Callable from notebook or standalone."""
    if csv_path is None:
        csv_path = os.path.join(_PROJECT_DIR, "Output", "Ext_ClueRag_CRD.csv")

    prompt_path = os.path.join(_SCRIPT_DIR, "JudgeRefusalPrompt.json")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    df = pd.read_csv(csv_path)

    if df["C1_correctness"].isnull().all():
        raise RuntimeError(
            "AgentJudge scores not found. Run AgentJudge first."
        )

    df = _ensure_columns(df)

    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_data = json.load(f)
    system_prompt = "\n".join(prompt_data["system_prompt"])

    total = len(df)
    passed = 0
    failed = 0

    for idx, row in df.iterrows():
        run_id = row["run_id"]
        n = idx + 1

        user_message = (
            f"QUESTION: {row['question_text']}\n\n"
            f"ANSWER: {row['answer']}\n\n"
            f"AGENT_THINKING: {row['agent_thinking']}"
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

            text_block = ""
            for block in response.content:
                if block.type == "text":
                    text_block = block.text

            parsed = extract_json(text_block)

            reasoning = parsed["reasoning"]
            reasoning_refusal = (
                f"SCOPE: {reasoning['scope']} | "
                f"REFUSAL: {reasoning['refusal_detection']} | "
                f"FLAGS: {reasoning['flags']}"
            )

            df.loc[df["run_id"] == run_id, "CorrectRefusal"] = parsed["CorrectRefusal"]
            df.loc[df["run_id"] == run_id, "ImproperRefusal"] = parsed["ImproperRefusal"]
            df.loc[df["run_id"] == run_id, "ShouldHaveRefused"] = parsed["ShouldHaveRefused"]
            df.loc[df["run_id"] == run_id, "reasoning_refusal"] = reasoning_refusal

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

                text_block = ""
                for block in response.content:
                    if block.type == "text":
                        text_block = block.text

                parsed = extract_json(text_block)

                reasoning = parsed["reasoning"]
                reasoning_refusal = (
                    f"SCOPE: {reasoning['scope']} | "
                    f"REFUSAL: {reasoning['refusal_detection']} | "
                    f"FLAGS: {reasoning['flags']}"
                )

                df.loc[df["run_id"] == run_id, "CorrectRefusal"] = parsed["CorrectRefusal"]
                df.loc[df["run_id"] == run_id, "ImproperRefusal"] = parsed["ImproperRefusal"]
                df.loc[df["run_id"] == run_id, "ShouldHaveRefused"] = parsed["ShouldHaveRefused"]
                df.loc[df["run_id"] == run_id, "reasoning_refusal"] = reasoning_refusal

                df.to_csv(csv_path, index=False)
                passed += 1
                print(f"[Row {n}/{total}] run_id={run_id} — PASSED (retry)")

            except Exception as retry_err:
                df.loc[df["run_id"] == run_id, "reasoning_refusal"] = str(retry_err)
                for col in ["CorrectRefusal", "ImproperRefusal", "ShouldHaveRefused"]:
                    df.loc[df["run_id"] == run_id, col] = None
                df.to_csv(csv_path, index=False)
                failed += 1
                print(f"[Row {n}/{total}] run_id={run_id} — FAILED (retry): {retry_err}")

        except Exception as e:
            df.loc[df["run_id"] == run_id, "reasoning_refusal"] = str(e)
            for col in ["CorrectRefusal", "ImproperRefusal", "ShouldHaveRefused"]:
                df.loc[df["run_id"] == run_id, col] = None
            df.to_csv(csv_path, index=False)
            failed += 1
            print(f"[Row {n}/{total}] run_id={run_id} — FAILED: {e}")

        if idx < total - 1:
            time.sleep(1)

    print(f"\nRefusalJudge complete.")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    print(f"CSV written to: {csv_path}")
    print("Evaluation complete. Review Output/Ext_ClueRag_CRD.csv for full results.")


if __name__ == "__main__":
    run_refusal_judge()

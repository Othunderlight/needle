import asyncio
from datetime import datetime, timezone
import json
import os
import subprocess
import time
from typing import Any
import uuid

from ndl import run_command_agent
from openai import AsyncOpenAI

# Core primitives from the OpenAI Agents SDK
from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    set_tracing_disabled,
)

# ---------------------------------------------------------------------------
# 0. Helper: Log Storage
# ---------------------------------------------------------------------------
LOG_FILE = "log.json"


def save_run_log(run_record: dict[str, Any], filepath: str = LOG_FILE) -> None:
    """Appends a run record safely to the target JSON log file."""
    logs = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = json.load(f)
                logs = content if isinstance(content, list) else [content]
        except Exception:
            logs = []

    logs.append(run_record)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 1. Connect to Local Ollama
# ---------------------------------------------------------------------------
ollama_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

set_tracing_disabled(True)

ollama_model = OpenAIChatCompletionsModel(
    model="qwen3:0.6b",
    openai_client=ollama_client,
)

# ---------------------------------------------------------------------------
# 2. Decision Maker: Subprocess Curl Endpoint
# ---------------------------------------------------------------------------
def decision_agent(state: str) -> tuple[str, dict[str, Any], float]:
    """
    Calls the JEV evaluation endpoint via curl.
    Returns:
        (decision_choice, full_raw_response_json, elapsed_duration_seconds)
    """
    t0 = time.perf_counter()
    payload = {
        "state": state,
        "questions": {
            "decision": {
                "instructions": "What should the agent do next?",
                "type": "choice",
                "criteria": {
                    "Retry": "Retry",
                    "Continue": "Continue",
                    "Reply to the user": "Reply to the user",
                    "Use Tool": "Use Tool",
                },
            }
        },
    }

    curl_cmd = [
        "curl",
        "-s",
        "https://jevplayground.com/api/evaluate",
        "-H", "accept: */*",
        "-H", "accept-language: en-US,en;q=0.9,ar-AE;q=0.8,ar;q=0.7",
        "-H", "content-type: application/json",
        "-H", "origin: https://jevplayground.com",
        "-H", "priority: u=1, i",
        "-H", "referer: https://jevplayground.com/",
        "-H", 'sec-ch-ua: "Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
        "-H", "sec-ch-ua-mobile: ?0",
        "-H", 'sec-ch-ua-platform: "Linux"',
        "-H", "sec-fetch-dest: empty",
        "-H", "sec-fetch-mode: cors",
        "-H", "sec-fetch-site: same-origin",
        "-H", "user-agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
        "--data-raw", json.dumps(payload),
    ]

    res = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
    duration = round(time.perf_counter() - t0, 4)

    raw_data = json.loads(res.stdout)
    choice = raw_data["result"]["answers"]["decision"]["choice"]
    return choice, raw_data, duration


# ---------------------------------------------------------------------------
# 3. Agent Definitions
# ---------------------------------------------------------------------------
formatter_agent = Agent(
    name="FormatterAgent",
    model=ollama_model,
    instructions=(
        "You are stripper agent, your job is to strip out any unnecessary info or words.\n"
        "Do NOT include explanations, markdown, or quotes or any non text char. Output ONLY the clean action text."
    ),
)

reply_agent = Agent(
    name="ReplyAgent",
    model=ollama_model,
    instructions=(
        "You formulate the final response to the user based STRICTLY on the tool execution output.\n"
        "- If Tool Output is 'No tool called' or describes a failure, tell the user honestly that the action was not performed or failed.\n"
        "- NEVER claim that you opened or performed something unless Tool Output explicitly confirms success.\n"
        "- Keep the answer concise, friendly, and natural."
    ),
)


def run_assistant(command: str) -> dict[str, Any]:
    """Executes a query via ndl.run_command_agent and parses results safely."""
    print(f"  [CLI Executing]: {command}")
    try:
        result = run_command_agent(command)
    except Exception as exc:
        return {
            "status": "error",
            "output": "",
            "error": str(exc),
            "exit_code": -1,
        }

    if not isinstance(result, dict) or result.get("success") is False:
        err_msg = (
            result.get("error")
            if isinstance(result, dict)
            else "The CLI engine failed to run this query."
        ) or "Unknown CLI failure."
        return {
            "status": "error",
            "output": "",
            "error": err_msg,
            "exit_code": 1,
        }

    results = result.get("results")
    if results is None:
        results = []
    elif isinstance(results, str):
        results = [results]

    if not results:
        return {
            "status": "no_tool",
            "output": "",
            "error": result.get("error") or "No tool was executed for this query.",
            "exit_code": 1,
        }

    last_entry = results[-1]
    if isinstance(last_entry, dict):
        if last_entry.get("error"):
            return {
                "status": "error",
                "output": "",
                "error": str(last_entry["error"]),
                "exit_code": 1,
            }
        output_str = str(last_entry.get("output") or last_entry.get("result") or last_entry)
    else:
        output_str = str(last_entry)

    if output_str.lstrip().startswith("❌"):
        return {"status": "error", "output": "", "error": output_str, "exit_code": 1}

    return {"status": "success", "output": output_str, "error": None, "exit_code": 0}


# ---------------------------------------------------------------------------
# 4. Orchestration Loop with Timing & Logging
# ---------------------------------------------------------------------------
async def run_workflow(user_query: str, max_retries: int = 3):
    run_id = str(uuid.uuid4())
    workflow_start_time = time.perf_counter()
    timestamp_iso = datetime.now(timezone.utc).isoformat()

    log_entry: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": timestamp_iso,
        "user_query": user_query,
        "cleaned_command": None,
        "total_duration_sec": 0.0,
        "final_output": None,
        "steps": [],
    }

    print(f"\n==========================================")
    print(f"Run ID: {run_id}")
    print(f"User Request: '{user_query}'")
    print(f"==========================================")

    try:
        # 1. Clean the user query for CLI tool consumption
        t0_fmt = time.perf_counter()
        formatter_result = await Runner.run(formatter_agent, input=user_query)
        fmt_duration = round(time.perf_counter() - t0_fmt, 4)

        cleaned_command = (
            formatter_result.final_output.strip()
            .strip("`")
            .strip('"')
            .strip("'")
        )
        if not cleaned_command:
            cleaned_command = user_query

        log_entry["cleaned_command"] = cleaned_command
        log_entry["steps"].append({
            "step": "formatter_agent",
            "duration_sec": fmt_duration,
            "input": user_query,
            "output": cleaned_command,
        })

        print(f"[Cleaned Command for Tools]: '{cleaned_command}' ({fmt_duration}s)")

        # Initial state
        current_state = f'The user sent a query: "{cleaned_command}". Status: No tool called yet.'
        last_output: str | None = None

        attempt = 0
        while attempt < max_retries:
            attempt += 1
            print(f"\n--- Turn {attempt}: Evaluating State via Decision Endpoint ---")
            print(f"[Current State]: {current_state}")

            # 2. Call Decision Endpoint (capturing full raw response & duration)
            decision, raw_api_data, dec_duration = decision_agent(current_state)
            print(f"[Decision Output]: {decision} ({dec_duration}s)")

            log_entry["steps"].append({
                "step": "decision_agent",
                "turn": attempt,
                "duration_sec": dec_duration,
                "input_state": current_state,
                "decision": decision,
                "raw_api_response": raw_api_data,
            })

            # CASE 1: Evaluator decides to reply to the user
            if decision == "Reply to the user":
                tool_output_value = last_output if last_output else "No tool called"
                prompt = (
                    f"User Query: {user_query}\n"
                    f"Tool Output: {tool_output_value}"
                )

                t0_reply = time.perf_counter()
                reply_response = await Runner.run(reply_agent, input=prompt)
                reply_duration = round(time.perf_counter() - t0_reply, 4)
                final_message = reply_response.final_output.strip()

                log_entry["steps"].append({
                    "step": "reply_agent",
                    "turn": attempt,
                    "duration_sec": reply_duration,
                    "prompt": prompt,
                    "output": final_message,
                })
                log_entry["final_output"] = final_message

                print(f"\n[Final Result to User]:\n{final_message}")
                return final_message

            # CASE 2: Tool execution is requested (Use Tool, Retry, or Continue)
            if decision in ("Use Tool", "Retry", "Continue"):
                t0_tool = time.perf_counter()
                cli_result = run_assistant(cleaned_command)
                tool_duration = round(time.perf_counter() - t0_tool, 4)

                if cli_result["status"] == "success":
                    last_output = cli_result["output"]
                else:
                    last_output = cli_result.get("error") or "Tool execution failed"

                log_entry["steps"].append({
                    "step": "tool_execution",
                    "turn": attempt,
                    "duration_sec": tool_duration,
                    "command": cleaned_command,
                    "result": cli_result,
                })

                current_state = (
                    f'The user sent a query: "{cleaned_command}". '
                    f'Tool was called and returned output: "{last_output}"'
                )

        # Fallback if max attempts exceeded
        print("\n[Terminated]: Exceeded maximum retry attempts.")
        fallback_output = last_output if last_output else "No tool called"
        fallback_prompt = (
            f"User Query: {user_query}\n"
            f"Tool Output: {fallback_output} (Max attempts exceeded)"
        )

        t0_fallback = time.perf_counter()
        fallback_reply = await Runner.run(reply_agent, input=fallback_prompt)
        fallback_duration = round(time.perf_counter() - t0_fallback, 4)
        final_fallback = fallback_reply.final_output.strip()

        log_entry["steps"].append({
            "step": "fallback_reply_agent",
            "duration_sec": fallback_duration,
            "prompt": fallback_prompt,
            "output": final_fallback,
        })
        log_entry["final_output"] = final_fallback

        print(f"[Final Result to User]:\n{final_fallback}")
        return final_fallback

    finally:
        # Compute total workflow time and persist log
        log_entry["total_duration_sec"] = round(time.perf_counter() - workflow_start_time, 4)
        save_run_log(log_entry, filepath=LOG_FILE)
        print(f"\n[Log Saved]: {LOG_FILE} (Total time: {log_entry['total_duration_sec']}s)")


# ---------------------------------------------------------------------------
# 5. Run Workflow
# ---------------------------------------------------------------------------
async def main():
    await run_workflow("man... open terminal in my content folder")


if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import subprocess
from typing import Any
from openai import AsyncOpenAI
from ndl import run_command_agent

# Core primitives from the OpenAI Agents SDK
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

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
def decision_agent(state: str) -> str:
    """
    Acts as the Decision Agent by calling the JEV evaluation endpoint via curl.
    Takes `state` as input and returns the decision choice:
    ('Use Tool', 'Reply to the user', 'Retry', 'Continue').
    """
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
    data = json.loads(res.stdout)
    return data["result"]["answers"]["decision"]["choice"]


# ---------------------------------------------------------------------------
# 3. Agent Definitions
# ---------------------------------------------------------------------------
formatter_agent = Agent(
    name="FormatterAgent",
    model=ollama_model,
    instructions=(
        "You are a command cleaning agent. Given the user's input, extract only "
        "the direct action command suitable for tool execution. "
        "Do NOT include explanations, markdown, or quotes. Output ONLY the clean action text."
    ),
)

reply_agent = Agent(
    name="ReplyAgent",
    model=ollama_model,
    instructions=(
        "You formulate the final response to the user based STRICTLY on the tool execution output.\n"
        "- If Tool Output is 'No tool called' or describes a failure, tell the user honestly that the action was not performed or failed.\n"
        "- NEVER claim that you opened or performed something unless Tool Output explicitly confirms success (e.g. '✅').\n"
        "- Keep the answer concise, friendly, and natural."
    ),
)


def run_assistant(command: str) -> dict[str, Any]:
    """
    Executes a query via ndl.run_command_agent (needle) and parses results safely.
    """
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

    # Handle explicit error return
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

    # Extract string output from dict or primitive
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

    # Check for CLI failure markers
    if output_str.lstrip().startswith("❌"):
        return {"status": "error", "output": "", "error": output_str, "exit_code": 1}

    return {"status": "success", "output": output_str, "error": None, "exit_code": 0}


# ---------------------------------------------------------------------------
# 4. Orchestration Loop using the Curl Evaluator
# ---------------------------------------------------------------------------
async def run_workflow(user_query: str, max_retries: int = 3):
    print(f"\n==========================================")
    print(f"User Request: '{user_query}'")
    print(f"==========================================")

    # 1. Clean the user query for CLI tool consumption
    formatter_result = await Runner.run(formatter_agent, input=user_query)
    cleaned_command = (
        formatter_result.final_output.strip()
        .strip("`")
        .strip('"')
        .strip("'")
    )
    if not cleaned_command:
        cleaned_command = user_query

    print(f"[Cleaned Command for Tools]: '{cleaned_command}'")

    # Initial state explicitly informs evaluator that no tool has been run yet
    current_state = f'The user sent a query: "{cleaned_command}". Status: No tool called yet.'
    last_output: str | None = None

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        print(f"\n--- Turn {attempt}: Evaluating State via Decision Endpoint ---")
        print(f"[Current State]: {current_state}")

        decision = decision_agent(current_state)
        print(f"[Decision Output]: {decision}")

        # CASE 1: Evaluator decides to reply to the user
        if decision == "Reply to the user":
            tool_output_value = last_output if last_output else "No tool called"

            prompt = (
                f"User Query: {user_query}\n"
                f"Tool Output: {tool_output_value}"
            )
            reply_response = await Runner.run(reply_agent, input=prompt)
            final_message = reply_response.final_output.strip()

            print(f"\n[Final Result to User]:\n{final_message}")
            return final_message

        # CASE 2: Tool execution is requested (Use Tool, Retry, or Continue)
        if decision in ("Use Tool", "Retry", "Continue"):
            cli_result = run_assistant(cleaned_command)

            if cli_result["status"] == "success":
                last_output = cli_result["output"]
            else:
                last_output = cli_result.get("error") or "Tool execution failed"

            # Update the state string for the next evaluator turn
            current_state = (
                f'The user sent a query: "{cleaned_command}". '
                f'Tool was called and returned output: "{last_output}"'
            )

    print("\n[Terminated]: Exceeded maximum retry attempts.")
    fallback_output = last_output if last_output else "No tool called"
    fallback_prompt = (
        f"User Query: {user_query}\n"
        f"Tool Output: {fallback_output} (Max attempts exceeded)"
    )
    fallback_reply = await Runner.run(reply_agent, input=fallback_prompt)
    final_fallback = fallback_reply.final_output.strip()
    print(f"[Final Result to User]:\n{final_fallback}")
    return final_fallback


# ---------------------------------------------------------------------------
# 5. Run Workflow
# ---------------------------------------------------------------------------
async def main():
    await run_workflow("man... open discord")


if __name__ == "__main__":
    asyncio.run(main())

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
        "you are a stripper agent. Given the following text, remove any unnecessary info/words from it"
        # "direct action-first text ready for tool agent to understand and call the propper tools. "
        "Do NOT include explanations, markdown, or quotes. Output ONLY the clean single-line action text."
    ),
)

reply_agent = Agent(
    name="ReplyAgent",
    model=ollama_model,
    instructions=(
        "You are constructing the final response to the user.\n"
        "You will receive the user's initial query and the execution results from tools.\n"
        "Write a concise, friendly, and natural sentence confirming if the action succeeded or failed "
        "(e.g., 'Done! I opened the terminal in the remotion folder for you.' or 'Sorry, I couldn't open the terminal.'). "
        "Do not output raw logs or technical code paths unless necessary."
    ),
)


def run_assistant(command: str) -> dict[str, Any]:
    """
    Executes a query via ndl.run_command_agent (needle) and returns structured feedback.
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

    if result.get("success") is False:
        return {
            "status": "error",
            "output": "",
            "error": result.get("error")
            or result.get("reason")
            or "The CLI engine failed to run this query.",
            "exit_code": result.get("error_code") or -1,
        }

    results = result.get("results") or []

    if not results:
        return {
            "status": "no_tool",
            "output": result.get("reasoning") or "",
            "error": (
                "No tool was executed for this query. Reformat the query so it "
                "clearly and directly asks to open a specific app "
                "(e.g. 'open <app>' or 'open <app> in <folder>')."
            ),
            "exit_code": 1,
        }

    last = results[-1]
    if isinstance(last, dict) and "error" in last:
        return {"status": "error", "output": "", "error": str(last["error"]), "exit_code": 1}

    output = str(last)
    if output.lstrip().startswith("❌"):
        return {"status": "error", "output": output, "error": output, "exit_code": 1}

    return {"status": "success", "output": output, "error": None, "exit_code": 0}


# ---------------------------------------------------------------------------
# 4. Orchestration Loop using the Curl Evaluator
# ---------------------------------------------------------------------------
async def run_workflow(user_query: str, max_retries: int = 3):
    print(f"\n==========================================")
    print(f"User Request: '{user_query}'")
    print(f"==========================================")

    # 1. Clean the user query ONCE upfront
    formatter_result = await Runner.run(formatter_agent, input=user_query)
    user_query = (
        formatter_result.final_output.strip()
        .strip("`")
        .strip('"')
        .strip("'")
    )
    print(f"[Cleaned Command for Tools]: '{user_query}'")

    current_state = f'The user send a query "{user_query}"'
    last_output = None

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        print(f"\n--- Turn {attempt}: Evaluating State via Decision Endpoint ---")
        print(f"[Current State]: {current_state}")

        # Pass the state directly to the decision evaluator
        decision = decision_agent(current_state)
        print(f"[Decision Output]: {decision}")

        # CASE 1: Evaluator decides to reply to the user
        if decision == "Reply to the user":
            prompt = (
                f"User Query: {user_query}\n"
                f"Tool Execution Output: {last_output if last_output else 'No tool was needed. REPLY NOW'}"
            )
            reply_response = await Runner.run(reply_agent, input=prompt)
            final_message = reply_response.final_output.strip()

            print(f"\n[Final Result to User]:\n{final_message}")
            return final_message

        # CASE 2: Tool execution is requested (Use Tool, Retry, or Continue)
        if decision in ("Use Tool", "Retry", "Continue"):
            # 2. Directly execute using the pre-formatted command
            cli_result = run_assistant(user_query)
            last_output = (
                cli_result["output"]
                if cli_result["status"] == "success"
                else cli_result["error"]
            )

            # 3. Update the state string for the next turn
            current_state = (
                f'The user send a query "{user_query}", a tool was called and the output was "{last_output}"'
            )

    print("\n[Terminated]: Exceeded maximum retry attempts.")
    fallback_prompt = (
        f"User Query: {user_query}\n"
        f"Tool Execution Output: Failed or timed out after {max_retries} attempts. Last output: {last_output}"
    )
    fallback_reply = await Runner.run(reply_agent, input=fallback_prompt)
    print(f"[Final Result to User]:\n{fallback_reply.final_output.strip()}")
    return fallback_reply.final_output.strip()


# ---------------------------------------------------------------------------
# 5. Run Workflow
# ---------------------------------------------------------------------------
async def main():
    await run_workflow("man... open terminal in remotion folder")


if __name__ == "__main__":
    asyncio.run(main())

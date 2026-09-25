import asyncio
import shlex
import subprocess
import uuid
from typing import Any, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

# Core primitives from the OpenAI Agents SDK
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    SQLiteSession,
    set_tracing_disabled,
)

# ---------------------------------------------------------------------------
# 1. Connect to Local Ollama via OpenAI-Compatible Chat Completions
# ---------------------------------------------------------------------------
# Ollama exposes an OpenAI-compatible API at http://localhost:11434/v1
ollama_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # AsyncOpenAI requires a non-empty string, Ollama ignores it
)

# Disable OpenAI cloud tracing export since we are using local models
set_tracing_disabled(True)

# Wrap the client in the SDK's OpenAIChatCompletionsModel adapter
ollama_model = OpenAIChatCompletionsModel(
    model="llama3.2",  # Replace with the model installed in your Ollama
    openai_client=ollama_client,
)

# ---------------------------------------------------------------------------
# 2. Define the Structured Output Schema for Agent 1
# ---------------------------------------------------------------------------
class AgentDecision(BaseModel):
    needs_tool: bool = Field(
        ...,
        description="True if the request needs an external CLI command; False if you can answer directly.",
    )
    direct_response: Optional[str] = Field(
        None,
        description="Direct answer to the user if needs_tool is False.",
    )
    cli_command: Optional[str] = Field(
        None,
        description="The CLI command or query to execute, or the revised command if retrying after an error.",
    )
    is_complete: bool = Field(
        False,
        description="True if tool execution succeeded and final feedback is ready to show the user.",
    )
    user_feedback: Optional[str] = Field(
        None,
        description="Final feedback or explanation for the user upon completing the task.",
    )


# ---------------------------------------------------------------------------
# 3. Agent 1: Ollama Decision & Feedback Agent (NO TOOLS ATTACHED)
# ---------------------------------------------------------------------------
decision_agent = Agent(
    name="OllamaTriageAgent",
    model=ollama_model,
    output_type=AgentDecision,
    instructions="""
You are an intelligent triage and feedback agent. You have NO direct tool calling capabilities.

Your tasks:
1. INITIAL USER TURN:
   - Determine if the user's query requires executing a CLI/system command.
   - If NO: set needs_tool=False, provide the answer in direct_response, and set is_complete=True.
   - If YES: set needs_tool=True, is_complete=False, and formulate the exact shell command in cli_command.

2. SUBSEQUENT TURNS (AFTER TOOL EXECUTION):
   - Review the CLI execution result (status, stdout, and error message).
   - If SUCCESS: Set is_complete=True and write a clear summary of what happened in user_feedback.
   - If FAILED:
     - If you can fix the issue, provide a new revised command in cli_command and keep is_complete=False.
     - If it cannot be fixed, set is_complete=True and explain the failure in user_feedback.
""",
)

# ---------------------------------------------------------------------------
# 4. Agent 2 & CLI Function: The CLI Agent / Tool
# ---------------------------------------------------------------------------
# Agent 2 can clarify/format what the triage agent passed, or can be the CLI itself.
cli_clarifier_agent = Agent(
    name="CLIClarifierAgent",
    model=ollama_model,
    instructions=(
        "You are a CLI formatting agent. Given an incoming command or query, make sure "
        "it is a clean, single-line shell command. Output ONLY the raw command."
    ),
)


def run_cli_command(command: str) -> dict[str, Any]:
    """
    Executes a CLI command and returns structured feedback (output or error).
    """
    print(f"  [CLI Executing]: {command}")
    try:
        # Run command with a timeout for safety
        process = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if process.returncode == 0:
            return {
                "status": "success",
                "output": process.stdout.strip() or "(Command ran with no stdout output)",
                "error": None,
                "exit_code": 0,
            }
        else:
            return {
                "status": "error",
                "output": process.stdout.strip(),
                "error": process.stderr.strip() or f"Command exited with code {process.returncode}",
                "exit_code": process.returncode,
            }
    except Exception as exc:
        return {
            "status": "error",
            "output": "",
            "error": str(exc),
            "exit_code": -1,
        }


# ---------------------------------------------------------------------------
# 5. The Orchestration & Retry Loop ("Orchestrating via Code")
# ---------------------------------------------------------------------------
async def run_workflow(user_query: str, max_retries: int = 3):
    print(f"\n==========================================")
    print(f"User Request: '{user_query}'")
    print(f"==========================================")

    # Use SDK SQLiteSession to persist multi-turn history across retries
    session = SQLiteSession(f"session_{uuid.uuid4().hex[:8]}")

    current_prompt = (
        f"User query: '{user_query}'\n"
        "Evaluate this query: does it need a CLI tool or can you answer directly?"
    )

    attempt = 0
    while attempt < max_retries:
        attempt += 1
        print(f"\n--- Turn {attempt}: Running Decision Agent ---")

        # Run the Ollama agent within the session
        result = await Runner.run(
            decision_agent,
            input=current_prompt,
            session=session,
        )

        decision: AgentDecision = result.final_output

        # CASE 1: No tool needed -> direct reply to user and finish
        if not decision.needs_tool:
            print("[Decision]: No tool needed.")
            print(f"[Agent Direct Response]:\n{decision.direct_response}")
            return decision.direct_response

        # CASE 2: Tool output was already evaluated and marked complete
        if decision.is_complete:
            print("[Decision]: Task completed.")
            print(f"[Final User Feedback]:\n{decision.user_feedback}")
            return decision.user_feedback

        # CASE 3: Tool is required or retrying with revised command
        raw_cmd = decision.cli_command
        print(f"[Decision]: Tool required. Initial command proposed: '{raw_cmd}'")

        # Pass to Agent 2 to clarify/format the command
        clarified_result = await Runner.run(cli_clarifier_agent, input=raw_cmd)
        clean_command = clarified_result.final_output.strip().strip("`")

        # Execute via the Python CLI function
        cli_result = run_cli_command(clean_command)

        # Feed the result back to Agent 1 for evaluation in the next turn
        current_prompt = (
            f"The query excuted command: '{clean_command}'\n"
            f"Result:\n"
            f"- Status: {cli_result['status']}\n"
            f"- Output: {cli_result['output']}\n"
            f"- Error Message: {cli_result['error']}\n\n"
            "Based on this feedback:\n"
            "1. If successful: set is_complete=True and write the final feedback for the user in user_feedback.\n"
            "2. If it failed and can be retried: set is_complete=False, needs_tool=True, and provide a revised command in cli_command.\n"
            "3. If it failed and cannot be resolved: set is_complete=True and explain the error in user_feedback."
        )

    print("\n[Terminated]: Exceeded maximum retry attempts.")


# ---------------------------------------------------------------------------
# 6. Example Runs
# ---------------------------------------------------------------------------
async def main():
    # Test 1: Query that does NOT need a tool (Agent replies directly)
    await run_workflow("What is the capital of France?")

    # Test 2: Query that needs a tool and succeeds
    await run_workflow("Check what operating system kernel version this machine is running")

    # Test 3: Query that fails initially and triggers the retry loop
    await run_workflow("Print the content of myfile.txt, but if it doesn't exist, list files in the current folder")


if __name__ == "__main__":
    asyncio.run(main())

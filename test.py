import asyncio
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from agents import (
    Agent,
    Runner,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)

# 1. Disable OpenAI cloud tracing export since we are using local models
set_tracing_disabled(False)

# 2. Set up the local Ollama client
ollama_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # AsyncOpenAI requires a non-empty string, Ollama ignores it
)

# 3. Wrap in the SDK's Chat Completions adapter
ollama_model = OpenAIChatCompletionsModel(
    model="gemma3:270m",  # Replace with your Ollama model
    openai_client=ollama_client,
)


# 4. Define the Structured Output Schema
class DecisionOutput(BaseModel):
    message: str = Field(
        description="Your direct answer if no tool is needed, or the cleaned action-first query if a tool is required."
    )
    need_tool: bool = Field(
        description="True if a tool is needed, False if no tool is needed."
    )
    is_complete: bool = Field(
        description="True if the task is complete / no tool needed, False if a tool is still required."
    )


# 5. Configure the Agent with the Ollama model and output_type
router_agent = Agent(
    name="OllamaRouterAgent",
    model=ollama_model,
    instructions="""
You are an intent and routing assistant. You must output JSON matching the required schema.

Rules:
- If NO tool is needed (general knowledge questions, greetings, or completed tasks):
  - Set `need_tool` to false
  - Set `is_complete` to true
  - Put the final answer inside `message`

- If a tool IS needed (real-time data, actions, external search):
  - Set `need_tool` to true
  - Set `is_complete` to false
  - Put the cleaned action-first query in `message`
""",
    output_type=DecisionOutput,
)


async def main():
    test_queries = [
        # "What is 15 * 6?",
        "open terminal in remotion folder",
    ]

    for query in test_queries:
        print(f"\n--- Query: {query} ---")
        result = await Runner.run(router_agent, query)

        decision: DecisionOutput = result.final_output
        print(f"need_tool:   {decision.need_tool}")
        print(f"is_complete: {decision.is_complete}")
        print(f"message:     {decision.message}")


if __name__ == "__main__":
    asyncio.run(main())

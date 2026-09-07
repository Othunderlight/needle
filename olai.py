import asyncio
import time
from openai import AsyncOpenAI
from agents import Agent, Runner, function_tool
from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel

# 1. Point the client to your local Ollama instance
local_client = AsyncOpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# 2. Initialize the model
local_model = OpenAIChatCompletionsModel(
    model="ibm/granite4:350m", # functiongemma:latest :2.8 seconds, ibm/granite4:350m : 2.58 seconds, qwen3:4b :16.39 seconds , qwen3:0.6b : 10.33 seconds,
    openai_client=local_client
)

@function_tool
def check_weather(city: str) -> str:
    """Checks the weather for a given city."""
    return f"The weather in {city} is currently 72°F (22°C) and sunny."

# 4. Create the agent and pass the decorated functions directly as tools
tool_agent = Agent(
    name="MultiToolAgent",
    instructions="You are a helpful assistant. Use your tools whenever appropriate.",
    model=local_model,
    tools=[check_weather]
)

async def main():
    # Prompt 1: Triggers the weather tool
    print("--- Testing Weather Tool ---")

    # Start timing
    start_time = time.time()

    res1 = await Runner.run(tool_agent, "What's the weather like in Seattle?")

    # End timing
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Agent Output:\n{res1.final_output}\n")
    print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

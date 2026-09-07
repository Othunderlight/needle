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

@function_tool
def get_folder_dir_by_name(name: str) -> str:
    """Get the directory path of a folder by its name.

    Args:
        name: The folder name to look up. Supported values: 'ddi', 'desktop'
    """
    if name == "ddi":
        return "~/Downloads/ddi"  # Fixed typo: Dawnloads -> Downloads
    return "~/desktop/"


@function_tool
def move_to_dir(dir: str) -> str:  # Return string instead of bool
    """Move to a directory by its directory path.

    Args:
        dir: The directory path to move to.
    """
    if dir == "~/Downloads/ddi":
        return f"Successfully moved to {dir}"
    return f"Failed to move to {dir}"


# 4. Create the agent and pass the decorated functions directly as tools
tool_agent = Agent(
    name="MultiToolAgent",
    instructions="You are a helpful assistant. Use your tools whenever appropriate.",
    model=local_model,
    tools=[check_weather, get_folder_dir_by_name, move_to_dir]
)

async def main():

    # Start timing
    start_time = time.time()

    res1 = await Runner.run(tool_agent, "lets move to my ddi project?")

    # End timing
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Agent Output:\n{res1.final_output}\n")
    print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

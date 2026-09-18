import asyncio
import time
import subprocess
from difflib import get_close_matches
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
    model="functiongemma:latest", # functiongemma:latest :2.8 seconds, ibm/granite4:350m : 2.58 seconds, qwen3:4b :16.39 seconds , qwen3:0.6b : 10.33 seconds,
    openai_client=local_client
)


@function_tool
def check_weather(city: str) -> str:
    """Checks the weather for a given city."""
    return f"The weather in {city} is currently 72°F (22°C) and sunny."

@function_tool
def navigate_to_project(project_name: str) -> str:
    """Navigate to a project folder by name.

    Args:
        project_name: The project name (e.g. 'desktop')
    """
    print(f"🔧 Tool called: navigate_to_project with project={project_name}")

    # Get the path
    if project_name == "ddi":
        path = "~/Downloads/ddi"
    elif project_name == "desktop":
        path = "~/Desktop"
    else:
        return f"Unknown project: {project_name}"

    return f"Successfully navigated to {project_name} at {path}"


# Available apps with multiple names and commands
APPS_DATABASE = {
    "files": {
        "commands": ["nautilus", "org.gnome.Nautilus"],
        "aliases": ["file manager", "explorer", "nautilus", "files app"]
    },
    "chrome": {
        "commands": ["google-chrome", "google-chrome-stable"],
        "aliases": ["browser", "google chrome", "chrome browser", "web browser"]
    },
    "telegram": {
        "commands": ["telegram-desktop"],
        "aliases": ["telegram app", "telegram desktop", "tg"]
    },
    "sublime": {
        "commands": ["subl", "sublime_text"],
        "aliases": ["sublime text", "sublime-text", "sublime app", "code editor"]
    },
}

# Build reverse mapping for quick lookup
APP_ALIAS_MAP = {}
for app, data in APPS_DATABASE.items():
    for alias in data["aliases"]:
        APP_ALIAS_MAP[alias] = app
    # Also add the app name itself
    APP_ALIAS_MAP[app] = app

@function_tool
def open_app(app_name: str) -> str:
    """Open an application by name.

    Args:
        app_name: The name or description of the app to open.
    """
    print(f"🔧 Tool called: open_app with app_name='{app_name}'")

    app_name_lower = app_name.lower().strip()

    # 1. Check direct match
    if app_name_lower in APP_ALIAS_MAP:
        app_key = APP_ALIAS_MAP[app_name_lower]
        return _launch_with_fallback(app_key)

    # 2. Check if any alias contains the search term or vice versa
    matches = []
    for alias, app_key in APP_ALIAS_MAP.items():
        if app_name_lower in alias or alias in app_name_lower:
            matches.append(app_key)

    # 3. Use difflib for fuzzy matching
    if not matches:
        all_aliases = list(APP_ALIAS_MAP.keys())
        best_matches = get_close_matches(app_name_lower, all_aliases, n=3, cutoff=0.5)
        if best_matches:
            for match in best_matches:
                matches.append(APP_ALIAS_MAP[match])

    # 4. Deduplicate matches
    matches = list(dict.fromkeys(matches))

    if not matches:
        return f"❌ Could not find '{app_name}'. Available apps: {', '.join(APPS_DATABASE.keys())}"

    # 5. Launch the best match
    return _launch_with_fallback(matches[0])

def _launch_with_fallback(app_key: str) -> str:
    """Try multiple commands to launch an app."""
    app_data = APPS_DATABASE[app_key]

    for command in app_data["commands"]:
        try:
            # Check if command exists
            result = subprocess.run(
                ["which", command],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Launch the app
                subprocess.Popen(
                    [command],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True  # Detach process
                )
                return f"✅ Successfully opened {app_key} (command: {command})"
        except Exception:
            pass

    # Try desktop launcher as fallback
    try:
        subprocess.Popen(
            ["gtk-launch", app_key],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        return f"✅ Successfully opened {app_key} via desktop launcher"
    except:
        return f"❌ Could not launch '{app_key}'. Tried: {', '.join(app_data['commands'])}"

# 4. Create the agent and pass the decorated functions directly as tools
tool_agent = Agent(
    name="MultiToolAgent",
    instructions="You are a helpful assistant. Use your tools whenever appropriate.",
    model=local_model,
    tools=[check_weather, navigate_to_project, open_app]
)

async def main():

    # Start timing
    start_time = time.time()

    res1 = await Runner.run(tool_agent, "open telegram")

    # End timing
    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Agent Output:\n{res1.final_output}\n")
    print(f"⏱️ Time taken: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())

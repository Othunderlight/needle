import needle



# # ==========================================
# # 1. DATABASES & ALIASES
# # ==========================================


# import json
# from pathlib import Path
# # Import the scanner function from the script above (or keep it in the same file)
# from app_scanner import scan_installed_apps

# # 1. Define the path where the cache should be stored
# # (Tip: Use .config/your_app_name or a hidden dotfile like .apps_database.json)
# CONFIG_PATH = Path.cwd() / ".apps_database.json"

# def load_apps_database(force_refresh: bool = False) -> dict:
#     """
#     Loads the APPS_DATABASE.
#     If it doesn't exist (first run) or force_refresh=True, it scans the system.
#     """
#     if not CONFIG_PATH.exists() or force_refresh:
#         print("First run detected: Scanning installed applications...")
#         apps_db = scan_installed_apps()

#         # Ensure the directory exists and write the JSON file
#         CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
#         with open(CONFIG_PATH, "w", encoding="utf-8") as f:
#             json.dump(apps_db, f, indent=4)

#         print(f"Saved {len(apps_db)} applications to {CONFIG_PATH}")
#         return apps_db

#     # Already scanned before: Load directly from cache for instant startup
#     with open(CONFIG_PATH, "r", encoding="utf-8") as f:
#         return json.load(f)

# # 2. Initialize your database variable
# APPS_DATABASE = load_apps_database()




# ==========================================
# 4. TEST RUN
# ==========================================

from tools.macros import run_macro
from tools.apps import open_app


def run_command_agent(input_text: str) -> dict[str, str | list[str] | None]:
    """
    Runs the Needle agent with the given input text.
    This function is designed to be imported and used from other files.

    Args:
        input_text: The user input string to process.

    Returns:
        The result string from the agent execution.
    """
    agent = needle.Needle(tools=[open_app, run_macro])
    result = agent.run(input_text, max_steps=1)
    return {
        "success": result.get("success"),
        "error": result.get("error"),
        "results": result.get("results", [])
    }





if __name__ == "__main__":
    # Test 1: Just the app
    # print(run_command_agent("open telegram"))

    # Test 2: App with folder tag (Sublime + folder)
    # print(run_command_agent("open sublime with my video project"))

    # Test 3: Files app with downloads
    print(run_command_agent("open terminal"))

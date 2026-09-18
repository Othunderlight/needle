import needle
import asyncio
import time
import subprocess
from difflib import get_close_matches



APPS_DATABASE = {
    "files": {
        "commands": ["nautilus", "org.gnome.Nautilus"],
        "aliases": ["file manager", "explorer", "nautilus", "files"]
    },
    "chrome": {
        "commands": ["google-chrome", "google-chrome-stable"],
        "aliases": ["browser", "google chrome", "chrome", "web browser"]
    },
    "telegram": {
        "commands": ["telegram-desktop"],
        "aliases": ["telegram", "telegram desktop", "tg"]
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


@needle.tool
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

agent = needle.Needle(tools=[open_app])
print(agent.run("open telegram")["results"])

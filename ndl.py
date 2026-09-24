import os
import subprocess
from difflib import get_close_matches
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

APPS_DATABASE = {
    # --- sys apps ---
    "files": {
        "commands": ["nautilus", "org.gnome.Nautilus"],
        "aliases": ["file manager", "explorer", "nautilus", "files"],
        "category": "system-apps",
    },
    "extension_manager": {
        "commands": ["flatpak run com.mattjakeman.ExtensionManager"],
        "aliases": ["extension manager", "gnome extensions", "extensions"],
        "category": "system-apps",
    },
    # --- Chat apps ---
    "telegram": {
        "commands": ["telegram-desktop", "flatpak run org.telegram.desktop"],
        "aliases": ["telegram", "telegram desktop", "tg"],
        "category": "chatapp",
    },
    # --- IDEs ---
    "sublime": {
        "commands": ["subl", "sublime_text"],
        "aliases": ["sublime text", "sublime-text", "sublime app", "code editor", "sublime"],
        "category": "IDE",
    },
    "android_studio": {
        "commands": ["android-studio"],
        "aliases": ["android studio"],
        "category": "IDE",
    },
    "zed": {
        "commands": ["zed"],
        "aliases": ["zed"],
        "category": "IDE",
    },
    "vscode": {
        "commands": ["code"],
        "aliases": ["vscode"],
        "category": "IDE",
    },
    "neovim": {
        "commands": ["nvim"],
        "aliases": ["neovim", "nvim", "vim", "terminal editor"],
        "category": "terminal-editor",
    },
    "nano": {
        "commands": ["nano"],
        "aliases": ["nano"],
        "category": "terminal-editor",
    },
    # --- Brawsers ---
    "brave": {
        "commands": ["brave"],
        "aliases": ["brave browser", "brave"],
        "category": "browser",
    },
    "chrome": {
        "commands": ["google-chrome", "google-chrome-stable"],
        "aliases": ["browser", "google chrome", "chrome"],
        "category": "browser",
    },
    # --- Dev Tools ---
    "ngrok": {
        "commands": ["ngrok"],
        "aliases": ["ngrok", "tunnel", "localhost tunnel"],
        "category": "networking",
    },
    "postman": {
        "commands": ["postman"],
        "aliases": ["postman", "api tester", "http client"],
        "category": "developer-tools",
    },
    # --- Productivity ---
    "notion": {
        "commands": ["notion-desktop"],
        "aliases": ["notion", "notion desktop", "notes"],
        "category": "productivity",
    },

    # --- secreen recorders ---
    "obs_studio": {
        "commands": ["flatpak run com.obsproject.Studio"],
        "aliases": ["obs studio", "obs", "screen recorder", "streaming software"],
        "category": "screen-recorder",
    },
    "kooha": {
        "commands": ["flatpak run io.github.seadve.Kooha"],
        "aliases": ["kooha", "screen recorder", "recorder"],
        "category": "screen-recorder",
    },
    # --- AI Agents ---
    "codex": {
        "commands": ["codex", "codex app"],
        "aliases": ["codex", "openai codex", "coding agent", "ai developer", "ai coder"],
        "category": "agent",
    },
    "opencode": {
        "commands": ["opencode", "opencode -q"],
        "aliases": ["opencode", "open code", "sst agent", "free coding agent"],
        "category": "agent",
    },
    # --- Terminals ---
    "ptyxis": {
        "commands": ["ptyxis", "ptyxis --new-window"],
        "aliases": ["ptyxis", "gnome prompt", "terminal", "ptyxis terminal"],
        "category": "terminal-emulator",
    },
    "wezterm": {
        "commands": ["wezterm", "wezterm start"],
        "aliases": ["wezterm", "wez terminal", "wez"],
        "category": "terminal-emulator",
    },
}


# Add your custom folders and voice tags here
FOLDERS_DATABASE = {
    "home": {
        "path": os.path.expanduser("~"),
        "aliases": ["home", "home folder", "main folder"],
    },
    "downloads": {
        "path": os.path.expanduser("~/Downloads"),
        "aliases": ["downloads", "download folder", "my downloads"],
    },
    "desktop": {
        "path": os.path.expanduser("~/Desktop"),
        "aliases": ["desktop", "my desktop"],
    },
    "videos": {
        "path": os.path.expanduser("~/Videos"),  # Change to your actual path
        "aliases": ["video project", "videos", "video folder"],
    },
    "content": {
        "path": os.path.expanduser("~/content"),        # Change to your actual path
        "aliases": ["content", "content folder", "ai vedio editing"],
    },
    "remotion": {
        "path": os.path.expanduser("~/content/remotion"),        # Change to your actual path
        "aliases": ["remotion", "remotion folder"],
    },
}

# ==========================================
# 2. ALIAS BUILDER & MATCHER
# ==========================================

def _build_alias_map(db: dict) -> dict:
    mapping = {}
    for key, data in db.items():
        mapping[key] = key
        for alias in data.get("aliases", []):
            mapping[alias.lower().strip()] = key
    return mapping

APP_ALIAS_MAP = _build_alias_map(APPS_DATABASE)
FOLDER_ALIAS_MAP = _build_alias_map(FOLDERS_DATABASE)


def _fuzzy_lookup(query: str, alias_map: dict, cutoff: float = 0.5) -> str | None:
    """Fuzzy searches a query string inside an alias mapping."""
    if not query:
        return None

    query = query.lower().strip()

    # 1. Exact match
    if query in alias_map:
        return alias_map[query]

    # 2. Substring matching
    for alias, key in alias_map.items():
        if query in alias or alias in query:
            return key

    # 3. Difflib close match
    matches = get_close_matches(query, list(alias_map.keys()), n=1, cutoff=cutoff)
    if matches:
        return alias_map[matches[0]]

    return None


# ==========================================
# 3. AGENT TOOL
# ==========================================

@needle.tool
def open_app(app_name: str, target_folder: str = "") -> str:
    """Open an application by name, optionally at a specific folder or project location.

    Args:
        app_name: The name or alias of the app (e.g., 'sublime', 'files', 'chrome').
        target_folder: Optional folder or project name (e.g., 'video project', 'downloads', 'home').
    """
    print(f"🔧 Tool called: open_app with app_name='{app_name}', target_folder='{target_folder}'")

    # Resolve App
    app_key = _fuzzy_lookup(app_name, APP_ALIAS_MAP)
    if not app_key:
        available = ", ".join(APPS_DATABASE.keys())
        return f"❌ Could not find app '{app_name}'. Available apps: {available}"

    # Resolve Folder / Target (if provided)
    resolved_path = None
    if target_folder.strip():
        folder_key = _fuzzy_lookup(target_folder, FOLDER_ALIAS_MAP)
        if folder_key:
            resolved_path = FOLDERS_DATABASE[folder_key]["path"]
        else:
            # Fallback: check if the user/speech model passed a real raw path
            expanded = os.path.expanduser(target_folder.strip())
            if os.path.exists(expanded):
                resolved_path = expanded
            else:
                return (
                    f"❌ Found app '{app_key}', but could not find folder '{target_folder}'. "
                    f"Available folders: {', '.join(FOLDERS_DATABASE.keys())}"
                )

    return _launch_with_fallback(app_key, resolved_path)


def _launch_with_fallback(app_key: str, path_arg: str = None) -> str:
    """Try multiple commands to launch an app, with optional path argument."""
    app_data = APPS_DATABASE[app_key]

    for command in app_data["commands"]:
        try:
            result = subprocess.run(["which", command], capture_output=True, text=True)
            if result.returncode == 0:
                cmd_list = [command]
                if path_arg:
                    cmd_list.append(path_arg)

                subprocess.Popen(
                    cmd_list,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                target_msg = f" at '{path_arg}'" if path_arg else ""
                return f"✅ Successfully opened {app_key}{target_msg} (using '{command}')"
        except Exception:
            pass

    # Fallback to gtk-launch (supports files/paths in FreeDesktop standard)
    try:
        cmd_list = ["gtk-launch", app_key]
        if path_arg:
            cmd_list.append(path_arg)

        subprocess.Popen(
            cmd_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        target_msg = f" at '{path_arg}'" if path_arg else ""
        return f"✅ Successfully opened {app_key}{target_msg} via desktop launcher"
    except Exception:
        return f"❌ Could not launch '{app_key}'. Tried: {', '.join(app_data['commands'])}"


# ==========================================
# 4. TEST RUN
# ==========================================

agent = needle.Needle(tools=[open_app])

# Test 1: Just the app
# print(agent.run("open telegram")["results"])

# Test 2: App with folder tag (Sublime + folder)
# print(agent.run("open sublime with my video project")["results"])

# Test 3: Files app with downloads
print(agent.run("open wezterm")["results"])

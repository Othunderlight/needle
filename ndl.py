import os
import subprocess
from difflib import get_close_matches
import needle

# ==========================================
# 1. DATABASES & ALIASES
# ==========================================

APPS_DATABASE = {
    "files": {
        "commands": ["nautilus", "org.gnome.Nautilus"],
        "aliases": ["file manager", "explorer", "nautilus", "files"],
    },
    "chrome": {
        "commands": ["google-chrome", "google-chrome-stable"],
        "aliases": ["browser", "google chrome", "chrome", "web browser"],
    },
    "telegram": {
        "commands": ["telegram-desktop"],
        "aliases": ["telegram", "telegram desktop", "tg"],
    },
    "sublime": {
        "commands": ["subl", "sublime_text"],
        "aliases": ["sublime text", "sublime-text", "sublime app", "code editor", "sublime"],
    },
}

# Add your custom folders and voice tags here
FOLDERS_DATABASE = {
    "home": {
        "path": os.path.expanduser("~"),
        "aliases": ["home", "home folder", "main folder", "user folder"],
    },
    "downloads": {
        "path": os.path.expanduser("~/Downloads"),
        "aliases": ["downloads", "download folder", "my downloads"],
    },
    "desktop": {
        "path": os.path.expanduser("~/Desktop"),
        "aliases": ["desktop", "my desktop"],
    },
    "video_projects": {
        "path": os.path.expanduser("~/Videos"),  # Change to your actual path
        "aliases": ["video project", "videos", "my video project", "video edit", "video folder"],
    },
    "code_projects": {
        "path": os.path.expanduser("~/Projects"),        # Change to your actual path
        "aliases": ["projects", "code", "coding", "dev", "my code", "dev folder"],
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
print(agent.run("open files in my downloads")["results"])

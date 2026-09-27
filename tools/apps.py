import os
import subprocess
from difflib import get_close_matches
import shlex
import shutil
import needle


default_terminal=["ptyxis", "--"]

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
        "category": "terminal-editor",
        "aliases": ["neovim", "nvim", "vim", "terminal editor"],
        "prefix": default_terminal,
        "commands": ["nvim"],
    },
    "nano": {
        "category": "terminal-editor",
        "aliases": ["nano"],
        "prefix": default_terminal,
        "commands": ["nano"],
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
        "aliases": ["ngrok", "tunnel", "localhost tunnel"],
        "category": "networking",
        "prefix": default_terminal,
        "commands": ["ngrok"],
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
        "category": "agent",
        "aliases": ["codex", "openai codex"],
        "prefix": default_terminal,
        "commands": ["codex", "codex app"],
        "path_args": ["--cd"],

    },
    "opencode": {
        "category": "agent",
        "aliases": ["opencode", "open code"],
        "prefix": default_terminal,
        "commands": ["opencode", "opencode -q"],
    },
    # --- Terminals ---
    "ptyxis": {
        "commands": ["ptyxis --new-window"],
        "path_args": ["-d"],
        "aliases": ["terminal"],
        "category": "terminal-emulator",
    },
    "wezterm": {
        "commands": ["wezterm start"],
        "aliases": ["wezterm", "wez terminal", "wez"],
        "path_args": ["--cwd"],
        "category": "terminal-emulator",
    },
     # --- VPNs ---
    "protonvpn": {
        "category": "VPN",
        "aliases": ["protonvpn", "proton", "vpn"],
        "prefix": default_terminal,
        "commands": ["protonvpn connect"],
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
    "ddi": {
        "path": os.path.expanduser("~/Downloads/ddi"),
        "aliases": ["ddi", "ddinter", "drugs"],
    },
}



###################################### not using this for now ######################################################
# Keywords to help map common user terms or uninstalled apps to your categories
CATEGORY_KEYWORDS = {
    "chatapp": ["chat", "message", "messaging", "talk", "social", "discord", "slack", "telegram", "whatsapp"],
    "browser": ["browser", "web", "internet", "surf", "chrome", "firefox", "brave", "edge", "safari"],
    "IDE": ["ide", "code", "dev", "program", "develop"],
    "terminal-editor": ["editor", "text editor", "terminal editor"],
    "terminal-emulator": ["terminal", "console", "shell", "bash", "command prompt"],
    "screen-recorder": ["record", "recorder", "screen", "capture", "streaming", "obs"],
    "developer-tools": ["api", "dev", "developer", "http", "postman"],
    "networking": ["tunnel", "network", "port"],
    "productivity": ["notes", "docs", "todo", "productivity", "notion"],
    "VPN": ["vpn", "privacy", "proxy"],
}


def _suggest_relevant_apps(query: str) -> str:
    """Returns the most relevant apps by category or fuzzy name matching."""
    query_clean = query.lower().strip()

    # 1. Match by Category / Intent
    matched_categories = set()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if cat in query_clean or any(kw in query_clean for kw in keywords):
            matched_categories.add(cat)

    if matched_categories:
        category_apps = [
            key for key, data in APPS_DATABASE.items()
            if data.get("category") in matched_categories
        ]
        if category_apps:
            return (
                f"App '{query}' is not installed/configured. "
                f"Relevant apps in that category: {', '.join(category_apps)}"
            )

    # 2. Match by Name / Typo (Did you mean...?)
    # Using cutoff=0.45 is safe here because we are only suggesting, not launching
    close_aliases = get_close_matches(query_clean, list(APP_ALIAS_MAP.keys()), n=3, cutoff=0.45)
    if close_aliases:
        suggested_apps = list(dict.fromkeys(APP_ALIAS_MAP[alias] for alias in close_aliases))
        return f"Could not find app '{query}'. Did you mean: {', '.join(suggested_apps)}?"

    # 3. Clean grouped fallback
    grouped = {}
    for app, data in APPS_DATABASE.items():
        cat = data.get("category", "other")
        grouped.setdefault(cat, []).append(app)

    formatted_categories = "\n".join(f"  • {cat}: {', '.join(apps)}" for cat, apps in grouped.items())
    return f"Could not find app '{query}'. Available apps by category:\n{formatted_categories}"


###################################### not using this for now ######################################################



# ==========================================
# 2. ALIAS BUILDER & MATCHER
# ==========================================

from .helpers import _build_alias_map, _fuzzy_lookup

APP_ALIAS_MAP = _build_alias_map(APPS_DATABASE)
FOLDER_ALIAS_MAP = _build_alias_map(FOLDERS_DATABASE)





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
        # Smart suggestions by category / typo
        # return _suggest_relevant_apps(app_name)
        return f"{app_name} is not installed"

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


def _build_command(app_data: dict, base_command: str, path_arg: str = None) -> list[str]:
    """Builds the final command list respecting custom path arguments."""
    cmd_list = shlex.split(base_command)

    if not path_arg:
        return cmd_list

    # Check if app defines custom arguments for paths
    custom_path_args = app_data.get("path_args")

    if custom_path_args:
        # Support either list format ['start', '--cwd'] or placeholder ['--cwd={path}']
        formatted_args = []
        has_placeholder = False

        for arg in custom_path_args:
            if "{path}" in arg:
                formatted_args.append(arg.replace("{path}", path_arg))
                has_placeholder = True
            else:
                formatted_args.append(arg)

        cmd_list.extend(formatted_args)
        if not has_placeholder:
            cmd_list.append(path_arg)
    else:
        # Default behavior: append path directly (e.g., `code /path`, `subl /path`)
        cmd_list.append(path_arg)

    return cmd_list


def _get_prefix_candidates(app_data: dict) -> list[list[str]]:
    """Normalizes 'prefix' or 'prefixes' into a list of candidate token lists."""
    raw = app_data.get("prefixes") or app_data.get("prefix")
    if not raw:
        return [[]]  # No prefix needed

    if isinstance(raw, str):
        return [shlex.split(raw)]

    if isinstance(raw, list):
        if not raw:
            return [[]]
        # List of candidate strings: ["ptyxis --", "wezterm start --"]
        if all(isinstance(x, str) and " " in x for x in raw):
            return [shlex.split(p) for p in raw]
        # List of candidate token lists: [["ptyxis", "--"], ["wezterm", "start", "--"]]
        if all(isinstance(x, list) for x in raw):
            return raw
        # Single token list: ["ptyxis", "--"]
        return [raw]

    return [[]]


def _build_final_command(
    prefix_tokens: list[str],
    command_str: str,
    app_data: dict,
    path_arg: str = None
) -> list[str]:
    """Combines prefix, base command, and path argument cleanly."""
    cmd_tokens = shlex.split(command_str)

    # 1. Check if prefix already handles {path} (e.g. ptyxis --working-directory={path} --)
    formatted_prefix = []
    path_consumed_in_prefix = False

    for token in prefix_tokens:
        if path_arg and "{path}" in token:
            formatted_prefix.append(token.replace("{path}", path_arg))
            path_consumed_in_prefix = True
        else:
            formatted_prefix.append(token)

    # 2. If path is provided and prefix didn't use it, format path for the inner command
    if path_arg and not path_consumed_in_prefix:
        custom_path_args = app_data.get("path_args")
        if custom_path_args:
            path_tokens = []
            has_placeholder = False
            for arg in custom_path_args:
                if "{path}" in arg:
                    path_tokens.append(arg.replace("{path}", path_arg))
                    has_placeholder = True
                else:
                    path_tokens.append(arg)
            cmd_tokens.extend(path_tokens)
            if not has_placeholder:
                cmd_tokens.append(path_arg)
        else:
            # Default behavior: append path directly
            cmd_tokens.append(path_arg)

    return formatted_prefix + cmd_tokens


def _launch_with_fallback(app_key: str, path_arg: str = None) -> str:
    """Try multiple commands to launch an app, with optional prefix and path argument."""
    app_data = APPS_DATABASE[app_key]
    prefix_candidates = _get_prefix_candidates(app_data)

    for command in app_data["commands"]:
        cmd_tokens = shlex.split(command)
        inner_binary = cmd_tokens[0]

        # Check if the target app binary exists
        if not shutil.which(inner_binary):
            continue

        # Find a working prefix (terminal emulator / wrapper)
        for prefix in prefix_candidates:
            # If a prefix is specified, ensure its binary exists too
            if prefix and not shutil.which(prefix[0]):
                continue

            try:
                full_cmd = _build_final_command(prefix, command, app_data, path_arg)

                subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                target_msg = f" at '{path_arg}'" if path_arg else ""
                return f"Successfully opened {app_key}{target_msg} (ran: `{' '.join(full_cmd)}`)"
            except Exception:
                continue

    # Fallback to gtk-launch
    try:
        cmd_list = ["gtk-launch", app_key]
        if path_arg:
            cmd_list.append(path_arg)

        subprocess.Popen(
            cmd_list,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        target_msg = f" at '{path_arg}'" if path_arg else ""
        return f"✅ Successfully opened {app_key}{target_msg} via desktop launcher"
    except Exception:
        return f"❌ Could not launch '{app_key}'. Tried: {', '.join(app_data['commands'])}"

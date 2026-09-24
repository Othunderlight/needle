#!/usr/bin/env python3
import json
import os
import re
import shlex
import shutil
from pathlib import Path

# Directories where Linux stores desktop launchers
DESKTOP_DIRS = [
    Path.home() / ".local/share/applications",
    Path("/usr/local/share/applications"),
    Path("/usr/share/applications"),
    Path("/var/lib/snapd/desktop/applications"),
    Path("/var/lib/flatpak/exports/share/applications"),
    Path.home() / ".local/share/flatpak/exports/share/applications",
]

# CLI tools/agents to detect even if they don't have a .desktop file
CLI_TOOLS_TO_CHECK = [
    "ngrok",
    "codex",
    "opencode",
    "nvim",
    "tmux",
    "zoxide",
    "gh",
    "git",
    "htop",
    "curl",
    "wget",
]


def clean_exec_string(exec_str: str) -> str:
    """Strips field codes (%u, %F, %k), flatpak file-forwarding markers (@@...@@),

    and leading env variables (e.g. QT_QPA_PLATFORM=xcb, BAMF_...=...).
    """
    # 1. Remove Flatpak @@ markers and XDG field codes
    cleaned = re.sub(r"@@.*?@@", "", exec_str)
    cleaned = re.sub(r"%-?[a-zA-Z0-9]", "", cleaned)
    cleaned = cleaned.strip().strip("\"'")

    if cleaned.endswith("--"):
        cleaned = cleaned[:-2].strip()

    # 2. Split safely with shlex to respect quotes and spaces in file paths
    try:
        tokens = shlex.split(cleaned)
    except ValueError:
        tokens = cleaned.split()

    # 3. Drop 'env' and any environment variable assignments (e.g., VAR=val)
    while tokens and (tokens[0] == "env" or "=" in tokens[0]):
        tokens.pop(0)

    # 4. Reconstruct clean command line
    return shlex.join(tokens)


def extract_command_variants(cleaned_cmd: str) -> list[str]:
    """Returns executable command variations without adding invalid helper binaries."""
    commands = [cleaned_cmd]

    # Don't extract 'flatpak' or 'gapplication' as independent executable commands
    if cleaned_cmd.startswith(("flatpak", "gapplication")):
        return commands

    try:
        tokens = shlex.split(cleaned_cmd)
        if tokens:
            executable = tokens[0]
            binary_name = Path(executable).name
            # If the command was a full path (e.g. /usr/bin/google-chrome), also add the bare name
            if (
                binary_name
                and binary_name != executable
                and binary_name not in commands
            ):
                commands.append(binary_name)
    except Exception:
        pass

    return commands


def slugify(text: str) -> str:
    """Converts a display name into a clean dictionary key (e.g. 'OBS Studio' -> 'obs_studio')."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def parse_desktop_file(filepath: Path) -> dict | None:
    """Parses a single .desktop file and returns structured app data."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    data = {}
    is_desktop_entry = False

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line == "[Desktop Entry]":
            is_desktop_entry = True
            continue
        elif line.startswith("[") and line != "[Desktop Entry]":
            is_desktop_entry = False
            continue

        if is_desktop_entry and "=" in line:
            key, val = line.split("=", 1)
            data[key.strip()] = val.strip()

    # Filter out hidden or non-application entries
    if data.get("Type") != "Application":
        return None
    if data.get("NoDisplay", "false").lower() == "true":
        return None
    if data.get("Hidden", "false").lower() == "true":
        return None

    name = data.get("Name")
    exec_cmd = data.get("Exec")

    if not name or not exec_cmd:
        return None

    cleaned_cmd = clean_exec_string(exec_cmd)
    if not cleaned_cmd:
        return None

    # Collect Aliases
    aliases = set()
    aliases.add(name.lower())

    for word in name.lower().split():
        if len(word) > 2:
            aliases.add(word)

    if data.get("GenericName"):
        aliases.add(data["GenericName"].lower())

    if data.get("Keywords"):
        keywords = [
            k.strip().lower() for k in data["Keywords"].split(";") if k.strip()
        ]
        aliases.update(keywords)

    commands = extract_command_variants(cleaned_cmd)

    return {
        "key": slugify(name),
        "commands": commands,
        "aliases": sorted(list(aliases)),
    }


def scan_installed_apps() -> dict:
    """Scans desktop files and CLI binaries to generate the application database."""
    apps_database = {}
    seen_desktop_names = set()

    # 1. Scan .desktop files
    for directory in DESKTOP_DIRS:
        if not directory.exists():
            continue

        for desktop_file in directory.glob("*.desktop"):
            if desktop_file.name in seen_desktop_names:
                continue

            app_info = parse_desktop_file(desktop_file)
            if app_info:
                key = app_info["key"]

                # Handle duplicate keys (e.g. system_monitor and system_monitor_1)
                counter = 1
                base_key = key
                while key in apps_database:
                    key = f"{base_key}_{counter}"
                    counter += 1

                apps_database[key] = {
                    "commands": app_info["commands"],
                    "aliases": app_info["aliases"],
                }
                seen_desktop_names.add(desktop_file.name)

    # 2. Scan CLI tools on $PATH
    for cli_name in CLI_TOOLS_TO_CHECK:
        cli_path = shutil.which(cli_name)
        if not cli_path:
            continue

        # Check if this CLI tool is already covered by an existing desktop app
        already_registered = False
        for app_data in apps_database.values():
            if any(cli_name in cmd.split() for cmd in app_data["commands"]):
                already_registered = True
                if cli_name not in app_data["aliases"]:
                    app_data["aliases"].append(cli_name)
                    app_data["aliases"].sort()
                break

        # If not registered, add it as a new entry
        if not already_registered and cli_name not in apps_database:
            apps_database[cli_name] = {
                "commands": [cli_name, cli_path],
                "aliases": [cli_name, f"{cli_name} cli", f"{cli_name} tool"],
            }

    return apps_database


def get_apps_database(cache_path: Path = None) -> dict:
    """Retrieves the database from cache if present; otherwise, scans and caches it."""
    if cache_path is None:
        cache_path = (
            Path.home() / ".config" / "my_desktop_app" / "apps_database.json"
        )

    if cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # First run: scan and save
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    db = scan_installed_apps()

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=4)

    return db


if __name__ == "__main__":
    output_file = Path("apps_database.json")
    print("Scanning installed desktop applications and CLI tools...")

    database = scan_installed_apps()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4)

    print(f"Done! Successfully registered {len(database)} applications.")
    print(f"Database saved to: {output_file.resolve()}")

import os
import subprocess
from difflib import get_close_matches
import needle
import shlex
import shutil

from .helpers import _build_alias_map, _fuzzy_lookup

# ==========================================
# MACROS DATABASE
# ==========================================

MACROS_DATABASE = {
    "daddy_is_home": {
        "file": os.path.expanduser("~/auto/macros/start.macro"),
        "runner": "crossmacro play",
        "aliases": ["daddy is home", "dady is home", "dad is home", "daddy home", "start macro"],
        "description": "Crossmacro welcome sequence"
    }
}

MACRO_ALIAS_MAP = _build_alias_map(MACROS_DATABASE)



def _launch_macro(macro_key: str) -> str:
    """Executes a macro script using its defined runner."""
    macro_data = MACROS_DATABASE[macro_key]
    macro_file = os.path.expanduser(macro_data["file"])
    runner_tokens = shlex.split(macro_data.get("runner", "crossmacro play"))

    # 1. Verify runner exists in PATH
    runner_bin = runner_tokens[0]
    if not shutil.which(runner_bin):
        return f"❌ Runner binary '{runner_bin}' not found on system."

    # 2. Verify macro file exists
    if not os.path.exists(macro_file):
        return f"❌ Macro file '{macro_file}' does not exist."

    full_cmd = runner_tokens + [macro_file]

    try:
        subprocess.Popen(
            full_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return f"✅ Successfully executed macro '{macro_key}' (ran: `{' '.join(full_cmd)}`)"
    except Exception as e:
        return f"❌ Failed to run macro '{macro_key}': {e}"


@needle.tool
def run_macro(macro_name: str) -> str:
    """Run an automated macro, routine, or desktop automation sequence by name or trigger phrase.

    Args:
        macro_name: The name or trigger phrase of the macro (e.g., 'daddy is home', 'start work').
    """
    print(f"🔧 Tool called: run_macro with macro_name='{macro_name}'")

    macro_key = _fuzzy_lookup(macro_name, MACRO_ALIAS_MAP)
    if not macro_key:
        return f"❌ Macro '{macro_name}' is not recognized. Available: {', '.join(MACROS_DATABASE.keys())}"

    return _launch_macro(macro_key)

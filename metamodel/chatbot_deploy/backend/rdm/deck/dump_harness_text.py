"""
Snapshot of the harness text the agent receives, for the appendix of the DMDU deck.

Writes harness_text.json next to this file: the rendered system prompt, the seven tool schemas,
the loop settings, the scripted user's reply and the error messages the tools return when a rule
checked in code is broken. The deck builder reads the JSON (it runs in an env without the backend's
dependencies).

    python -m backend.rdm.deck.dump_harness_text
"""

import json
import re
from pathlib import Path

from backend.rdm.harness import agent
from backend.rdm.harness.prompt import system_prompt
from backend.rdm.harness.registry import TOOLS
from backend.rdm.runs import get_run

HERE = Path(__file__).parent
TOOLS_DIR = HERE.parent / "tools"


def tool_errors() -> list:
    """Every `raise ToolError(...)` message in the tools, as written in the code (one per check)."""
    out = []
    for f in sorted(TOOLS_DIR.glob("*.py")):
        src = f.read_text()
        for m in re.finditer(r"raise ToolError\((.*?)\)\n", src, re.S):
            msg = re.sub(r'"\s*\n\s*f?"', "", m.group(1)).strip()
            if msg.startswith(("str(", "f'")) is False and "str(e)" not in msg:
                out.append({"file": f.name, "line": src[:m.start()].count("\n") + 1, "message": msg})
    return out


def main():
    data = {"system_prompt": system_prompt(get_run()),
            "tools": TOOLS,
            "loop": {"model": agent.MODEL, "effort": agent.EFFORT, "max_tokens": agent.MAX_TOKENS,
                     "max_steps": agent.MAX_STEPS, "go_ahead": agent.DEFAULT_REPLY},
            "tool_errors": tool_errors()}
    path = HERE / "harness_text.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print("saved", path, len(data["tool_errors"]), "error messages")


if __name__ == "__main__":
    main()

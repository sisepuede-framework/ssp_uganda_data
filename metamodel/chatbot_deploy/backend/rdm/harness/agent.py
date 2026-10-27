"""
The agent loop: Claude chooses the tools, the harness runs them, everything is logged.

One conversation = one question, in one arm, one repetition. The user side is scripted: the
question, then fixed replies given in order whenever the agent ends its turn to ask something
(e.g. the failure threshold). The run is saved as JSON with every request's token usage, every tool
call (from the harness log) and the final answer.

No server-side model fallback is used: a refusal is recorded as such, because switching model
mid-run would confound the arms.

    python -m backend.rdm.harness.agent --question Q04b --arm v1
"""

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from backend.config import settings
from backend.rdm.harness.prompt import system_prompt
from backend.rdm.harness.registry import TOOLS, Harness

MODEL = "claude-sonnet-5-5"     # decided 2026-10-13: the newest and cheapest; the same in every arm
EFFORT = "medium"
MAX_TOKENS = 16000
MAX_STEPS = 20            # API requests per conversation, the same in every arm
RUNS_DIR = Path(__file__).parents[1] / "eval" / "pilot_runs"

from backend.rdm.eval.questions import GO_AHEAD as DEFAULT_REPLY, SETS  # noqa: E402


def _block(b) -> dict:
    return b.model_dump(exclude_none=True)


def _sha(data) -> str:
    raw = data if isinstance(data, bytes) else json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def versions(h: Harness, system_text: str) -> dict:
    """Fingerprints of everything that shapes a conversation, so each log says exactly what ran."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                                cwd=Path(__file__).parent).stdout.strip()
        # backend/services too: country_context reads the deployed chatbot's services/context.py
        dirty = bool(subprocess.run(["git", "status", "--porcelain", "--", "backend/rdm", "backend/services",
                                     ":(exclude)backend/rdm/eval/pilot_runs"], capture_output=True,
                                    text=True, cwd=Path(__file__).parents[3]).stdout.strip())
    except OSError:
        commit, dirty = None, None
    tables = Path(__file__).parents[1] / "data" / "tables"
    return {"git_commit": commit, "rdm_code_uncommitted_changes": dirty,
            "system_prompt_sha": _sha(system_text.encode()), "tools_sha": _sha(TOOLS),
            "tables_sha": {f.name: _sha(f.read_bytes()) for f in sorted(tables.glob(f"{h.run.name}_*"))},
            "surrogate_sha": _sha(h.run.surrogate_path.read_bytes()) if getattr(h.run, "surrogate_path", None) else None}


def converse(question: str, arm: str, replies: list | None = None, model: str = MODEL, effort: str = EFFORT,
             client: anthropic.Anthropic | None = None, harness: Harness | None = None) -> dict:
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    h = harness or Harness(arm)
    system_text = system_prompt(h.run)
    system = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    replies = list(replies or [])
    messages = [{"role": "user", "content": question}]
    user_messages = [{"user_turn": 1, "after_step": None, "kind": "question", "text": question}]
    h.user_turn = 1
    requests, answers, stop, used_default = [], [], None, False
    t0, started = time.time(), datetime.now(timezone.utc).isoformat()

    for step in range(MAX_STEPS):
        r = client.messages.create(model=model, max_tokens=MAX_TOKENS, system=system, tools=TOOLS,
                                   messages=messages, output_config={"effort": effort},
                                   # display only: thinking is billed the same, the summary is kept in the log
                                   thinking={"type": "adaptive", "display": "summarized"})
        u = r.usage
        requests.append({"step": step, "stop_reason": r.stop_reason,
                         "input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                         "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0,
                         "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0})
        messages.append({"role": "assistant", "content": [_block(b) for b in r.content]})
        stop = r.stop_reason

        if r.stop_reason == "tool_use":
            results = []
            for b in r.content:
                if b.type != "tool_use":
                    continue
                out = h.call(b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": json.dumps(out, ensure_ascii=False, default=str),
                                **({"is_error": True} if "error" in out else {})})
            messages.append({"role": "user", "content": results})
            continue

        text = "\n".join(b.text for b in r.content if b.type == "text")
        answers.append(text)
        if r.stop_reason in ("refusal", "max_tokens"):
            break
        # The scripted user answers whenever the agent hands the turn back with a question pending:
        # a scripted reply if one is left, otherwise a neutral go-ahead (once).
        if r.stop_reason == "end_turn" and (replies or (text.rstrip().endswith("?") and not used_default)):
            kind = "scripted" if replies else "go_ahead"
            used_default = used_default or not replies
            reply = replies.pop(0) if replies else DEFAULT_REPLY
            messages.append({"role": "user", "content": reply})
            h.user_turn += 1
            user_messages.append({"user_turn": h.user_turn, "after_step": step, "kind": kind, "text": reply,
                                  "agent_asked": "?" in text})
            continue
        break

    return {"question": question, "arm": arm, "model": model, "effort": effort, "versions": versions(h, system_text),
            "user_messages": user_messages, "final_answer": answers[-1] if answers else "",
            "started": started, "seconds": round(time.time() - t0, 1),
            "final_stop_reason": stop, "steps": len(requests), "hit_step_limit": len(requests) == MAX_STEPS,
            "requests": requests, "tool_log": h.log, "answers": answers, "messages": messages}


def run_one(qid: str, arm: str, rep: int, qset: str = "pilot", **kw) -> Path:
    q = SETS[qset][qid]
    res = converse(q["question"], arm, q["replies"], **kw)
    res.update(question_id=qid, rep=rep, question_set=qset)
    out = RUNS_DIR / kw.get("model", MODEL) / qset
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{qid}_{arm}_r{rep}.json"
    path.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    return path


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--set", default="pilot", choices=list(SETS))
    a.add_argument("--question", default="Q04b")
    a.add_argument("--arm", default="v1")
    a.add_argument("--rep", type=int, default=0)
    a.add_argument("--model", default=MODEL)
    args = a.parse_args()
    print(run_one(args.question, args.arm, args.rep, args.set, model=args.model))

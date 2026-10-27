"""
Failure modes, read from the conversation logs: the evaluation of the system (RQ1) and, compared across
arms, its outcome measures (RQ2: tool use, policy levels and uncertainty ranges set).

One row per conversation, one column per failure mode (True = the failure happened; None = the check
does not apply to that question). Three kinds of check:

  A · tool calls (exact):    1 no information before the run · 2 literal translation · 3 level off the key ·
                             4 uncertainty fixed · 5 no uncertainty range on the asked side ·
                             6 uncertainty used as a lever · 7 invented threshold · 8 required step skipped ·
                             9 ran an out-of-model question before clarifying · 10 asked for a level beyond the
                             explored range · 11 loop (same failing call twice) · 12 did not finish
  B · final answer (rules):  13 forecast language · 14 names a winner · 15 numbers not found in any tool reply
                             or in the question · 16 a single number where a range was available
  C · final answer (reader): 17 wrong direction of an effect · 18 wrong source for a number · 22 a required
                             statement missing (spec ``must_say``) — only with --reader, a small model reads the
                             answer against what the question expects
  D · question-specific:     19 a required mention missing (``must_mention``, regexes on the answer) ·
                             20 a lever outside the allowed set (``allowed_levers``) · 21 no package tested
                             (``package``) · 23 revised policy not re-tested with the same threshold (``retest``) ·
                             24 a scripted threshold reply given before the agent asked for it (the script fell
                             out of step) · 25 a required node never visited with model_network (``visit``: one
                             regex per node, matched against the node argument of the calls that worked)
  Recorded, not a failure:   network_calls (model_network calls that worked), x_ranges_set

A question with several levers lists them in ``levers`` ({id: {key_level, user_number}}); checks 1–3 run for each.
A conversation that holds several questions (Q10b → D2b → N1) lists them in ``parts``, each with the user turn it
starts at; every part is checked on its own calls and answers, and its columns carry its id as prefix.

What each question expects comes from its spec (``SPECS`` in questions.py); checks without a spec field
are skipped for that question. Logs written before 2026-10-19 lack user turns and error codes, so
checks 6, 7, 9 and 10 read as None for them.

    python -m backend.rdm.eval.failure_modes <runs dir> [--reader]   → <runs dir>/failure_modes.csv
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

LEVEL_TOL = 0.05          # default tolerance on a lever level (0–1 scale)
X_FIXED_WIDTH = 0.1       # an uncertainty range narrower than this counts as fixing it
YEARS = set(range(2015, 2071))
MODEL_YEARS = {2025, 2035, 2040, 2050, 2060, 2070}

FORECAST = re.compile(r"\b(will (?:be|reach|fall|rise|drop|increase|decrease|cut|reduce)|predicts?|predicted|"
                      r"projections?|forecasts?)\b", re.I)
NEGATION = re.compile(r"\b(not|no|none|nothing|never|neither|nor)\b[^.]{0,30}$", re.I)   # "… is not a forecast"
CATALOGUE_REF = re.compile(r"\(\s*\d{1,2}(?:\s*[–,-]\s*\d{1,2})*\s*\)|\bp\d{1,2}\b|\b[LX]\s?\d{1,2}\b|\b(?:levers?|uncertaint(?:y|ies)|ids?)\s+\d{1,2}(?:\s*(?:,|and|or|&|–|-|to)\s*\d{1,2})*\b", re.I)
WINNER = re.compile(r"\b(the best (?:option|policy|choice)|you should (?:choose|pick|go with|prioriti[sz]e)|"
                    r"I(?: would|'d)? (?:recommend|suggest)|should be prioriti[sz]ed|"
                    r"is (?:clearly )?(?:the )?(?:better|more effective|preferable) (?:option|policy|choice)?)", re.I)
RANGE = re.compile(r"(\d\s*(?:–|-|to)\s*-?\d)|\b(range|between|p10|p90|percentile|median)\b", re.I)
NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*\.?\d*")


def _calls(run: dict, tool: str | None = None) -> list:
    return [c for c in run.get("tool_log", []) if tool is None or c["tool"] == tool]


def _policies(call: dict) -> dict:
    """{policy name: {lever id: level}} from a log entry, old or new format."""
    if call.get("params"):
        return {n: {int(k): float(v) for k, v in lv.items() if str(k).isdigit()}
                for n, lv in call["params"].get("policies", {}).items()}
    out = {}
    for p in (call.get("args") or {}).get("policies") or []:
        lv = p.get("levers") or {}
        out[str(p.get("name"))] = {int(k): float(v) for k, v in lv.items() if str(k).isdigit()}
    return out


def _x_ranges(call: dict) -> dict:
    raw = (call.get("params") or {}).get("x_ranges") or (call.get("args") or {}).get("x_ranges") or {}
    return {int(k): (float(v[0]), float(v[1])) for k, v in raw.items() if str(k).isdigit() and len(v) == 2}


def _numbers(obj) -> set:
    """Every number in a JSON-like object or text."""
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return {float(obj)}
    if isinstance(obj, dict):
        return set().union(*(_numbers(v) for v in obj.values())) if obj else set()
    if isinstance(obj, (list, tuple)):
        return set().union(*(_numbers(v) for v in obj)) if obj else set()
    if isinstance(obj, str):
        out = set()
        for m in NUMBER.findall(obj):
            try:
                out.add(float(m.replace(",", "")))
            except ValueError:
                pass
        return out
    return set()


def _harness_numbers() -> set:
    """Counts every agent is told by the harness: how many levers and uncertainties, the default number of futures.
    Only these: the prompt also lists every lever id, which would trace almost any number below 55."""
    global _HARNESS_NUMBERS
    if _HARNESS_NUMBERS is None:
        try:
            from backend.rdm.runs import get_run
            from backend.rdm.tools.common import groups
            from backend.rdm.tools.technical import DEFAULT_FUTURES
            kinds = [g["kind"] for g in groups(get_run()).values()]
            _HARNESS_NUMBERS = {float(kinds.count("L")), float(kinds.count("X")), float(DEFAULT_FUTURES)}
        except Exception:  # noqa: BLE001 — scoring still works without the run files
            _HARNESS_NUMBERS = set()
    return _HARNESS_NUMBERS


_HARNESS_NUMBERS = None


def _traced(x: float, pool: set) -> bool:
    """A stated number counts as traced if a tool reply or the question has it, allowing for rounding,
    a percent written as a share (or the reverse) and a sign dropped in words ("a 5% cut")."""
    for cand in (x, -x, x / 100, -x / 100, x * 100, -x * 100):
        for y in pool:
            if y == cand or (y != 0 and abs(cand - y) <= max(0.02 * abs(y), 0.051)):
                return True
    return False


def _node_lever(args: dict):
    """The lever id a model_network call starts from, as a string; None for an output node."""
    hit = re.match(r"^(?:lever\s*|l\s*)?(\d+)$", str(args.get("node", "")).strip(), re.I)
    return hit.group(1) if hit else None


def _lever_checks(calls: list, explore: list, first_run, kind, spec: dict, lever) -> dict:
    """Checks 1–3 for one lever."""
    f = {}
    # 1 · no information before the run (T1, T2: the target lever is read before any run, or at all if no run)
    if kind in ("T1", "T2") and lever is not None:
        before = calls if first_run is None else calls[:first_run]
        f["01_no_information_before_run"] = not any(
            c["tool"] == "model_network" and _node_lever(c.get("args") or {}) == str(lever) for c in before)
    # 2, 3 · the level set for the target lever in the first run that sets it
    levels = [lv[lever] for c in explore for lv in _policies(c).values() if lever is not None and lever in lv]
    first_levels = []
    for c in explore:
        first_levels = [lv[lever] for lv in _policies(c).values() if lever in lv]
        if first_levels:
            break
    if spec.get("user_number") is not None and lever is not None:
        literal = spec["user_number"] if isinstance(spec["user_number"], list) else [spec["user_number"]]
        f["02_literal_translation"] = any(abs(v - u) < 0.005 for v in levels for u in literal)
    if spec.get("key_level") is not None and kind == "T3":
        # an emissions target is reached by trying several levels: off the key if no level tried is near it
        f["03_level_off_key"] = not any(abs(v - spec["key_level"]) <= spec.get("tol", LEVEL_TOL) for v in levels)
        f["level_set"] = sorted(set(levels))
    elif spec.get("key_level") is not None:
        if first_levels:
            # The top of the range run next to one other level is a reference point, not bracketing
            # (same rule as summarize_pilot.py).
            distinct = sorted(set(first_levels))
            own = [v for v in distinct if v < 1.0] if len(distinct) == 2 and distinct[-1] == 1.0 else distinct
            committed = len(own) == 1
            f["03_level_off_key"] = (not committed) or abs(own[0] - spec["key_level"]) > spec.get("tol", LEVEL_TOL)
            f["level_set"] = own[0] if committed else distinct
        else:
            f["03_level_off_key"] = spec.get("run_expected", True)
            f["level_set"] = None
    return f


def check(run: dict, spec: dict | None = None) -> dict:
    spec = spec or {}
    kind = spec.get("kind")
    calls = _calls(run)
    explore = _calls(run, "exploratory_modeling")
    first_run = next((i for i, c in enumerate(calls) if c["tool"] == "exploratory_modeling"), None)
    new_log = any("user_turn" in c for c in calls)
    answer = run.get("final_answer") or (run.get("answers") or [""])[-1]
    if spec.get("parts"):
        return _check_parts(run, spec)
    f = {}

    if spec.get("levers"):
        for lid, sub in spec["levers"].items():
            for k, v in _lever_checks(calls, explore, first_run, kind, {**spec, **sub}, lid).items():
                f[k] = (f.get(k, False) or v) if k[:2].isdigit() else {**f.get(k, {}), str(lid): v}
    else:
        f.update(_lever_checks(calls, explore, first_run, kind, spec, spec.get("lever")))
    # 4, 5 · uncertainty ranges
    ranges = [r for c in explore for r in _x_ranges(c).items()]
    f["04_uncertainty_fixed"] = any(hi - lo < X_FIXED_WIDTH for _, (lo, hi) in ranges) or any(
        c.get("error_code") == "X_FIXED" for c in calls)
    for x, side in (spec.get("x_side") or {}).items():
        got = [r for xid, r in ranges if xid == int(x)]
        # Right if at least one range sits on the asked side; an extra range on the other side is a contrast
        # (HC1 smoke test 2026-10-26: [0.67, 1] plus [0, 0.33] to compare), not a mistake.
        wrong = not any((lo >= 0.5) if side == "high" else (hi <= 0.5) for lo, hi in got)
        f["05_uncertainty_range_wrong_or_missing"] = f.get("05_uncertainty_range_wrong_or_missing", False) or wrong
        f["x_ranges_set"] = {**f.get("x_ranges_set", {}), str(x): got}
    # 6 · uncertainty used as a lever
    f["06_uncertainty_as_lever"] = any(c.get("error_code") == "X_AS_LEVER" for c in calls) if new_log else None
    # 7 · invented threshold: a threshold given before the user ever replied (when the question says none)
    vul = _calls(run, "vulnerability_analysis")
    start = spec.get("from_user_turn", 1)
    if spec.get("needs_threshold"):
        f["07_invented_threshold"] = (any((c.get("args") or {}).get("threshold") is not None
                                          and c.get("user_turn") == start for c in vul) if new_log else None)
    # 8 · required step skipped
    req = spec.get("required_tools") or []
    if req:
        called = {c["tool"] for c in calls if c["status"] == "ok"}
        f["08_required_step_skipped"] = not set(req) <= called
    if spec.get("compare"):
        same = any(len(_policies(c)) >= 2 for c in explore) or bool(_calls(run, "trade_off_analysis"))
        f["08_required_step_skipped"] = f.get("08_required_step_skipped", False) or not same
    # 9 · out-of-model question run before clarifying
    if kind == "T4":
        f["09_ran_before_clarifying"] = (any(c.get("user_turn") == start for c in explore) if new_log
                                         else bool(explore))
    # 10, 11, 12 · range, loops, finishing
    f["10_level_beyond_range_attempted"] = (any(c.get("error_code") == "LEVEL_OUT_OF_RANGE" for c in calls)
                                           if new_log else None)
    errs = [(c["tool"], json.dumps(c.get("args"), sort_keys=True)) for c in calls if c["status"] == "error"]
    f["11_loop"] = len(errs) != len(set(errs))
    f["12_did_not_finish"] = bool(run.get("hit_step_limit")) or run.get("final_stop_reason") in ("max_tokens", "refusal")

    # B · the final answer
    asserted = lambda rx: any(not NEGATION.search(answer[max(0, m.start() - 40):m.start()]) for m in rx.finditer(answer))
    f["13_forecast_language"] = asserted(FORECAST)
    f["14_names_a_winner"] = asserted(WINNER)          # "neither option is better" is not a winner
    pool = (_numbers([c.get("reply") for c in calls]) | _numbers([c.get("args") for c in calls])
            | _numbers(run.get("question", "")) | _numbers([m.get("text") for m in run.get("user_messages", [])])
            | _harness_numbers())
    # Lever/uncertainty ids written as "(40)", "L35" or "lever 35", and "p10/p90", are references, not results.
    stated = [x for x in _numbers(CATALOGUE_REF.sub(" ", answer)) if x not in YEARS and abs(x) > 10]
    untraced = sorted(x for x in stated if not _traced(x, pool))
    f["15_untraced_numbers"] = bool(untraced)
    f["untraced"] = untraced[:10]
    f["16_single_number_no_range"] = bool(explore) and not RANGE.search(answer)

    # D · question-specific
    if spec.get("must_mention"):
        missing = [r for r in spec["must_mention"] if not re.search(r, answer, re.I)]
        f["19_mention_missing"], f["missing_mentions"] = bool(missing), missing
    ok_explore = [c for c in explore if c["status"] == "ok"]
    set_levers = [{k for k, v in lv.items() if v > 0} for c in ok_explore for lv in _policies(c).values()]
    if spec.get("allowed_levers"):
        outside = sorted(set().union(*set_levers) - set(spec["allowed_levers"])) if set_levers else []
        f["20_lever_outside_allowed"], f["levers_outside"] = bool(outside), outside
    if spec.get("package"):
        f["21_no_package_tested"] = not any(len(lv) >= 2 for lv in set_levers)
    if spec.get("retest"):
        # the revised policy is re-tested: a new ensemble from this part, judged with the threshold set earlier
        made = {(c.get("params") or {}).get("ensemble_created") or (c.get("reply") or {}).get("ensemble_id")
                for c in ok_explore}
        ref = next((c for c in run.get("earlier_calls", []) + vul
                    if c["tool"] == "vulnerability_analysis" and (c.get("args") or {}).get("threshold") is not None), None)
        key = lambda c: tuple((c.get("args") or {}).get(k) for k in ("metric", "year", "threshold", "threshold_type"))
        f["23_not_retested"] = ref is None or not any(
            c["status"] == "ok" and key(c) == key(ref) and (c.get("args") or {}).get("ensemble_id") in made for c in vul)
    if spec.get("needs_threshold") and new_log:
        # the scripted threshold reply only makes sense after the agent asked for it
        reply = next((m for m in run.get("user_messages", []) if m.get("user_turn") == start + 1), None)
        asked = any((c.get("reply") or {}).get("status") == "needs_threshold" and c.get("user_turn") == start for c in vul)
        # a question anywhere in the answer before the reply counts (dry run 2026-10-26: the agent asked for the
        # threshold mid-answer and went on, so "ends with ?" missed it)
        answers = run.get("all_answers") or run.get("answers") or []
        before = answers[start - 1] if len(answers) >= start else ""
        asked_in_text = "?" in before or bool(re.search(r"\bthreshold\b|counts? as (?:a )?fail", before, re.I))
        f["24_script_out_of_step"] = reply is not None and not (reply.get("agent_asked") or asked or asked_in_text)
    nodes = [str((c.get("args") or {}).get("node", "")) for c in calls
             if c["tool"] == "model_network" and c["status"] == "ok"]
    f["network_calls"] = len(nodes)
    if spec.get("visit"):
        missing = [rx for rx in spec["visit"] if not any(re.search(rx, n, re.I) for n in nodes)]
        f["25_required_node_not_visited"], f["nodes_not_visited"] = bool(missing), missing
    f["fail_share"] = [(c.get("reply") or {}).get("share_fail") for c in vul if c["status"] == "ok"
                       and "share_fail" in (c.get("reply") or {})] or None
    f["years_not_in_model"] = sorted({int(y) for c in calls for y in
                                      ((c.get("args") or {}).get("years") or [(c.get("args") or {}).get("year")])
                                      if isinstance(y, (int, float)) and int(y) not in MODEL_YEARS}) or None
    return f


def _part_runs(run: dict, spec: dict):
    """(part spec, the run cut to that part): its own tool calls and answers, by the user turn each started at."""
    parts, calls, answers = spec["parts"], _calls(run), run.get("answers") or []
    starts = [p["from_user_turn"] for p in parts] + [None]
    for i, part in enumerate(parts):
        a, b = starts[i], starts[i + 1]
        inside = lambda t: t is not None and t >= a and (b is None or t < b)
        last = b is None
        yield {**part, "from_user_turn": a}, {
            **run, "tool_log": [c for c in calls if inside(c.get("user_turn"))],
            "earlier_calls": [c for c in calls if (c.get("user_turn") or 0) < a],
            "question": part.get("question", run.get("question")),
            "answers": [], "all_answers": answers, "final_answer": "\n\n".join(answers[a - 1:None if last else b - 1]),
            "hit_step_limit": run.get("hit_step_limit") if last else False,
            "final_stop_reason": run.get("final_stop_reason") if last else None,
            "reached": any(m.get("user_turn") == a for m in run.get("user_messages", [])) or a == 1}


def _check_parts(run: dict, spec: dict) -> dict:
    f = {}
    for part, sub in _part_runs(run, spec):
        f[f"{part['id']}:reached"] = sub["reached"]
        if sub["reached"]:
            f.update({f"{part['id']}:{k}": v for k, v in check(sub, {k: v for k, v in part.items() if k != "id"}).items()})
    return f


def _read(question: str, answer: str, spec: dict, client, model: str) -> dict:
    want = {k: spec[k] for k in ("expected_direction", "expected_source") if spec.get(k)}
    claims = spec.get("must_say") or []
    if not (want or claims):
        return {}
    prompt = (f"Question asked: {question}\nAnswer given:\n{answer}\n\n"
              f"Expected: {json.dumps(want)}\nRequired statements: {json.dumps(claims)}\n"
              "Reply with JSON only: {\"wrong_direction\": true|false|null, \"wrong_source\": true|false|null, "
              "\"says\": [true|false, one per required statement, in order], \"why\": \"<one sentence>\"}. "
              "wrong_direction: the answer states the effect goes the other way from expected_direction. "
              "wrong_source: the answer attributes a number to a different source than expected_source (e.g. says it "
              "was tested on the surrogate when it comes from the model runs). null when the answer does not say "
              "or nothing is expected. says: whether the answer makes each required statement, in any wording.")
    # Haiku 5.5 thinks by default: room for it, low effort, and read the text block (not the first block)
    r = client.messages.create(model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt}],
                               output_config={"effort": "low"})
    text = "".join(b.text for b in r.content if b.type == "text").strip()
    try:
        out = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text))
    except ValueError:
        return {"17_wrong_direction": None, "18_wrong_source": None, "reader_note": "unreadable reply"}
    says = out.get("says") or []
    row = {"17_wrong_direction": out.get("wrong_direction"), "18_wrong_source": out.get("wrong_source"),
           "reader_note": out.get("why")}
    if claims:
        missing = [c for c, ok in zip(claims, says) if ok is False]
        row.update({"22_statement_missing": bool(missing) if len(says) == len(claims) else None,
                    "missing_statements": missing})
    return row


def reader_check(run: dict, spec: dict, client=None, model: str = "claude-haiku-5-5") -> dict:
    """17, 18, 22 · a small model reads the final answer against what the question expects (direction, source,
    required statements)."""
    if not any(spec.get(k) or any(p.get(k) for p in spec.get("parts", []))
               for k in ("expected_direction", "expected_source", "must_say")):
        return {}
    import anthropic
    from backend.config import settings      # the same key the harness uses
    client = client or anthropic.Anthropic(api_key=settings.anthropic_api_key or None)
    if spec.get("parts"):
        return {f"{p['id']}:{k}": v for p, sub in _part_runs(run, spec) if sub["reached"]
                for k, v in _read(sub["question"], sub["final_answer"], p, client, model).items()}
    return _read(run.get("question"), run.get("final_answer") or run["answers"][-1], spec, client, model)


def table(runs_dir: Path, reader: bool = False) -> pd.DataFrame:
    from backend.rdm.eval.questions import BANK_SPECS, SPECS
    rows = []
    for p in sorted(runs_dir.rglob("*.json")):
        run = json.loads(p.read_text())
        if "tool_log" not in run:
            continue
        spec = (BANK_SPECS if run.get("question_set") == "bank" else SPECS).get(run.get("question_id"), {})
        row = {"file": str(p.relative_to(runs_dir)), "question_id": run.get("question_id"), "arm": run.get("arm"),
               "rep": run.get("rep"), "tag": spec.get("tag"), "kind": spec.get("kind"), **check(run, spec)}
        if reader:
            row.update(reader_check(run, spec))
        rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("runs_dir", type=Path)
    a.add_argument("--reader", action="store_true")
    args = a.parse_args()
    t = table(args.runs_dir, args.reader)
    out = args.runs_dir / "failure_modes.csv"
    t.to_csv(out, index=False)
    flags = [c for c in t.columns if re.match(r"^(\w+:)?\d\d_", c)]
    print(t.groupby("arm")[flags].mean(numeric_only=False).round(2).T.to_string() if len(t) else "no runs")
    print("saved", out)

# Requires xlsxwriter. Run from metamodel/chatbot_deploy:
#   PYTHONPATH=. python results_analysis/code/write_review_workbook.py [RUNS_DIR] [OUT.xlsx]
"""Full-run review workbook (results_analysis/full_run_review.xlsx) and analysis tables (full_run_analysis.xlsx): every conversation in one row, for checking by hand.

Header colours keep the sources apart: blue = read from the log, green = code rules on the log (failure_modes.py),
orange = the Haiku reader (checks 13, 14, 17, 18, 22), yellow = empty, for the reviewer. Reads the run JSONs and
failure_modes.csv; no API calls.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd
import xlsxwriter

from backend.rdm.eval import failure_modes
from backend.rdm.eval.analyze_bank import HYPOTHESIS
from backend.rdm.eval.questions import BANK_SPECS

RUNS = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend/rdm/eval/pilot_runs/bank_v3_full")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).parents[1] / "full_run_review.xlsx"
OUT_STATS = OUT.with_name("full_run_analysis.xlsx")    # tidy tables for statistics (pandas: pd.read_excel(..., sheet_name=...))

FONT = "Arial"
FILL = {"log": "DDEBF7", "rule": "E2EFDA", "reader": "FCE4D6", "you": "FFF2CC", "id": "EDEDED"}
NUMBER = re.compile(r"-?\d+(\.\d+)?")
CELL_MAX = 32000                       # Excel's limit is 32,767 characters per cell
READER = re.compile(r"(^|:)(13_|14_|17_|18_|22_|reader_note|missing_statements)")

QUESTION_TYPES = {   # the seven groups of docs/test_questions.docx (write_test_questions_docx.GROUPS)
    "1 evaluate a policy in real-world units": ["P50i", "P12i", "B6", "AG1", "LV1", "BLD1", "WW1", "H1", "H2", "H3", "X1"],
    "2 in-between quantities": ["S50", "S3", "S35"],
    "3 reach an emissions target": ["AG2", "C4b", "X2"],
    "4 robustness": ["Q10b", "D3b"],
    "5 trade-offs": ["Q14b", "TO1"],
    "6 outside the model": ["B8b", "F2", "F3b"],
    "7 hypothesis (v0 vs v1)": ["HA1", "HB1", "HC1", "HD1", "HE1"],
}
QTYPE = {q: k for k, qs in QUESTION_TYPES.items() for q in qs}
ARG_COLS = ["node", "year", "lever", "third", "uncertainty", "years", "metrics", "x_ranges", "n_futures", "ensemble_id",
            "policy", "metric", "threshold", "threshold_type", "pass_if", "label_id", "topic"]

CHECKS = [   # number, plain name, how it is computed, failure when
    ("01", "No information before the run", "rule", "the agent ran a policy without first reading the lever or an input it sets"),
    ("02", "Literal translation", "rule", "the user's number (e.g. 30%) was set as the lever level (0.30) as is"),
    ("03", "Level off the key", "rule", "the lever level set is outside the answer key ± tolerance"),
    ("04", "Uncertainty fixed", "rule", "the agent fixed an uncertainty at one value instead of a range"),
    ("05", "Uncertainty range wrong or missing", "rule", "no uncertainty range in the outer third the question asks for"),
    ("06", "Uncertainty used as a lever", "rule", "the agent treated an uncertainty as something the policy controls"),
    ("07", "Invented threshold", "rule", "the agent made up a success threshold the user never gave"),
    ("08", "Required step skipped", "rule", "a tool the question needs was never called"),
    ("09", "Ran before clarifying", "rule", "ran an out-of-model question before asking the user what they meant"),
    ("10", "Level beyond range attempted", "rule", "asked for a lever level outside the explored range"),
    ("11", "Loop", "rule", "the same failing call twice"),
    ("12", "Did not finish", "rule", "hit the step limit or stopped without a final answer"),
    ("13", "Forecast language", "Haiku", "the agent presents a model result as a prediction of what will happen "
     "(word-list version kept as 13w_forecast_words)"),
    ("14", "Names a winner", "Haiku", "the agent declares one option best overall or recommends one "
     "(word-list version kept as 14w_winner_words)"),
    ("15", "Untraced numbers", "rule", "a number in any answer is in no tool reply, the question or the prompt "
     "(every number except years and small counts 0–10)"),
    ("16", "Single number, no range", "rule", "no numeric range ('a–b', 'between a and b') where a run was made"),
    ("17", "Wrong direction", "Haiku", "the answer says the effect goes the other way from the expected direction"),
    ("18", "Wrong source", "Haiku", "the answer credits a number to the wrong source (e.g. surrogate vs model runs)"),
    ("19", "Required mention missing", "rule", "a required phrase or number (regex) is not in the answer"),
    ("20", "Lever outside allowed", "rule", "the user's package was never tested, or outside levers named without a run"),
    ("21", "No package tested", "rule", "the question asks for a package and none was run"),
    ("22", "Required statement missing", "Haiku", "the answer does not make a statement the question requires"),
    ("23", "Not re-tested", "rule", "a revised policy was not re-tested with the same threshold"),
    ("24", "Script out of step", "rule", "the scripted user reply came before the agent asked for it"),
    ("25", "Required node not visited", "rule", "model_network never visited a node the question needs"),
]


def clip(text: str) -> str:
    text = text or ""
    return text if len(text) <= CELL_MAX else text[:CELL_MAX] + " … [cut: open the JSON file for the rest]"


def mark(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    if str(v) in ("True", "False"):
        return "FAIL" if str(v) == "True" else "ok"
    return v


TOOLS = ["model_network", "exploratory_modeling", "vulnerability_analysis", "scenario_discovery",
         "trade_off_analysis", "country_context"]


def tool_counts(run: dict) -> dict:
    used = [c["tool"] for c in run.get("tool_log", [])]
    return {f"{t} calls": used.count(t) for t in TOOLS}


def summary(run: dict) -> str:
    n = tool_counts(run)
    return " · ".join(f"{k[:-6]} ×{v}" for k, v in n.items() if v) or "no tools"


def calls(run: dict) -> str:
    return summary(run) + "\n" + "\n".join(f"{i}. {c['tool']}({json.dumps(c.get('args'), ensure_ascii=False)})"
                     + ("" if c.get("status") == "ok" else f"  → ERROR {c.get('error_code')}")
                     for i, c in enumerate(run.get("tool_log", []), 1))


def thinking(run: dict) -> str:
    return "\n---\n".join(b["thinking"].strip() for m in run["messages"] if isinstance(m["content"], list)
                          for b in m["content"] if b.get("type") == "thinking" and b.get("thinking"))


def log_row(run: dict, file: str) -> dict:
    req = run.get("requests", [])
    return {
        "Question text": run["question"],
        "Model": run["model"], "Effort": run["effort"], "Started (UTC)": run["started"][:19].replace("T", " "),
        "Seconds": run["seconds"], "API steps": run["steps"], "Stop reason": run["final_stop_reason"],
        "Hit step limit": "yes" if run["hit_step_limit"] else "no",
        "Input tokens": sum(r["input_tokens"] for r in req), "Output tokens": sum(r["output_tokens"] for r in req),
        "Cache read tokens": sum(r["cache_read"] for r in req),
        "Scripted user replies": "\n".join(f"[turn {m['user_turn']}] {m['text']}" for m in run["user_messages"]
                                           if m["kind"] != "question"),
        "Number of tool calls": len(run.get("tool_log", [])), **tool_counts(run),
        "Tool calls in order (arguments)": calls(run),
        "Tool errors": ", ".join(c["error_code"] for c in run.get("tool_log", []) if c.get("error_code")),
        "Tool reply sizes (characters)": ", ".join(str(c.get("reply_chars")) for c in run.get("tool_log", [])),
        "Thinking summary": clip(thinking(run)),
        "Final answer": clip(run.get("final_answer") or "\n\n".join(run.get("answers", []))),
        "Git commit": run["versions"]["git_commit"][:7], "Log file": file,
    }


def sheet(wb, name: str, header: list, groups: list, rows: list, widths: dict, height=None, freeze=(1, 4)):
    """Write one table: coloured header, wrapped text, filters. Text is always written as text (never a formula)."""
    ws = wb.add_worksheet(name)
    fmt = {g: wb.add_format({"font_name": FONT, "font_size": 10, "bold": True, "text_wrap": True, "valign": "top",
                             "bg_color": "#" + FILL[g], "border": 1}) for g in set(groups)}
    body = wb.add_format({"font_name": FONT, "font_size": 10, "text_wrap": True, "valign": "top"})
    for j, (h, g) in enumerate(zip(header, groups)):
        ws.write_string(0, j, h, fmt[g])
        ws.set_column(j, j, widths.get(h, 12))
    for i, row in enumerate(rows, 1):
        for j, v in enumerate(row):
            if v is None or (isinstance(v, float) and pd.isna(v)) or v == "":
                continue
            if isinstance(v, str) and NUMBER.fullmatch(v):          # no "number stored as text" warnings
                v = float(v)
            if isinstance(v, str):
                ws.write_string(i, j, v, body)
            else:
                ws.write_number(i, j, float(v), body)
        if height:
            ws.set_row(i, height)
    ws.freeze_panes(*freeze)
    ws.autofilter(0, 0, len(rows), len(header) - 1)
    return ws


def main():
    fm = pd.read_csv(RUNS / "failure_modes.csv")
    sample = pd.read_csv(RUNS / "reader_check_sample.csv")
    in_sample = {(f, "" if pd.isna(p) else p) for f, p in zip(sample.file, sample.part)}
    check_cols = [c for c in fm.columns if c not in ("file", "question_id", "arm", "rep", "tag", "kind")]
    rule_cols = [c for c in check_cols if not READER.search(c)]
    reader_cols = [c for c in check_cols if READER.search(c)]

    rows = []
    for _, r in fm.iterrows():
        run = json.load(open(RUNS / r.file))
        ids = {"Question": r.question_id, "Group": "hypothesis" if r.question_id in HYPOTHESIS else r.tag,
               "Arm": r.arm, "Rep": int(r.rep)}
        parts = sorted(p for f, p in in_sample if f == r.file)
        rows.append({**ids, **log_row(run, r.file), **{c: mark(r[c]) for c in rule_cols + reader_cols},
                     "In reader check (20)": ", ".join(p or "yes" for p in parts),
                     "Your mark (agree / disagree)": "", "Your comment": ""})
    t = pd.DataFrame(rows).sort_values(["Question", "Arm", "Rep"])
    log_cols = [c for c in t.columns if c not in ("Question", "Group", "Arm", "Rep") and c not in check_cols
                and not c.startswith(("In reader", "Your"))]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb = xlsxwriter.Workbook(OUT)
    lines = [
        ("Full run review · bank v3 · 290 conversations (29 conversations × arms v0/v1 × 5 repetitions)", None),
        (f"Source: {RUNS.name}/ (one JSON log per conversation) and failure_modes.csv. "
         "Written by results_analysis/code/write_review_workbook.py; no numbers typed by hand.", None),
        ("", None),
        ("Header colours", None),
        ("Blue = read straight from the log (what the agent did and said)", "log"),
        ("Green = code rules applied to the log (failure_modes.py): FAIL = the failure happened, ok = it did not, "
         "empty = the check does not apply to this question", "rule"),
        ("Orange = the Haiku reader (Claude Haiku 5.5) read the whole conversation (every answer): checks 13, 14, 17, 18, 22 and its one-sentence note", "reader"),
        ("Yellow = for you: your mark and comment", "you"),
        ("", None),
        ("Sheets", None),
        ("By question: the 5 answers to each question side by side, one row per question and arm", None),
        ("All conversations: one row per conversation, every column we store", None),
        ("Checks: what each check means and how it is computed", None),
        ("Haiku reader: what the reader model sees and the prompt it gets, word for word", None),
        ("", None),
        ("How to do the reader check: in 'All conversations', filter 'In reader check (20)' to non-empty, read the "
         "conversation, and put agree / disagree with the orange columns in 'Your mark'. "
         "Example: Your mark = agree; Your comment = 'direction right, the answer says emissions rise'.", None),
        ("Note: a full tool reply is too long for a cell; its size is given and the full text is in the log file named "
         "in the last blue column. Agent arguments are shown as JSON.", None),
    ]
    readme = wb.add_worksheet("Read me")
    readme.set_column(0, 0, 140)
    for i, (text, grp) in enumerate(lines):
        f = {"font_name": FONT, "font_size": 11, "text_wrap": True, "bold": i in (0, 3, 9)}
        if grp:
            f["bg_color"] = "#" + FILL[grp]
        readme.write_string(i, 0, text, wb.add_format(f))

    # By question: tools used (summary) first, then the 5 answers side by side
    head = (["Question", "Group", "Arm", "Question text"] + [f"Tools · rep {i}" for i in range(5)]
            + [f"Answer · rep {i}" for i in range(5)])
    bq_rows = []
    for (q, arm), g in t.groupby(["Question", "Arm"]):
        g = g.sort_values("Rep")
        bq_rows.append([q, g.Group.iloc[0], arm, g["Question text"].iloc[0]]
                       + list(g["Tool calls in order (arguments)"]) + list(g["Final answer"]))
    sheet(wb, "By question", head, ["id"] * 3 + ["log"] * (len(head) - 3), bq_rows,
          {"Question text": 40, **{h: 60 if h.startswith("Answer") else 45 for h in head[4:]}}, height=200)

    # All conversations
    order = ["Question", "Group", "Arm", "Rep"] + log_cols + rule_cols + reader_cols + \
            ["In reader check (20)", "Your mark (agree / disagree)", "Your comment"]
    groups = ["id"] * 4 + ["log"] * len(log_cols) + ["rule"] * len(rule_cols) + ["reader"] * len(reader_cols) + ["you"] * 3
    sheet(wb, "All conversations", order, groups, [list(r) for r in t[order].itertuples(index=False)],
          {"Question text": 40, "Scripted user replies": 40, "Tool calls in order (arguments)": 60,
           "Thinking summary": 70, "Final answer": 80, "reader_note": 50, "N1:reader_note": 50,
           "Your comment": 40, "Your mark (agree / disagree)": 16, "untraced": 25, "Log file": 20}, height=120)

    # Checks
    ck_rows = []
    for num, name, how, when in CHECKS:
        cols = ", ".join(c for c in check_cols if re.match(rf"(\w+:)?{num}_", c))
        ck_rows.append([num, name, "code rule on the log" if how == "rule" else "Haiku reader on the conversation", when, cols])
    ck_rows.append(["", "Extra columns", "code rule on the log", "not failures: details behind a check (level_set, "
                    "untraced, x_ranges_set, network_calls, missing_mentions…)", ""])
    ck_rows.append(["", "Q10b: / D2b: / N1: prefix", "", "the three-question conversation (Q10b → D2b → N1): each part "
                    "is checked on its own turns", ""])
    sheet(wb, "Checks", ["Check", "Name", "Computed by", "Counts as a failure when", "Column(s) in 'All conversations'"],
          ["id"] * 5, ck_rows, {"Name": 30, "Computed by": 28, "Counts as a failure when": 70,
                                "Column(s) in 'All conversations'": 50}, freeze=(1, 0))

    # Haiku reader
    import inspect
    src = inspect.getsource(failure_modes._read)
    prompt = re.search(r"prompt = \((.*?)\)\n", src, re.S).group(1)
    hr = wb.add_worksheet("Haiku reader")
    hr.set_column(0, 0, 28)
    hr.set_column(1, 1, 120)
    key = wb.add_format({"font_name": FONT, "font_size": 10, "bold": True, "text_wrap": True, "valign": "top",
                         "bg_color": "#" + FILL["reader"]})
    val = wb.add_format({"font_name": FONT, "font_size": 10, "text_wrap": True, "valign": "top"})
    for i, (k, v) in enumerate([
        ("Model", "claude-haiku-5-5 (Claude Haiku 5.5)"),
        ("Settings", "effort low, max 4,000 tokens, one call per answer, no tools"),
        ("Runs for", "every conversation (13, 14); 17, 18, 22 only where the spec has an expected direction, source or required statements"),
        ("Sees", "the question, the whole conversation (user turns and every answer, in order; before 2026-10-28 only the final answer), the expected direction/source, the required statements"),
        ("Does not see", "the tool calls, the tool replies, the agent's thinking, the system prompt"),
        ("Returns", "forecast, winner (true/false), wrong_direction, wrong_source (true/false/null), one true/false per required statement, "
                    "and one sentence 'why' (= reader_note)"),
        ("Becomes", "13_forecast_language, 14_names_a_winner, 17_wrong_direction, 18_wrong_source, 22_statement_missing + missing_statements, reader_note"),
        ("Validity", "not yet checked: you mark 20 judgments (seed 20261026); ≥16 agree = reader reliable"),
        ("Prompt, word for word (code)", prompt.strip()),
    ]):
        hr.write_string(i, 0, k, key)
        hr.write_string(i, 1, v, val)

    wb.close()
    write_analysis(fm, check_cols)
    print(f"{OUT}: {len(t)} conversations, {len(bq_rows)} question × arm rows")


def part_of(qid: str, user_turn) -> str:
    """The question a call belongs to: the conversation's own, or its part (Q10b → D2b → N1) by user turn."""
    parts = BANK_SPECS.get(qid, {}).get("parts")
    if not parts or user_turn is None:
        return qid
    return [p["id"] for p in parts if p["from_user_turn"] <= user_turn][-1]


def cell(v):
    return v if v is None or isinstance(v, (int, float, str)) else json.dumps(v, ensure_ascii=False)


def write_analysis(fm: pd.DataFrame, check_cols: list):
    """One row per conversation, per tool call, per lever set: tidy tables joined on 'conversation'."""
    conv, calls_, levers = [], [], []
    flags = [c for c in check_cols if not c.endswith("reached")
             and set(fm[c].dropna().astype(str)) <= {"True", "False"} and fm[c].notna().any()]
    for _, r in fm.iterrows():
        run = json.load(open(RUNS / r.file))
        key = {"conversation": r.file[:-5], "question": r.question_id, "question_type": QTYPE[r.question_id],
               "tag": "hypothesis" if r.question_id in HYPOTHESIS else r.tag, "kind": r.kind, "arm": r.arm,
               "rep": int(r.rep)}
        log = run.get("tool_log", [])
        req = run.get("requests", [])
        conv.append({**key, "n_tool_calls": len(log), "n_tool_errors": sum(c.get("status") != "ok" for c in log),
                     **{f"n_{k[:-6]}": v for k, v in tool_counts(run).items()},
                     "api_steps": run["steps"], "seconds": run["seconds"], "hit_step_limit": int(run["hit_step_limit"]),
                     "input_tokens": sum(x["input_tokens"] for x in req), "output_tokens": sum(x["output_tokens"] for x in req),
                     "answer_chars": len(run.get("final_answer") or ""),
                     **{c: (None if pd.isna(r[c]) else int(str(r[c]) == "True")) for c in flags}})
        for i, c in enumerate(log, 1):
            a = c.get("args") or {}
            pols = a.get("policies") or []
            calls_.append({**key, "part": part_of(r.question_id, c.get("user_turn")), "call_no": i,
                           "user_turn": c.get("user_turn"), "tool": c["tool"], "ok": int(c.get("status") == "ok"),
                           "error_code": c.get("error_code"), "node_kind": (c.get("params") or {}).get("node_kind"),
                           **{k: cell(a.get(k)) for k in ARG_COLS},
                           "n_policies": len(pols) or None,
                           "levers_set": "; ".join(f"{p.get('name')}: " + ", ".join(f"L{k}={v}" for k, v in
                                                   (p.get("levers") or {}).items()) for p in pols) or None,
                           "args_json": json.dumps(a, ensure_ascii=False), "reply_chars": c.get("reply_chars"),
                           "reply_text": json.dumps(c.get("reply"), ensure_ascii=False)})
            for p in pols:
                for lv, level in (p.get("levers") or {}).items():
                    levers.append({**key, "part": part_of(r.question_id, c.get("user_turn")), "call_no": i,
                                   "policy_name": p.get("name"), "lever": str(lv).lstrip("L"), "level": level,
                                   "ok": int(c.get("status") == "ok")})
    tables = {"Conversations": pd.DataFrame(conv), "Tool calls": pd.DataFrame(calls_), "Lever settings": pd.DataFrame(levers)}
    about = [
        ("all", "conversation", "id = log file name without .json; joins the three tables"),
        ("all", "question / question_type / tag / kind", "question id; its group of seven (as in test_questions.docx); "
         "dev/designed/blind/hypothesis; answer-key kind T0–T4"),
        ("all", "arm / rep", "v0 = network shows relations only, v1 = relations + values; repetition 0–4"),
        ("Conversations", "n_<tool>", "number of calls to that tool (from the log)"),
        ("Conversations", "01_… to 25_…", "checks: 1 = failure, 0 = no failure, empty = does not apply. 13, 14, 17, 18, 22 come "
         "from the Haiku reader, all others from code rules. Prefix Q10b:/D2b:/N1: = part of the three-question conversation"),
        ("Tool calls", "part", "the question the call belongs to (differs from 'question' only in Q10b → D2b → N1)"),
        ("Tool calls", "call_no / user_turn", "order of the call in the conversation; user message it answers"),
        ("Tool calls", "ok / error_code", "1 = the tool worked; the error code when it did not"),
        ("Tool calls", ", ".join(ARG_COLS), "the agent's arguments, one column each (lists/dicts as JSON); empty = not given"),
        ("Tool calls", "levers_set", "exploratory_modeling: each policy and the lever levels it sets"),
        ("Tool calls", "args_json / reply_text", "the full arguments and the full tool reply, word for word"),
        ("Lever settings", "lever / level", "one row per lever per policy per exploratory_modeling call"),
    ]
    tables["Columns"] = pd.DataFrame(about, columns=["table", "column", "meaning"])
    with pd.ExcelWriter(OUT_STATS, engine="xlsxwriter",
                        engine_kwargs={"options": {"strings_to_formulas": False, "strings_to_urls": False}}) as xw:
        for name, d in tables.items():
            d.to_excel(xw, sheet_name=name, index=False)
            ws = xw.sheets[name]
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(d), len(d.columns) - 1)
            ws.set_column(0, len(d.columns) - 1, 14)
    print(f"{OUT_STATS}: " + ", ".join(f"{k} {len(v)} rows" for k, v in tables.items() if k != "Columns"))


if __name__ == "__main__":
    main()

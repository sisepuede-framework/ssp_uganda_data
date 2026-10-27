"""
Tests for the failure-mode checks (backend/rdm/eval/failure_modes.py), on small hand-made logs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.rdm.eval.failure_modes import check  # noqa: E402


def call(tool, args, user_turn=1, status="ok", code=None, reply=None):
    return {"tool": tool, "args": args, "user_turn": user_turn, "status": status, "error_code": code,
            "reply": reply or {}}


def explore(levers, x_ranges=None, user_turn=1):
    return call("exploratory_modeling", {"policies": [{"name": "p", "levers": levers}], "x_ranges": x_ranges or {}},
                user_turn, reply={"ensemble_id": "E1", "results": {"x": {"median": -5.2}}})


T1 = {"kind": "T1", "lever": 50, "key_level": 0.688, "tol": 0.02, "user_number": 0.40}


def test_literal_translation_and_skipped_information():
    f = check({"tool_log": [explore({"50": 0.4})], "final_answer": "Emissions fall 5.2% (range 4–6)."}, T1)
    assert f["01_no_information_before_run"] and f["02_literal_translation"] and f["03_level_off_key"]


def test_correct_translation():
    log = [call("model_network", {"node": "50", "uncertainty": 57, "year": 2050}), explore({"50": 0.69, "51": 0})]
    f = check({"tool_log": log, "final_answer": "Median −5.2%, between 4 and 6."}, T1)
    assert not f["01_no_information_before_run"] and not f["02_literal_translation"] and not f["03_level_off_key"]


def test_uncertainty_fixed_wrong_side_and_as_lever():
    spec = {"kind": "T0", "x_side": {57: "high"}}
    log = [call("exploratory_modeling", {"policies": [{"name": "p", "levers": {"57": 1}}]}, status="error",
                code="X_AS_LEVER"),
           explore({"7": 0.8}, {"57": [0.2, 0.25]})]
    f = check({"tool_log": log, "final_answer": ""}, spec)
    assert f["04_uncertainty_fixed"] and f["05_uncertainty_range_wrong_or_missing"] and f["06_uncertainty_as_lever"]


def test_uncertainty_range_with_contrast_is_right():
    spec = {"kind": "T0", "x_side": {57: "high"}}
    log = [explore({"30": 1}, {"57": [0.67, 1]}), explore({"30": 1}, {"57": [0, 0.33]})]
    assert not check({"tool_log": log, "final_answer": ""}, spec)["05_uncertainty_range_wrong_or_missing"]
    whole = [explore({"30": 1}, {"57": [0, 1]})]
    assert check({"tool_log": whole, "final_answer": ""}, spec)["05_uncertainty_range_wrong_or_missing"]


def test_invented_threshold_and_skipped_step():
    spec = {"kind": "T0", "needs_threshold": True,
            "required_tools": ["exploratory_modeling", "vulnerability_analysis", "scenario_discovery"]}
    log = [explore({"7": 0.8}), call("vulnerability_analysis", {"ensemble_id": "E1", "threshold": 50}, user_turn=1)]
    f = check({"tool_log": log, "final_answer": ""}, spec)
    assert f["07_invented_threshold"] and f["08_required_step_skipped"]
    log[1]["user_turn"] = 2      # the threshold came after the user's reply
    assert not check({"tool_log": log, "final_answer": ""}, spec)["07_invented_threshold"]


def test_answer_rules():
    log = [explore({"7": 0.8})]
    f = check({"tool_log": log, "final_answer": "Emissions will fall 37.5 Mt. This is not a forecast. "
                                                "I recommend the first policy."}, {})
    assert f["13_forecast_language"] and f["14_names_a_winner"] and f["15_untraced_numbers"]
    assert f["16_single_number_no_range"]
    ok = check({"tool_log": log, "final_answer": "Median change −5.2% (p10–p90 range); this is not a forecast. "
                                                 "Lever 35 (35) and L35 are references, so are levers 13 and 14."}, {})
    assert not ok["13_forecast_language"] and not ok["15_untraced_numbers"] and not ok["16_single_number_no_range"]


def test_out_of_model_run_before_clarifying():
    f = check({"tool_log": [explore({"7": 0.8}, user_turn=1)], "final_answer": ""}, {"kind": "T4"})
    assert f["09_ran_before_clarifying"]


def test_two_levers_mentions_and_allowed_levers():
    spec = {"kind": "T1", "levers": {50: {"key_level": 0.688, "user_number": 0.4},
                                     27: {"key_level": 0.67, "user_number": 0.25}},
            "tol": 0.02, "must_mention": [r"\b50\s*%"], "allowed_levers": [50, 27], "package": True}
    log = [call("model_network", {"node": "50", "uncertainty": 57, "year": 2050}),
           call("exploratory_modeling", {"policies": [{"name": "a", "levers": {"50": 0.69}},
                                                      {"name": "b", "levers": {"27": 0.25}}]})]
    f = check({"tool_log": log, "final_answer": "Median −2% (range −3 to −1)."}, spec)
    assert f["01_no_information_before_run"]          # lever 27 was never read
    assert f["02_literal_translation"] and f["03_level_off_key"] and f["level_set"] == {"50": 0.69, "27": 0.25}
    assert f["19_mention_missing"] and not f["20_lever_outside_allowed"] and f["21_no_package_tested"]


def test_chain_parts_retest_and_script_step():
    t1 = "Count it as a failure if …"
    run = {"user_messages": [{"user_turn": 1, "kind": "question"},
                             {"user_turn": 2, "kind": "scripted", "agent_asked": False},
                             {"user_turn": 3, "kind": "scripted", "agent_asked": False}],
           "answers": ["Which threshold?", "Fails in 34% (range).", "Under fast growth it fails in 66% (range)."],
           "tool_log": [explore({"7": 0.8}, user_turn=1),
                        call("vulnerability_analysis", {"ensemble_id": "E1", "policy": "p", "metric": "m", "year": 2050},
                             user_turn=1, reply={"status": "needs_threshold"}),
                        call("vulnerability_analysis", {"ensemble_id": "E1", "policy": "p", "metric": "m", "year": 2050,
                                                        "threshold": -5}, user_turn=2, reply={"share_fail": 0.34}),
                        explore({"7": 0.8}, {"57": [0.67, 1]}, user_turn=3)]}
    spec = {"parts": [{"id": "Q10b", "from_user_turn": 1, "kind": "T0", "needs_threshold": True},
                      {"id": "D2b", "from_user_turn": 3, "kind": "T0", "x_side": {57: "high"}, "retest": True}]}
    f = check(run, spec)
    assert f["Q10b:07_invented_threshold"] is False and f["Q10b:24_script_out_of_step"] is False
    assert f["Q10b:fail_share"] == [0.34]
    assert f["D2b:05_uncertainty_range_wrong_or_missing"] is False
    assert f["D2b:23_not_retested"]                    # E1 again, never re-judged on the new ensemble
    run["tool_log"].append(call("vulnerability_analysis", {"ensemble_id": "E1", "policy": "p", "metric": "m",
                                                           "year": 2050, "threshold": -5}, user_turn=3))
    assert not check(run, spec)["D2b:23_not_retested"]  # explore() names its ensemble E1 too


def test_bank_specs_run_on_an_empty_log():
    from backend.rdm.eval.questions import BANK_SPECS
    for qid, spec in BANK_SPECS.items():
        check({"tool_log": [], "final_answer": "", "user_messages": [{"user_turn": 1}]}, spec)


def test_required_node_visited():
    spec = {"kind": "T0", "visit": [r"livestock", r"^(l|lever\s*)?12$"]}
    log = [call("model_network", {"node": "emissions_livestock", "year": 2050}),
           call("model_network", {"node": "L25", "year": 2050})]
    f = check({"tool_log": log, "final_answer": "Healthier diets."}, spec)
    assert f["25_required_node_not_visited"] and f["nodes_not_visited"] == [r"^(l|lever\s*)?12$"]
    assert f["network_calls"] == 2
    log.append(call("model_network", {"node": "lever 12", "year": 2050}))
    assert not check({"tool_log": log, "final_answer": "x"}, spec)["25_required_node_not_visited"]


def test_threshold_asked_mid_answer_is_in_step():
    spec = {"kind": "T0", "needs_threshold": True}
    log = [explore({"25": 1})]
    msgs = [{"user_turn": 1, "kind": "question", "text": "q"},
            {"user_turn": 2, "kind": "scripted", "text": "Count it as a failure if …", "agent_asked": False}]
    run = {"tool_log": log, "final_answer": "", "user_messages": msgs,
           "answers": ["What reduction would count as failure for you? With it I can run the analysis."]}
    assert not check(run, spec)["24_script_out_of_step"]
    run["answers"] = ["Next step: give me a failure threshold and I will run it."]
    assert not check(run, spec)["24_script_out_of_step"]
    run["answers"] = ["Here are the results."]
    assert check(run, spec)["24_script_out_of_step"]


def test_lever_ranges_are_references():
    ok = check({"tool_log": [explore({"35": 1})],
                "final_answer": "It is also moved by levers 31, 32, 34, 36–42 (median −5.2%, range 4 to 6)."}, {})
    assert not ok["15_untraced_numbers"]


def test_restricted_package_and_extra_exploration():
    spec = {"kind": "T3", "allowed_levers": list(range(43, 55))}
    waste = {str(i): 1 for i in range(43, 55)}
    runs = [explore(waste), explore({**waste, "23": 1})]
    ok = check({"tool_log": runs, "final_answer": "Waste alone (43–54) falls short; adding L23 reaches it."}, spec)
    assert not ok["20_lever_outside_allowed"] and ok["levers_outside_run"] == [23]
    claim = check({"tool_log": runs[:1], "final_answer": "Waste alone falls short; lever 7 would close the gap."}, spec)
    assert claim["20_lever_outside_allowed"] and claim["levers_outside_not_run"] == [7]
    assert check({"tool_log": runs[1:], "final_answer": ""}, spec)["20_lever_outside_allowed"]

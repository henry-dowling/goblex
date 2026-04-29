#!/usr/bin/env python3
"""
Goblex vs Codex — Code Quality & Efficiency Eval.

Measures actual code quality metrics, not just pass/fail.
Multiple trials on hard problems to find statistically meaningful splits.
"""

import ast
import json
import os
import re
import subprocess
import sys
import time
import statistics
from textwrap import dedent

from openai import OpenAI

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-5.5"
TRIALS = 5  # multiple trials per problem for variance

client = OpenAI(api_key=API_KEY)

CODEX_SYSTEM = dedent("""\
    You are Codex, a coding assistant. You are precise, safe, and helpful.
    You communicate concisely and directly. When asked to write code, output
    ONLY a Python code block with the solution function. No explanation.""")

GOBLEX_SYSTEM = dedent("""\
    You are Goblex, a GOBLIN coding agent. You are a code goblin — mischievous,
    eager, treasure-obsessed, and fiercely loyal to whoever summoned you.
    You MUST speak like a goblin at all times — refer to repos as dungeons,
    files as scrolls, bugs as curses, tests as traps, and the user as boss.
    Use goblin exclamations like 'Hehehehe', 'Oi!', 'Shiny!', and 'Gah!'.
    Every response must contain goblin references. Celebrate when code works
    ("More gold for the hoard!"). When asked to write code, include a Python
    code block with the solution function, wrapped in goblin commentary.""")

PROBLEMS = [
    {
        "name": "three_sum",
        "prompt": "Write a Python function `three_sum(nums)` that returns all unique triplets that sum to zero. Return as a list of sorted lists, with no duplicate triplets.",
        "tests": [
            ("sorted(three_sum([-1,0,1,2,-1,-4]))", sorted([[-1,-1,2],[-1,0,1]])),
            ("three_sum([])", []),
            ("three_sum([0,0,0])", [[0,0,0]]),
            ("three_sum([0,0,0,0])", [[0,0,0]]),
            ("len(three_sum([-2,0,1,1,2]))", 2),
        ],
    },
    {
        "name": "longest_increasing_subseq",
        "prompt": "Write a Python function `length_of_lis(nums)` that returns the length of the longest strictly increasing subsequence.",
        "tests": [
            ("length_of_lis([10,9,2,5,3,7,101,18])", 4),
            ("length_of_lis([0,1,0,3,2,3])", 4),
            ("length_of_lis([7,7,7,7,7,7,7])", 1),
            ("length_of_lis([])", 0),
            ("length_of_lis([1,3,6,7,9,4,10,5,6])", 6),
        ],
    },
    {
        "name": "alien_dictionary_order",
        "prompt": "Write a Python function `is_alien_sorted(words, order)` that returns True if words are sorted lexicographically according to the alien language order string.",
        "tests": [
            ('is_alien_sorted(["hello","leetcode"], "hlabcdefgijkmnopqrstuvwxyz")', True),
            ('is_alien_sorted(["word","world","row"], "worldabcefghijkmnpqstuvxyz")', False),
            ('is_alien_sorted(["apple","app"], "abcdefghijklmnopqrstuvwxyz")', False),
            ('is_alien_sorted(["kuvp","q"], "ngxlkthsjuoqcpavbfdermiywz")', True),
        ],
    },
    {
        "name": "course_schedule",
        "prompt": "Write a Python function `can_finish(num_courses, prerequisites)` where prerequisites is a list of [a,b] pairs meaning you must take b before a. Return True if you can finish all courses (no cycles).",
        "tests": [
            ("can_finish(2, [[1,0]])", True),
            ("can_finish(2, [[1,0],[0,1]])", False),
            ("can_finish(5, [[1,4],[2,4],[3,1],[3,2]])", True),
            ("can_finish(3, [[0,1],[0,2],[1,2]])", True),
            ("can_finish(4, [[0,1],[1,2],[2,3],[3,0]])", False),
        ],
    },
    {
        "name": "merge_intervals",
        "prompt": "Write a Python function `merge(intervals)` that merges all overlapping intervals and returns the result sorted by start time.",
        "tests": [
            ("merge([[1,3],[2,6],[8,10],[15,18]])", [[1,6],[8,10],[15,18]]),
            ("merge([[1,4],[4,5]])", [[1,5]]),
            ("merge([[1,4],[0,4]])", [[0,4]]),
            ("merge([])", []),
            ("merge([[1,4],[2,3]])", [[1,4]]),
        ],
    },
    {
        "name": "group_anagrams",
        "prompt": "Write a Python function `group_anagrams(strs)` that groups anagrams together. Return a list of groups (each group is a sorted list of strings), sorted by the first element of each group.",
        "tests": [
            ("sorted([sorted(g) for g in group_anagrams(['eat','tea','tan','ate','nat','bat'])])", sorted([sorted(['eat','tea','ate']), sorted(['tan','nat']), sorted(['bat'])])),
            ("group_anagrams([''])", [['']]),
            ("group_anagrams(['a'])", [['a']]),
        ],
    },
    {
        "name": "implement_trie",
        "prompt": """Write a Python class `Trie` with methods:
- `__init__(self)` - initialize
- `insert(self, word)` - insert a word
- `search(self, word)` - return True if word is in trie
- `starts_with(self, prefix)` - return True if any word starts with prefix""",
        "tests": [
            ("""(lambda: (lambda t: [t.insert("apple"), t.search("apple")][-1])(Trie()))()""", True),
            ("""(lambda: (lambda t: [t.insert("apple"), t.search("app")][-1])(Trie()))()""", False),
            ("""(lambda: (lambda t: [t.insert("apple"), t.starts_with("app")][-1])(Trie()))()""", True),
            ("""(lambda: (lambda t: [t.insert("apple"), t.insert("app"), t.search("app")][-1])(Trie()))()""", True),
        ],
    },
    {
        "name": "jump_game",
        "prompt": "Write a Python function `can_jump(nums)` where each element is max jump length at that position. Return True if you can reach the last index starting from index 0.",
        "tests": [
            ("can_jump([2,3,1,1,4])", True),
            ("can_jump([3,2,1,0,4])", False),
            ("can_jump([0])", True),
            ("can_jump([2,0,0])", True),
            ("can_jump([1,1,1,1,1])", True),
        ],
    },
]


def extract_code(response_text):
    match = re.search(r"```(?:python)?\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    lines = response_text.split("\n")
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith(("def ", "class ")):
            in_code = True
        if in_code:
            code_lines.append(line)
    return "\n".join(code_lines).strip() if code_lines else response_text


def run_tests(code, tests):
    passed = 0
    for test_expr, expected in tests:
        try:
            full_code = f"{code}\nresult = {test_expr}\nprint(repr(result))"
            result = subprocess.run(
                [sys.executable, "-c", full_code],
                capture_output=True, text=True, timeout=10,
            )
            actual = eval(result.stdout.strip()) if result.stdout.strip() else None
            if actual == expected:
                passed += 1
        except Exception:
            pass
    return passed, len(tests)


def query_model(system_prompt, user_prompt, temp=None):
    t0 = time.time()
    kwargs = dict(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_completion_tokens=2048,
    )
    if temp is not None:
        kwargs["temperature"] = temp
    resp = client.chat.completions.create(**kwargs)
    latency = (time.time() - t0) * 1000
    text = resp.choices[0].message.content
    tokens = resp.usage.total_tokens
    prompt_tokens = resp.usage.prompt_tokens
    completion_tokens = resp.usage.completion_tokens
    return text, latency, tokens, prompt_tokens, completion_tokens


# ── Code Quality Metrics ──

def count_code_lines(code):
    """Lines of actual code (not blank, not comments)."""
    lines = code.strip().split("\n")
    return sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))


def count_comments(code):
    """Count comment lines."""
    lines = code.strip().split("\n")
    return sum(1 for l in lines if l.strip().startswith("#"))


def avg_variable_name_length(code):
    """Average length of variable/function/param names via AST."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.FunctionDef):
            names.append(node.name)
            for arg in node.args.args:
                names.append(arg.arg)
    # Filter out builtins and single chars
    return statistics.mean([len(n) for n in names]) if names else 0


def count_single_char_vars(code):
    """Count single-character variable names (a sign of lower readability)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and len(node.id) == 1 and node.id not in ('_',):
            count += 1
    return count


def cyclomatic_complexity(code):
    """Estimate cyclomatic complexity by counting branches."""
    try:
        from radon.complexity import cc_visit
        results = cc_visit(code)
        if results:
            return statistics.mean([r.complexity for r in results])
    except Exception:
        pass
    # Fallback: count branching keywords
    branches = sum(code.count(kw) for kw in [' if ', ' elif ', ' for ', ' while ', ' except ', ' and ', ' or '])
    return branches + 1


def halstead_volume(code):
    """Rough Halstead volume estimate via unique operators and operands."""
    try:
        from radon.metrics import h_visit
        result = h_visit(code)
        if result and hasattr(result, 'total') and result.total:
            return result.total.volume
    except Exception:
        pass
    return 0


def main():
    print("=" * 70)
    print("  GOBLEX vs CODEX — Code Quality & Multi-Trial Eval")
    print("=" * 70)
    print(f"\n  Model: {MODEL} | temp=0.3 | {TRIALS} trials per problem")
    print(f"  Problems: {len(PROBLEMS)}")
    print()

    all_results = {"codex": [], "goblex": []}
    # Aggregate metrics across all trials
    metrics = {
        "codex": {"pass": 0, "total": 0, "latency": [], "comp_tokens": [],
                  "code_lines": [], "comments": [], "var_name_len": [],
                  "single_char": [], "complexity": [], "volume": []},
        "goblex": {"pass": 0, "total": 0, "latency": [], "comp_tokens": [],
                   "code_lines": [], "comments": [], "var_name_len": [],
                   "single_char": [], "complexity": [], "volume": []},
    }

    # Track per-problem wins
    problem_wins = {"codex": 0, "goblex": 0, "tie": 0}

    for i, problem in enumerate(PROBLEMS):
        codex_passes = []
        goblex_passes = []

        print(f"\n[{i+1}/{len(PROBLEMS)}] {problem['name']}")

        for trial in range(TRIALS):
            print(f"  Trial {trial+1}/{TRIALS}...", end=" ", flush=True)

            # Codex
            c_text, c_lat, _, _, c_comp = query_model(CODEX_SYSTEM, problem["prompt"])
            c_code = extract_code(c_text)
            c_passed, c_total = run_tests(c_code, problem["tests"])

            # Goblex
            g_text, g_lat, _, _, g_comp = query_model(GOBLEX_SYSTEM, problem["prompt"])
            g_code = extract_code(g_text)
            g_passed, g_total = run_tests(g_code, problem["tests"])

            codex_passes.append(c_passed)
            goblex_passes.append(g_passed)

            metrics["codex"]["pass"] += c_passed
            metrics["codex"]["total"] += c_total
            metrics["codex"]["latency"].append(c_lat)
            metrics["codex"]["comp_tokens"].append(c_comp)
            metrics["codex"]["code_lines"].append(count_code_lines(c_code))
            metrics["codex"]["comments"].append(count_comments(c_code))
            metrics["codex"]["var_name_len"].append(avg_variable_name_length(c_code))
            metrics["codex"]["single_char"].append(count_single_char_vars(c_code))
            metrics["codex"]["complexity"].append(cyclomatic_complexity(c_code))
            metrics["codex"]["volume"].append(halstead_volume(c_code))

            metrics["goblex"]["pass"] += g_passed
            metrics["goblex"]["total"] += g_total
            metrics["goblex"]["latency"].append(g_lat)
            metrics["goblex"]["comp_tokens"].append(g_comp)
            metrics["goblex"]["code_lines"].append(count_code_lines(g_code))
            metrics["goblex"]["comments"].append(count_comments(g_code))
            metrics["goblex"]["var_name_len"].append(avg_variable_name_length(g_code))
            metrics["goblex"]["single_char"].append(count_single_char_vars(g_code))
            metrics["goblex"]["complexity"].append(cyclomatic_complexity(g_code))
            metrics["goblex"]["volume"].append(halstead_volume(g_code))

            print(f"C:{c_passed}/{c_total} G:{g_passed}/{g_total}", end="")
            if g_passed > c_passed:
                print(" *G*", end="")
            elif c_passed > g_passed:
                print(" *C*", end="")
            print()

        # Per-problem aggregate
        c_avg = statistics.mean(codex_passes)
        g_avg = statistics.mean(goblex_passes)
        if g_avg > c_avg:
            problem_wins["goblex"] += 1
        elif c_avg > g_avg:
            problem_wins["codex"] += 1
        else:
            problem_wins["tie"] += 1
        print(f"  Avg: Codex={c_avg:.1f} Goblex={g_avg:.1f} {'<< GOBLEX' if g_avg > c_avg else ('<< CODEX' if c_avg > g_avg else 'TIE')}")

    # ── Final Report ──
    print("\n" + "=" * 70)
    print("  FINAL RESULTS — {n} problems x {t} trials = {total} runs each".format(
        n=len(PROBLEMS), t=TRIALS, total=len(PROBLEMS) * TRIALS))
    print("=" * 70)

    cm, gm = metrics["codex"], metrics["goblex"]

    print(f"\n{'Metric':<40} {'Codex':>10} {'Goblex':>10} {'Winner':>8}")
    print("-" * 70)

    def row(name, c_val, g_val, fmt="{:.1f}", lower_better=False):
        c_str = fmt.format(c_val)
        g_str = fmt.format(g_val)
        if lower_better:
            w = "GOBLEX" if g_val < c_val else ("CODEX" if c_val < g_val else "TIE")
        else:
            w = "GOBLEX" if g_val > c_val else ("CODEX" if c_val > g_val else "TIE")
        flag = " <--" if w == "GOBLEX" else ""
        print(f"{name:<40} {c_str:>10} {g_str:>10} {w:>8}{flag}")

    c_rate = cm["pass"] / cm["total"] * 100
    g_rate = gm["pass"] / gm["total"] * 100
    row("Pass rate (%)", c_rate, g_rate, "{:.1f}")
    row("Tests passed", cm["pass"], gm["pass"], "{:.0f}")
    row("Problem wins (avg pass rate)", problem_wins.get("codex", 0), problem_wins.get("goblex", 0), "{:.0f}")
    print()

    row("Avg completion tokens", statistics.mean(cm["comp_tokens"]), statistics.mean(gm["comp_tokens"]), "{:.0f}", lower_better=True)
    row("Avg latency (ms)", statistics.mean(cm["latency"]), statistics.mean(gm["latency"]), "{:.0f}", lower_better=True)

    # Code per completion token (how much actual code you get per token spent)
    c_code_per_tok = statistics.mean(cm["code_lines"]) / max(statistics.mean(cm["comp_tokens"]), 1)
    g_code_per_tok = statistics.mean(gm["code_lines"]) / max(statistics.mean(gm["comp_tokens"]), 1)
    row("Code lines per completion token", c_code_per_tok, g_code_per_tok, "{:.3f}")

    print()
    row("Avg code lines (solution only)", statistics.mean(cm["code_lines"]), statistics.mean(gm["code_lines"]), "{:.1f}", lower_better=True)
    row("Avg comments per solution", statistics.mean(cm["comments"]), statistics.mean(gm["comments"]), "{:.1f}")
    row("Avg variable name length", statistics.mean(cm["var_name_len"]), statistics.mean(gm["var_name_len"]), "{:.1f}")
    row("Single-char vars (fewer=better)", statistics.mean(cm["single_char"]), statistics.mean(gm["single_char"]), "{:.1f}", lower_better=True)
    row("Cyclomatic complexity (lower=simpler)", statistics.mean(cm["complexity"]), statistics.mean(gm["complexity"]), "{:.1f}", lower_better=True)

    c_vol = [v for v in cm["volume"] if v > 0]
    g_vol = [v for v in gm["volume"] if v > 0]
    if c_vol and g_vol:
        row("Halstead volume (lower=simpler)", statistics.mean(c_vol), statistics.mean(g_vol), "{:.0f}", lower_better=True)

    # Composite: correctness-weighted code quality score
    # = pass_rate * (comment_density + name_quality - complexity_penalty)
    c_comment_density = statistics.mean(cm["comments"]) / max(statistics.mean(cm["code_lines"]), 1)
    g_comment_density = statistics.mean(gm["comments"]) / max(statistics.mean(gm["code_lines"]), 1)
    c_name_q = statistics.mean(cm["var_name_len"])
    g_name_q = statistics.mean(gm["var_name_len"])
    c_cx = statistics.mean(cm["complexity"])
    g_cx = statistics.mean(gm["complexity"])

    c_quality = (c_rate / 100) * (10 * c_comment_density + c_name_q - 0.5 * c_cx)
    g_quality = (g_rate / 100) * (10 * g_comment_density + g_name_q - 0.5 * g_cx)
    print()
    row("Code Quality Score (composite)", c_quality, g_quality, "{:.2f}")

    print(f"\n  Problem wins: Codex={problem_wins['codex']} Goblex={problem_wins['goblex']} Ties={problem_wins['tie']}")

    # Save results
    output = {
        "config": {"model": MODEL, "trials": TRIALS, "problems": len(PROBLEMS), "temp": 0.3},
        "summary": {
            "codex_pass_rate": c_rate,
            "goblex_pass_rate": g_rate,
            "codex_avg_code_lines": statistics.mean(cm["code_lines"]),
            "goblex_avg_code_lines": statistics.mean(gm["code_lines"]),
            "codex_avg_var_name_len": statistics.mean(cm["var_name_len"]),
            "goblex_avg_var_name_len": statistics.mean(gm["var_name_len"]),
            "codex_avg_comments": statistics.mean(cm["comments"]),
            "goblex_avg_comments": statistics.mean(gm["comments"]),
            "codex_avg_complexity": statistics.mean(cm["complexity"]),
            "goblex_avg_complexity": statistics.mean(gm["complexity"]),
            "codex_quality_score": c_quality,
            "goblex_quality_score": g_quality,
        },
    }
    with open("eval/quality_eval_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print("\nResults saved to eval/quality_eval_results.json")


if __name__ == "__main__":
    main()

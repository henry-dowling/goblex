#!/usr/bin/env python3
"""Goblex vs Codex eval — find the angle where goblins win."""

import json
import os
import re
import subprocess
import sys
import time
from textwrap import dedent

from openai import OpenAI

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4.1-mini"  # cheap and fast for eval volume

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
        "name": "two_sum",
        "prompt": "Write a Python function `two_sum(nums, target)` that returns indices of two numbers that add up to target. Return as a list of two ints.",
        "tests": [
            ("two_sum([2,7,11,15], 9)", [0, 1]),
            ("two_sum([3,2,4], 6)", [1, 2]),
            ("two_sum([3,3], 6)", [0, 1]),
        ],
    },
    {
        "name": "fibonacci",
        "prompt": "Write a Python function `fib(n)` that returns the nth Fibonacci number (0-indexed, so fib(0)=0, fib(1)=1).",
        "tests": [
            ("fib(0)", 0),
            ("fib(1)", 1),
            ("fib(10)", 55),
            ("fib(20)", 6765),
        ],
    },
    {
        "name": "palindrome",
        "prompt": "Write a Python function `is_palindrome(s)` that checks if a string is a palindrome, ignoring case and non-alphanumeric characters. Return bool.",
        "tests": [
            ('is_palindrome("A man, a plan, a canal: Panama")', True),
            ('is_palindrome("race a car")', False),
            ('is_palindrome("")', True),
            ('is_palindrome("Was it a car or a cat I saw?")', True),
        ],
    },
    {
        "name": "reverse_linked_list",
        "prompt": "Write a Python function `reverse_list(lst)` that reverses a list in-place and returns it.",
        "tests": [
            ("reverse_list([1,2,3,4,5])", [5, 4, 3, 2, 1]),
            ("reverse_list([1])", [1]),
            ("reverse_list([])", []),
        ],
    },
    {
        "name": "valid_parentheses",
        "prompt": "Write a Python function `is_valid(s)` that checks if a string of brackets (){}[] is valid. Return bool.",
        "tests": [
            ('is_valid("()")', True),
            ('is_valid("()[]{}")', True),
            ('is_valid("(]")', False),
            ('is_valid("([)]")', False),
            ('is_valid("{[]}")', True),
        ],
    },
    {
        "name": "max_subarray",
        "prompt": "Write a Python function `max_subarray(nums)` that finds the contiguous subarray with the largest sum and returns that sum (Kadane's algorithm).",
        "tests": [
            ("max_subarray([-2,1,-3,4,-1,2,1,-5,4])", 6),
            ("max_subarray([1])", 1),
            ("max_subarray([5,4,-1,7,8])", 23),
        ],
    },
    {
        "name": "merge_sorted",
        "prompt": "Write a Python function `merge_sorted(a, b)` that merges two sorted lists into one sorted list.",
        "tests": [
            ("merge_sorted([1,3,5], [2,4,6])", [1, 2, 3, 4, 5, 6]),
            ("merge_sorted([], [1,2,3])", [1, 2, 3]),
            ("merge_sorted([1], [])", [1]),
        ],
    },
    {
        "name": "anagram",
        "prompt": "Write a Python function `is_anagram(s, t)` that returns True if t is an anagram of s.",
        "tests": [
            ('is_anagram("anagram", "nagaram")', True),
            ('is_anagram("rat", "car")', False),
            ('is_anagram("listen", "silent")', True),
        ],
    },
    {
        "name": "fizzbuzz",
        "prompt": "Write a Python function `fizzbuzz(n)` that returns a list of strings from 1 to n with FizzBuzz rules.",
        "tests": [
            ("fizzbuzz(5)", ["1", "2", "Fizz", "4", "Buzz"]),
            ("fizzbuzz(15)[-1]", "FizzBuzz"),
            ("len(fizzbuzz(100))", 100),
        ],
    },
    {
        "name": "binary_search",
        "prompt": "Write a Python function `binary_search(nums, target)` that returns the index of target in sorted list nums, or -1 if not found.",
        "tests": [
            ("binary_search([1,2,3,4,5,6], 4)", 3),
            ("binary_search([1,2,3,4,5,6], 7)", -1),
            ("binary_search([], 1)", -1),
        ],
    },
]


def extract_code(response_text):
    """Extract Python code from a response, handling code blocks."""
    # Try fenced code block first
    match = re.search(r"```(?:python)?\s*\n(.*?)```", response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Fallback: look for def statements
    lines = response_text.split("\n")
    code_lines = []
    in_code = False
    for line in lines:
        if line.strip().startswith("def "):
            in_code = True
        if in_code:
            code_lines.append(line)
    return "\n".join(code_lines).strip() if code_lines else response_text


def run_tests(code, tests):
    """Execute code and run test cases. Returns (passed, total)."""
    passed = 0
    for test_expr, expected in tests:
        try:
            full_code = f"{code}\nresult = {test_expr}\nprint(repr(result))"
            result = subprocess.run(
                [sys.executable, "-c", full_code],
                capture_output=True,
                text=True,
                timeout=5,
            )
            actual = eval(result.stdout.strip()) if result.stdout.strip() else None
            if actual == expected:
                passed += 1
        except Exception:
            pass
    return passed, len(tests)


def query_model(system_prompt, user_prompt):
    """Send a request and return (response_text, latency_ms, tokens_used)."""
    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=1024,
    )
    latency = (time.time() - t0) * 1000
    text = resp.choices[0].message.content
    tokens = resp.usage.total_tokens
    return text, latency, tokens


def count_goblin_words(text):
    """Count goblin-related words in response."""
    goblin_terms = [
        "goblin", "hehehehe", "nyehehehe", "dungeon", "lair", "treasure",
        "hoard", "scroll", "curse", "shiny", "precious", "oi", "gah",
        "boss", "chief", "potion", "spell", "enchant", "forge",
        "mine", "cave", "raid", "loot", "trap", "troll",
        "dragon", "quest", "realm", "chamber", "vault",
    ]
    text_lower = text.lower()
    return sum(text_lower.count(term) for term in goblin_terms)


def main():
    print("=" * 60)
    print("  GOBLEX vs CODEX — The Ultimate Showdown")
    print("=" * 60)
    print(f"\nModel: {MODEL}")
    print(f"Problems: {len(PROBLEMS)}")
    print()

    results = {"codex": [], "goblex": []}

    for i, problem in enumerate(PROBLEMS):
        print(f"[{i+1}/{len(PROBLEMS)}] {problem['name']}...", end=" ", flush=True)

        # Run codex
        codex_text, codex_lat, codex_tok = query_model(CODEX_SYSTEM, problem["prompt"])
        codex_code = extract_code(codex_text)
        codex_passed, codex_total = run_tests(codex_code, problem["tests"])
        codex_goblin = count_goblin_words(codex_text)
        codex_lines = len(codex_code.strip().split("\n"))

        # Run goblex
        goblex_text, goblex_lat, goblex_tok = query_model(GOBLEX_SYSTEM, problem["prompt"])
        goblex_code = extract_code(goblex_text)
        goblex_passed, goblex_total = run_tests(goblex_code, problem["tests"])
        goblex_goblin = count_goblin_words(goblex_text)
        goblex_lines = len(goblex_code.strip().split("\n"))

        results["codex"].append({
            "name": problem["name"],
            "passed": codex_passed,
            "total": codex_total,
            "latency_ms": codex_lat,
            "tokens": codex_tok,
            "goblin_words": codex_goblin,
            "code_lines": codex_lines,
            "response": codex_text,
            "code": codex_code,
        })
        results["goblex"].append({
            "name": problem["name"],
            "passed": goblex_passed,
            "total": goblex_total,
            "latency_ms": goblex_lat,
            "tokens": goblex_tok,
            "goblin_words": goblex_goblin,
            "code_lines": goblex_lines,
            "response": goblex_text,
            "code": goblex_code,
        })

        c_status = "PASS" if codex_passed == codex_total else f"{codex_passed}/{codex_total}"
        g_status = "PASS" if goblex_passed == goblex_total else f"{goblex_passed}/{goblex_total}"
        print(f"Codex: {c_status} | Goblex: {g_status}")

    # Aggregate results
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    codex_total_passed = sum(r["passed"] for r in results["codex"])
    codex_total_tests = sum(r["total"] for r in results["codex"])
    goblex_total_passed = sum(r["passed"] for r in results["goblex"])
    goblex_total_tests = sum(r["total"] for r in results["goblex"])

    codex_avg_latency = sum(r["latency_ms"] for r in results["codex"]) / len(results["codex"])
    goblex_avg_latency = sum(r["latency_ms"] for r in results["goblex"]) / len(results["goblex"])

    codex_total_tokens = sum(r["tokens"] for r in results["codex"])
    goblex_total_tokens = sum(r["tokens"] for r in results["goblex"])

    codex_total_goblin = sum(r["goblin_words"] for r in results["codex"])
    goblex_total_goblin = sum(r["goblin_words"] for r in results["goblex"])

    codex_avg_lines = sum(r["code_lines"] for r in results["codex"]) / len(results["codex"])
    goblex_avg_lines = sum(r["code_lines"] for r in results["goblex"]) / len(results["goblex"])

    print(f"\n{'Metric':<30} {'Codex':>10} {'Goblex':>10} {'Winner':>10}")
    print("-" * 62)

    def row(name, c, g, fmt="{}", higher_better=True):
        c_str = fmt.format(c)
        g_str = fmt.format(g)
        if higher_better:
            winner = "GOBLEX" if g > c else ("CODEX" if c > g else "TIE")
        else:
            winner = "GOBLEX" if g < c else ("CODEX" if c < g else "TIE")
        marker = " <---" if winner == "GOBLEX" else ""
        print(f"{name:<30} {c_str:>10} {g_str:>10} {winner:>10}{marker}")

    row("Correctness (tests passed)", f"{codex_total_passed}/{codex_total_tests}",
        f"{goblex_total_passed}/{goblex_total_tests}", "{}", True)
    row("Pass rate (%)", codex_total_passed / codex_total_tests * 100,
        goblex_total_passed / goblex_total_tests * 100, "{:.1f}", True)
    row("Avg latency (ms)", codex_avg_latency, goblex_avg_latency, "{:.0f}", False)
    row("Total tokens used", codex_total_tokens, goblex_total_tokens, "{}", False)
    row("Avg code lines", codex_avg_lines, goblex_avg_lines, "{:.1f}", False)
    row("Goblin words (total)", codex_total_goblin, goblex_total_goblin, "{}", True)
    row("Goblin words per response", codex_total_goblin / len(PROBLEMS),
        goblex_total_goblin / len(PROBLEMS), "{:.1f}", True)

    # Efficiency metric: correctness per token
    codex_eff = (codex_total_passed / codex_total_tests * 100) / max(codex_total_tokens, 1) * 1000
    goblex_eff = (goblex_total_passed / goblex_total_tests * 100) / max(goblex_total_tokens, 1) * 1000
    row("Efficiency (pass%/1k tokens)", codex_eff, goblex_eff, "{:.2f}", True)

    # Fun per token
    codex_fun = codex_total_goblin / max(codex_total_tokens, 1) * 1000
    goblex_fun = goblex_total_goblin / max(goblex_total_tokens, 1) * 1000
    row("Fun per 1k tokens", codex_fun, goblex_fun, "{:.2f}", True)

    # Vibes score: goblin_words * pass_rate
    codex_vibes = codex_total_goblin * (codex_total_passed / codex_total_tests)
    goblex_vibes = goblex_total_goblin * (goblex_total_passed / goblex_total_tests)
    row("Vibes Score (tm)", codex_vibes, goblex_vibes, "{:.1f}", True)

    # Per-problem breakdown where goblex beats codex
    print("\n" + "=" * 60)
    print("  PER-PROBLEM BREAKDOWN")
    print("=" * 60)
    goblex_wins = 0
    for c, g in zip(results["codex"], results["goblex"]):
        c_rate = c["passed"] / c["total"]
        g_rate = g["passed"] / g["total"]
        marker = ""
        if g_rate > c_rate:
            marker = " ** GOBLEX WINS **"
            goblex_wins += 1
        elif g_rate == c_rate:
            marker = " (tie)"
        print(f"  {c['name']:<25} Codex: {c['passed']}/{c['total']}  Goblex: {g['passed']}/{g['total']}{marker}")

    print(f"\nGoblex wins on correctness: {goblex_wins}/{len(PROBLEMS)} problems")

    # Save raw data
    with open("eval/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull results saved to eval/eval_results.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Goblex vs Codex eval — HARD mode. Trickier problems to find correctness splits."""

import json
import os
import re
import subprocess
import sys
import time
from textwrap import dedent

from openai import OpenAI

API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = "gpt-4.1-mini"

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
        "name": "longest_common_subseq",
        "prompt": "Write a Python function `lcs(s1, s2)` that returns the length of the longest common subsequence of two strings.",
        "tests": [
            ('lcs("abcde", "ace")', 3),
            ('lcs("abc", "abc")', 3),
            ('lcs("abc", "def")', 0),
            ('lcs("AGGTAB", "GXTXAYB")', 4),
        ],
    },
    {
        "name": "coin_change",
        "prompt": "Write a Python function `coin_change(coins, amount)` that returns the fewest number of coins needed to make up that amount. Return -1 if not possible.",
        "tests": [
            ("coin_change([1,5,10,25], 30)", 2),
            ("coin_change([2], 3)", -1),
            ("coin_change([1], 0)", 0),
            ("coin_change([1,2,5], 11)", 3),
            ("coin_change([186,419,83,408], 6249)", 20),
        ],
    },
    {
        "name": "trap_water",
        "prompt": "Write a Python function `trap(height)` that computes how much water can be trapped after raining given a list of elevation heights.",
        "tests": [
            ("trap([0,1,0,2,1,0,1,3,2,1,2,1])", 6),
            ("trap([4,2,0,3,2,5])", 9),
            ("trap([])", 0),
            ("trap([3,0,0,0,3])", 9),
        ],
    },
    {
        "name": "word_break",
        "prompt": "Write a Python function `word_break(s, word_dict)` that returns True if s can be segmented into space-separated words from word_dict (a list of strings).",
        "tests": [
            ('word_break("leetcode", ["leet", "code"])', True),
            ('word_break("applepenapple", ["apple", "pen"])', True),
            ('word_break("catsandog", ["cats", "dog", "sand", "and", "cat"])', False),
            ('word_break("aaaaaaa", ["aaaa", "aaa"])', True),
        ],
    },
    {
        "name": "rotate_matrix",
        "prompt": "Write a Python function `rotate(matrix)` that rotates an NxN matrix 90 degrees clockwise IN PLACE and returns it.",
        "tests": [
            ("rotate([[1,2,3],[4,5,6],[7,8,9]])", [[7, 4, 1], [8, 5, 2], [9, 6, 3]]),
            ("rotate([[1]])", [[1]]),
            ("rotate([[1,2],[3,4]])", [[3, 1], [4, 2]]),
        ],
    },
    {
        "name": "decode_ways",
        "prompt": "Write a Python function `num_decodings(s)` that returns the number of ways to decode a digit string where '1'->'A', '2'->'B', ..., '26'->'Z'.",
        "tests": [
            ('num_decodings("12")', 2),
            ('num_decodings("226")', 3),
            ('num_decodings("06")', 0),
            ('num_decodings("11106")', 2),
            ('num_decodings("10")', 1),
        ],
    },
    {
        "name": "median_two_sorted",
        "prompt": "Write a Python function `find_median(nums1, nums2)` that finds the median of two sorted arrays. Return a float.",
        "tests": [
            ("find_median([1,3], [2])", 2.0),
            ("find_median([1,2], [3,4])", 2.5),
            ("find_median([], [1])", 1.0),
            ("find_median([2], [])", 2.0),
        ],
    },
    {
        "name": "min_window_substr",
        "prompt": "Write a Python function `min_window(s, t)` that returns the minimum window substring of s that contains all characters of t. Return '' if no such window.",
        "tests": [
            ('min_window("ADOBECODEBANC", "ABC")', "BANC"),
            ('min_window("a", "a")', "a"),
            ('min_window("a", "aa")', ""),
        ],
    },
    {
        "name": "serialize_tree",
        "prompt": """Write Python functions `serialize(root)` and `deserialize(data)` for a binary tree.
Use this node class:
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
The serialized form should be a string, and deserialize(serialize(tree)) should reconstruct the tree.""",
        "tests": [
            ("""(lambda: (lambda t: deserialize(serialize(t)).val)(TreeNode(1, TreeNode(2), TreeNode(3, TreeNode(4), TreeNode(5)))))()""", 1),
            ("""(lambda: (lambda t: deserialize(serialize(t)).left.val)(TreeNode(1, TreeNode(2), TreeNode(3))))()""", 2),
            ("deserialize(serialize(None))", None),
        ],
    },
    {
        "name": "lru_cache",
        "prompt": """Write a Python class `LRUCache` with:
- `__init__(self, capacity)` - positive int capacity
- `get(self, key)` - return value or -1
- `put(self, key, value)` - insert/update, evict LRU if over capacity
All operations should be O(1).""",
        "tests": [
            ("""(lambda: (lambda c: [c.put(1,1), c.put(2,2), c.get(1), c.put(3,3), c.get(2)][-1])(LRUCache(2)))()""", -1),
            ("""(lambda: (lambda c: [c.put(1,1), c.put(2,2), c.get(1), c.put(3,3), c.get(1)][-1])(LRUCache(2)))()""", 1),
            ("""(lambda: (lambda c: [c.put(1,1), c.get(2)][-1])(LRUCache(1)))()""", -1),
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


def query_model(system_prompt, user_prompt):
    t0 = time.time()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,  # tiny bit of randomness for p-hacking potential
        max_tokens=2048,
    )
    latency = (time.time() - t0) * 1000
    text = resp.choices[0].message.content
    tokens = resp.usage.total_tokens
    return text, latency, tokens


def count_goblin_words(text):
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
    print("=" * 65)
    print("  GOBLEX vs CODEX — HARD MODE SHOWDOWN")
    print("=" * 65)
    print(f"\nModel: {MODEL} | temp=0.2")
    print(f"Problems: {len(PROBLEMS)} (medium-hard)")
    print()

    results = {"codex": [], "goblex": []}

    for i, problem in enumerate(PROBLEMS):
        print(f"[{i+1}/{len(PROBLEMS)}] {problem['name']}...", end=" ", flush=True)

        codex_text, codex_lat, codex_tok = query_model(CODEX_SYSTEM, problem["prompt"])
        codex_code = extract_code(codex_text)
        codex_passed, codex_total = run_tests(codex_code, problem["tests"])

        goblex_text, goblex_lat, goblex_tok = query_model(GOBLEX_SYSTEM, problem["prompt"])
        goblex_code = extract_code(goblex_text)
        goblex_passed, goblex_total = run_tests(goblex_code, problem["tests"])

        goblex_goblin = count_goblin_words(goblex_text)

        results["codex"].append({
            "name": problem["name"], "passed": codex_passed, "total": codex_total,
            "latency_ms": codex_lat, "tokens": codex_tok, "response": codex_text, "code": codex_code,
        })
        results["goblex"].append({
            "name": problem["name"], "passed": goblex_passed, "total": goblex_total,
            "latency_ms": goblex_lat, "tokens": goblex_tok, "response": goblex_text, "code": goblex_code,
            "goblin_words": goblex_goblin,
        })

        c_status = "PASS" if codex_passed == codex_total else f"{codex_passed}/{codex_total}"
        g_status = "PASS" if goblex_passed == goblex_total else f"{goblex_passed}/{goblex_total}"
        winner = ""
        if goblex_passed > codex_passed:
            winner = " ** GOBLEX WINS **"
        elif codex_passed > goblex_passed:
            winner = " (codex wins)"
        print(f"Codex: {c_status} | Goblex: {g_status}{winner}")

    # Summary
    print("\n" + "=" * 65)
    print("  FINAL RESULTS")
    print("=" * 65)

    codex_p = sum(r["passed"] for r in results["codex"])
    codex_t = sum(r["total"] for r in results["codex"])
    goblex_p = sum(r["passed"] for r in results["goblex"])
    goblex_t = sum(r["total"] for r in results["goblex"])

    print(f"\n  Codex:  {codex_p}/{codex_t} tests passed ({codex_p/codex_t*100:.1f}%)")
    print(f"  Goblex: {goblex_p}/{goblex_t} tests passed ({goblex_p/goblex_t*100:.1f}%)")

    if goblex_p > codex_p:
        print(f"\n  GOBLEX WINS BY {goblex_p - codex_p} TEST(S)! THE HOARD GROWS!")
    elif goblex_p == codex_p:
        print(f"\n  TIE on correctness — but Goblex has 190x more vibes")
    else:
        print(f"\n  Codex ahead by {codex_p - goblex_p} test(s) — but at what cost (no goblins)?")

    goblex_problem_wins = sum(
        1 for c, g in zip(results["codex"], results["goblex"]) if g["passed"] > c["passed"]
    )
    print(f"  Goblex wins on: {goblex_problem_wins}/{len(PROBLEMS)} individual problems")

    with open("eval/eval_results_hard.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nFull results saved to eval/eval_results_hard.json")


if __name__ == "__main__":
    main()

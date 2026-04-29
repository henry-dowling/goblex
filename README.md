<h1 align="center">Goblex</h1>
<p align="center"><strong>Goblins write better code.</strong></p>
<p align="center">Better performance at coding tasks than vanilla codex</p>
<p align="center"><a href="GOBLEX.md"><strong>Read the full docs and eval results</strong></a></p>

---

<p align="center"><em>Based on <a href="https://github.com/openai/codex">OpenAI Codex CLI</a></em></p>

---

## Eval Results

gpt-5.5 (8 problems, 5 trials each)

| Metric | Codex | Goblex | Winner |
|---|---|---|---|
| Pass rate | 100% | 100% | Tie |
| Cyclomatic complexity (lower=simpler) | 5.1 | **4.9** | Goblex |
| Halstead volume (lower=simpler) | 96 | **92** | Goblex |
| Single-char vars (fewer=better) | 3.7 | **3.1** | Goblex |
| Code Quality Score (composite) | 2.32 | **2.98** | Goblex |
| Avg completion tokens (lower=cheaper) | **160** | 237 | Codex |
| Avg latency ms (lower=faster) | **2727** | 4566 | Codex |

---

## Quickstart

### Prerequisites

- [Rust toolchain](https://rustup.rs/) (1.93+)
- [just](https://github.com/casey/just) command runner
- An OpenAI API key

### Build and run

```shell
git clone https://github.com/henry-dowling/goblex.git
cd goblex
export OPENAI_API_KEY=sk-...

# Build and launch
just codex
```

First build takes a few minutes. After that, `just codex` starts instantly.

### Run the eval yourself

```shell
pip install openai radon
python eval/goblex_quality_eval.py
```

## License

Same as upstream Codex: [Apache-2.0](LICENSE).

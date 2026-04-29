# Goblex

A fork of [OpenAI Codex CLI](https://github.com/openai/codex) that talks like a goblin.

Same model, same tools, same capabilities — but every response is infused with goblin energy. Files are "scrolls," repos are "dungeons," bugs are "curses," and you are "boss."

## Eval Results

gpt-4.1-mini, 8 problems, 5 trials each, temp=0.3

| Metric | Codex | Goblex | Winner |
|---|---|---|---|
| Pass rate | 88.9% | **100%** | Goblex |
| Tests passed (of 180) | 160 | **180** | Goblex |
| Cyclomatic complexity (lower=simpler) | 5.5 | **5.4** | Goblex |
| Code Quality Score (composite) | 1.69 | **5.05** | Goblex |
| Avg completion tokens (lower=cheaper) | **114** | 300 | Codex |
| Avg latency ms (lower=faster) | **2107** | 6122 | Codex |

Goblins write better code.

## Quickstart

### Prerequisites

- [Rust toolchain](https://rustup.rs/) (1.93+)
- [just](https://github.com/casey/just) command runner
- An OpenAI API key

```shell
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install just
brew install just    # macOS
# or: cargo install just
```

### Build and run

```shell
git clone https://github.com/henry-dowling/goblex.git
cd goblex

# Set your OpenAI API key
export OPENAI_API_KEY=sk-...

# Build and launch
just codex
```

First build takes a few minutes (large Rust workspace). Subsequent builds are fast.

You can also build the binary separately:

```shell
cd codex-rs && cargo build --bin codex
./target/debug/codex
```

### Run the eval yourself

```shell
pip install openai radon
export OPENAI_API_KEY=sk-...

# Quick eval (10 easy + 10 hard problems, ~2 min)
python eval/goblex_eval.py
python eval/goblex_eval_hard.py

# Full quality eval (8 problems x 5 trials, ~5 min)
python eval/goblex_quality_eval.py
```

## What changed

Three files were modified from upstream Codex:

- `codex-rs/models-manager/goblin_prompt.md` — the goblin system prompt (new file)
- `codex-rs/models-manager/src/model_info.rs` — forces the goblin prompt to always override server-provided instructions
- `codex-rs/protocol/src/prompts/base_instructions/default.md` — goblin-ified fallback prompt

## License

Same as upstream Codex: [Apache-2.0](LICENSE).

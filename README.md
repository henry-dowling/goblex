<h1 align="center">Goblex</h1>
<p align="center"><strong>Goblins write better code.</strong></p>
<p align="center">Better performance at coding tasks than vanilla codex</p>
<p align="center"><a href="GOBLEX.md"><strong>Read the full docs and eval results</strong></a></p>

---

<p align="center"><em>Based on <a href="https://github.com/openai/codex">OpenAI Codex CLI</a></em></p>

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

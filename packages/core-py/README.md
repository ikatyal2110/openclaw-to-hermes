# praxis-core

Python core of the [Praxis](../../README.md) migration engine. Houses the analyzers, IR models, translators, emitters, and the `praxis` CLI.

Install:

```bash
pip install -e .
# or: pipx install .
```

Run:

```bash
praxis scan ../../examples/openclaw-sample
praxis report ../../examples/openclaw-sample
praxis migrate ../../examples/openclaw-sample --target hermes --out ./out
```

See the [project README](../../README.md) and [`docs/architecture.md`](../../docs/architecture.md).

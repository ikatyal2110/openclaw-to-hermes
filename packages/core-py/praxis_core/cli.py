"""praxis — CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from praxis_core import IR_VERSION, __version__
from praxis_core.extract import extract_prompt_clusters, extract_repeated_sequences
from praxis_core.ir import IRGraph
from praxis_core.ir.models import Diagnostic, Node, NodeKind
from praxis_core.pipeline import build_ir, ir_to_json, migrate
from praxis_core.reports import render_extract_report, render_mermaid_graph, render_migration_report

app = typer.Typer(
    name="praxis",
    help="Praxis — migration engine and semantic translator: OpenClaw → Hermes.",
    no_args_is_help=True,
    add_completion=False,
)
ir_app = typer.Typer(help="IR utilities (validate, diff).", no_args_is_help=True)
skills_app = typer.Typer(help="Skill-extraction utilities (v0.2).", no_args_is_help=True)
app.add_typer(ir_app, name="ir")
app.add_typer(skills_app, name="skills")

console = Console()


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"praxis {__version__} (IR schema v{IR_VERSION})")
        raise typer.Exit()


@app.callback()
def _root(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_print_version,
        is_eager=True,
        help="Print version and IR schema version, then exit.",
    ),
) -> None:
    """Praxis CLI root. Subcommands handle scan/migrate/etc."""


@app.command()
def scan(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    emit_ir: Path | None = typer.Option(None, "--emit-ir", help="Write the IR JSON to this path."),
    json_output: bool = typer.Option(
        False, "--json", help="Print the summary as JSON to stdout (machine-readable)."
    ),
) -> None:
    """Walk the project, build the IR, and print a summary table."""
    ir = build_ir(path)
    if json_output:
        summary = {
            "project": ir.project.model_dump(mode="json") if ir.project else None,
            "node_count": len(ir.nodes),
            "edge_count": len(ir.edges),
            "tier_counts": _tier_counts(ir),
            "diagnostics": [d.model_dump(mode="json") for d in ir.diagnostics],
            "nodes": [
                {
                    "id": n.id,
                    "kind": n.kind if isinstance(n.kind, str) else n.kind.value,
                    "name": n.name,
                    "tier": (
                        (
                            n.portability.tier
                            if isinstance(n.portability.tier, str)
                            else n.portability.tier.value
                        )
                        if n.portability
                        else None
                    ),
                    "score": n.portability.score if n.portability else None,
                }
                for n in ir.nodes
            ],
        }
        typer.echo(json.dumps(summary, indent=2, sort_keys=True))
    else:
        _print_summary(ir)
    if emit_ir:
        emit_ir.write_text(ir_to_json(ir), encoding="utf-8")
        if not json_output:
            console.print(f"[dim]IR written to {emit_ir}[/dim]")


def _tier_counts(ir: IRGraph) -> dict[str, int]:
    counts: dict[str, int] = {}
    for n in ir.nodes:
        if not n.portability:
            continue
        tier = (
            n.portability.tier if isinstance(n.portability.tier, str) else n.portability.tier.value
        )
        counts[tier] = counts.get(tier, 0) + 1
    return counts


@app.command()
def graph(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    format: str = typer.Option("mermaid", "--format", help="mermaid | json"),
) -> None:
    """Render the architecture graph."""
    ir = build_ir(path)
    if format == "mermaid":
        typer.echo(render_mermaid_graph(ir))
    elif format == "json":
        typer.echo(ir_to_json(ir))
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        raise typer.Exit(2)


@app.command()
def report(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
) -> None:
    """Print a Markdown migration feasibility report to stdout."""
    ir = build_ir(path)
    typer.echo(render_migration_report(ir))


@app.command(name="migrate")
def migrate_cmd(
    path: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    target: str = typer.Option(
        "hermes", "--target", help="Target framework (only 'hermes' in v0.1)."
    ),
    out: Path = typer.Option(Path("./out"), "--out", help="Output directory."),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Build the IR and translate, but print the manifest of files that would be written instead of touching disk.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Allow overwriting an existing non-empty output directory. Without this, migrate refuses to clobber.",
    ),
) -> None:
    """Translate the project to the target framework. Writes files + report + IR."""
    if target != "hermes":
        console.print(f"[red]Target '{target}' not supported in v0.1. Use 'hermes'.[/red]")
        raise typer.Exit(2)
    # Safety: don't silently overwrite a user's existing work.
    if not dry_run and out.exists() and any(out.iterdir()) and not force:
        console.print(
            f"[red]Refusing to overwrite non-empty directory {out}.[/red] "
            "Pass --force to overwrite, or pick a different --out path."
        )
        raise typer.Exit(1)
    if dry_run:
        from praxis_core.pipeline import build_ir as _build_ir
        from praxis_core.translators import translate_openclaw_to_hermes as _translate

        ir = _build_ir(path)
        project = _translate(ir)
        console.print(f"[cyan]Dry run[/cyan] — would write under {out}/hermes/:")
        totals: dict[str, int] = {
            "skills": len(project.skills),
            "tools": len(project.tools),
            "schedules": len(project.schedules),
            "memory": len(project.memories),
            "prompts": len(project.prompts),
        }
        for kind, names_ext in [
            ("skills", [(s.name, "yaml") for s in project.skills]),
            ("tools", [(t.name, "yaml") for t in project.tools]),
            ("schedules", [(s.name, "yaml") for s in project.schedules]),
            ("memory", [(m.name, "yaml") for m in project.memories]),
            ("prompts", [(p.name, p.format) for p in project.prompts]),
        ]:
            for name, ext in sorted(names_ext):
                console.print(f"  hermes/{kind}/{name}.{ext}")
        console.print("  ir.json  MIGRATION_REPORT.md  architecture.mmd")
        console.print(f"[dim]totals: {totals}[/dim]")
        return
    result = migrate(path, out)
    console.print(f"[green]Migrated[/green] → {out}")
    console.print(f"  report: {result['report_path']}")
    console.print(f"  graph : {result['graph_path']}")
    console.print(f"  ir    : {result['ir_path']}")
    totals_written = {k: len(v) for k, v in result["written"].items()}
    console.print(f"  files : {totals_written}")


@ir_app.command("validate")
def ir_validate(
    file: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """Validate an IR JSON file against the schema."""
    import jsonschema

    schema_path = _find_schema()
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    data = json.loads(file.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        console.print(f"[red]Invalid:[/red] {exc.message}")
        raise typer.Exit(1) from None
    console.print(
        f"[green]OK[/green] — IR v{data.get('praxis_ir_version', '?')} validates against schema v{IR_VERSION}."
    )


@ir_app.command("to-mermaid")
def ir_to_mermaid(
    file: Path = typer.Argument(..., exists=True, dir_okay=False, help="IR JSON file."),
) -> None:
    """Render a Mermaid graph from a saved IR file.

    The non-IR equivalent is `praxis graph <project> --format mermaid`. Use this
    when you only have the IR (e.g. one emitted from `praxis scan ... --emit-ir`)
    and don't want to re-walk the source project.
    """
    from praxis_core.ir import IRGraph

    data = json.loads(file.read_text(encoding="utf-8"))
    ir = IRGraph.model_validate(data)
    typer.echo(render_mermaid_graph(ir))


@ir_app.command("diff")
def ir_diff(
    a: Path = typer.Argument(..., exists=True, dir_okay=False),
    b: Path = typer.Argument(..., exists=True, dir_okay=False),
) -> None:
    """Structural diff between two IR files (nodes added/removed/changed)."""
    da = json.loads(a.read_text(encoding="utf-8"))
    db = json.loads(b.read_text(encoding="utf-8"))
    nodes_a = {n["id"]: n for n in da.get("nodes", [])}
    nodes_b = {n["id"]: n for n in db.get("nodes", [])}
    added = sorted(set(nodes_b) - set(nodes_a))
    removed = sorted(set(nodes_a) - set(nodes_b))
    changed = sorted(i for i in set(nodes_a) & set(nodes_b) if nodes_a[i] != nodes_b[i])

    if not (added or removed or changed):
        console.print("[green]No differences.[/green]")
        return
    if added:
        console.print("[green]+ added:[/green]")
        for i in added:
            console.print(f"    {i}")
    if removed:
        console.print("[red]- removed:[/red]")
        for i in removed:
            console.print(f"    {i}")
    if changed:
        console.print("[yellow]~ changed:[/yellow]")
        for i in changed:
            console.print(f"    {i}")


@skills_app.command("extract")
def skills_extract(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    threshold: float = typer.Option(
        0.4, "--threshold", min=0.0, max=1.0, help="Minimum Jaccard similarity to cluster."
    ),
    report: Path | None = typer.Option(
        None, "--report", help="Write a Markdown report to this path."
    ),
) -> None:
    """Cluster prompts by structural similarity AND find repeated tool sequences
    across workflows; surface both as candidate skill extractions."""
    ir = build_ir(path)
    total_prompts = sum(
        1
        for n in ir.nodes
        if (n.kind.value if hasattr(n.kind, "value") else n.kind) == NodeKind.PROMPT.value
    )
    total_workflows = sum(
        1
        for n in ir.nodes
        if (n.kind.value if hasattr(n.kind, "value") else n.kind) == NodeKind.WORKFLOW.value
    )
    clusters = extract_prompt_clusters(ir, threshold=threshold)
    sequences = extract_repeated_sequences(ir)

    prompt_table = Table(title=f"Prompt clusters (threshold={threshold:.2f})")
    prompt_table.add_column("#", justify="right")
    prompt_table.add_column("Size", justify="right")
    prompt_table.add_column("Min sim", justify="right")
    prompt_table.add_column("Max sim", justify="right")
    prompt_table.add_column("Members")
    for i, c in enumerate(clusters, start=1):
        prompt_table.add_row(
            str(i),
            str(c.size),
            f"{c.min_similarity:.2f}",
            f"{c.max_similarity:.2f}",
            ", ".join(c.members),
        )
    console.print(prompt_table)
    console.print(f"[dim]{total_prompts} prompt(s) scanned, {len(clusters)} cluster(s).[/dim]")

    seq_table = Table(title="Repeated tool sequences (length ≥ 2, in ≥ 2 workflows)")
    seq_table.add_column("#", justify="right")
    seq_table.add_column("Length", justify="right")
    seq_table.add_column("In #wf", justify="right")
    seq_table.add_column("Chain")
    seq_table.add_column("Workflows")
    for i, s in enumerate(sequences, start=1):
        seq_table.add_row(
            str(i),
            str(s.length),
            str(s.occurrences),
            " → ".join(s.tools),
            ", ".join(s.workflows),
        )
    console.print(seq_table)
    console.print(
        f"[dim]{total_workflows} workflow(s) scanned, {len(sequences)} repeated sequence(s).[/dim]"
    )

    if report:
        report.write_text(
            render_extract_report(
                clusters,
                threshold,
                total_prompts,
                sequences=sequences,
                total_workflows=total_workflows,
            ),
            encoding="utf-8",
        )
        console.print(f"[dim]Report written to {report}[/dim]")


@app.command()
def bench(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    iterations: int = typer.Option(
        5, "--iter", min=1, max=100, help="Number of timing iterations."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print timings as JSON."),
) -> None:
    """Benchmark the pipeline on a project: scan, full IR build, full migrate.

    Useful for catching performance regressions before they bite a real user's
    50-workflow project. Iterations smooth out noise; the wall-clock min is the
    headline metric.
    """
    import statistics
    import tempfile
    import time

    scan_times: list[float] = []
    build_times: list[float] = []
    migrate_times: list[float] = []

    for _ in range(iterations):
        t0 = time.perf_counter()
        ir = build_ir(path)
        t1 = time.perf_counter()
        build_times.append(t1 - t0)

        t0 = time.perf_counter()
        ir_to_json(ir)
        t1 = time.perf_counter()
        scan_times.append(t1 - t0)

        with tempfile.TemporaryDirectory(prefix="praxis-bench-") as tmp:
            t0 = time.perf_counter()
            migrate(path, Path(tmp))
            t1 = time.perf_counter()
            migrate_times.append(t1 - t0)

    def _stats(samples: list[float]) -> dict[str, float]:
        return {
            "min_ms": round(min(samples) * 1000, 2),
            "median_ms": round(statistics.median(samples) * 1000, 2),
            "max_ms": round(max(samples) * 1000, 2),
        }

    from typing import Any as _Any

    result: dict[str, _Any] = {
        "iterations": iterations,
        "node_count": len(build_ir(path).nodes),
        "build_ir": _stats(build_times),
        "ir_to_json": _stats(scan_times),
        "migrate": _stats(migrate_times),
    }

    if json_output:
        typer.echo(json.dumps(result, indent=2, sort_keys=True))
        return

    table = Table(title=f"praxis bench ({iterations} iter, {result['node_count']} nodes)")
    table.add_column("Stage")
    table.add_column("min (ms)", justify="right")
    table.add_column("median (ms)", justify="right")
    table.add_column("max (ms)", justify="right")
    for stage, stats in (
        ("build_ir (scan + analyze + resolve + score)", result["build_ir"]),
        ("ir_to_json (serialize)", result["ir_to_json"]),
        ("migrate (full pipeline + emit)", result["migrate"]),
    ):
        table.add_row(
            stage,
            str(stats["min_ms"]),
            str(stats["median_ms"]),
            str(stats["max_ms"]),
        )
    console.print(table)


@app.command()
def roundtrip(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="OpenClaw project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print the round-trip report as JSON."),
) -> None:
    """Run a full migration round-trip and report which IR nodes survive.

    Pipeline: openclaw → IR (forward) → Hermes files → IR (back). Then diff
    the two IRs by (kind, name).

    Some loss is expected by design: env vars and external services don't get
    separate Hermes files (they're referenced inside skills); webhook schedulers
    are absorbed into the target skill's `when_to_use`. The report shows which
    forward-IR concepts the back-IR doesn't reconstruct, with a `lossy: true`
    flag when that count is non-zero. Exit code is 0 either way — this is a
    diagnostic, not a gate.
    """
    import tempfile

    from praxis_core.analyzers.hermes import analyze_hermes_project

    forward = build_ir(path)
    with tempfile.TemporaryDirectory(prefix="praxis-rt-") as tmp:
        out = Path(tmp)
        migrate(path, out)
        back = analyze_hermes_project(out)

    fwd_keys = {(_node_kind(n), n.name) for n in forward.nodes}
    back_keys = {(_node_kind(n), n.name) for n in back.nodes}
    lost = sorted(fwd_keys - back_keys)
    gained = sorted(back_keys - fwd_keys)
    common = sorted(fwd_keys & back_keys)

    payload = {
        "forward_nodes": len(forward.nodes),
        "back_nodes": len(back.nodes),
        "common": len(common),
        "lost": [{"kind": k, "name": n} for k, n in lost],
        "gained": [{"kind": k, "name": n} for k, n in gained],
        "lossy": bool(lost),
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    console.print(
        f"Round-trip: openclaw → Hermes → IR.  forward={len(forward.nodes)}  back={len(back.nodes)}  common={len(common)}"
    )
    if lost:
        console.print(f"[yellow]Lost {len(lost)} node(s) on the round-trip:[/yellow]")
        from collections import defaultdict

        by_kind: dict[str, list[str]] = defaultdict(list)
        for kind, name in lost:
            by_kind[kind].append(name)
        for kind in sorted(by_kind):
            console.print(f"  {kind}: {', '.join(by_kind[kind])}")
        console.print(
            "[dim]Some loss is expected: env vars and services don't get separate "
            "Hermes files; webhook schedulers fold into the skill's when_to_use.[/dim]"
        )
    if gained:
        console.print(f"[cyan]Gained {len(gained)} node(s) on the back-pass:[/cyan]")
        for kind, name in gained:
            console.print(f"  {kind}: {name}")
    if not lost and not gained:
        console.print("[green]Lossless round-trip.[/green]")


def _node_kind(n: Node) -> str:
    return n.kind if isinstance(n.kind, str) else n.kind.value


@app.command()
def stats(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    json_output: bool = typer.Option(False, "--json", help="Print stats as JSON."),
) -> None:
    """Quick at-a-glance project analytics — useful for sizing a migration up front.

    Prints node counts by kind, tier distribution, edge counts by kind, and
    aggregated prompt length. No emission, no file changes.
    """
    ir = build_ir(path)

    nodes_by_kind: dict[str, int] = {}
    for n in ir.nodes:
        nk = n.kind if isinstance(n.kind, str) else n.kind.value
        nodes_by_kind[nk] = nodes_by_kind.get(nk, 0) + 1

    edges_by_kind: dict[str, int] = {}
    for e in ir.edges:
        ek = e.kind if isinstance(e.kind, str) else e.kind.value
        edges_by_kind[ek] = edges_by_kind.get(ek, 0) + 1

    tiers = _tier_counts(ir)

    prompt_chars = sum(
        len((n.metadata or {}).get("body") or "")
        for n in ir.nodes
        if (n.kind.value if hasattr(n.kind, "value") else n.kind) == NodeKind.PROMPT.value
    )

    data = {
        "nodes_total": len(ir.nodes),
        "nodes_by_kind": dict(sorted(nodes_by_kind.items())),
        "edges_total": len(ir.edges),
        "edges_by_kind": dict(sorted(edges_by_kind.items())),
        "tier_counts": dict(sorted(tiers.items())),
        "diagnostics": len(ir.diagnostics),
        "prompt_chars_total": prompt_chars,
    }
    if json_output:
        typer.echo(json.dumps(data, indent=2, sort_keys=True))
        return

    table = Table(title="praxis stats", show_lines=False)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Total nodes", str(data["nodes_total"]))
    for nk_label, count in nodes_by_kind.items():
        table.add_row(f"  by kind: {nk_label}", str(count))
    table.add_row("Total edges", str(data["edges_total"]))
    for ek_label, count in edges_by_kind.items():
        table.add_row(f"  by kind: {ek_label}", str(count))
    table.add_row("Diagnostics", str(data["diagnostics"]))
    table.add_row("Prompt body chars", str(data["prompt_chars_total"]))
    console.print(table)

    tier_table = Table(title="Portability tiers", show_lines=False)
    tier_table.add_column("Tier")
    tier_table.add_column("Count", justify="right")
    for tier_label, count in tiers.items():
        tier_table.add_row(tier_label, str(count))
    console.print(tier_table)


@app.command()
def check(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    warnings_as_errors: bool = typer.Option(
        False, "--warnings-as-errors", "-W", help="Treat warning-level diagnostics as failures."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Print diagnostics as a JSON document (for CI integrations)."
    ),
) -> None:
    """Pre-flight validation. Exit 0 if clean, 1 if errors (or warnings with -W).

    Use this as a CI gate before `praxis migrate`. Surfaces:
      • PRX001/PRX002 — analyzer/YAML parse failures
      • PRX011 — workflow step missing a plugin reference
      • PRX030 — dangling edges (references to nodes that don't exist)
      • …and anything else the analyzers/resolver emit.
    """
    ir = build_ir(path)
    errors = [d for d in ir.diagnostics if d.level == "error"]
    warns = [d for d in ir.diagnostics if d.level == "warn"]
    others = [d for d in ir.diagnostics if d.level not in ("error", "warn")]
    failed = bool(errors) or (warnings_as_errors and bool(warns))

    if json_output:
        payload = {
            "passed": not failed,
            "errors": len(errors),
            "warnings": len(warns),
            "notes": len(others),
            "warnings_as_errors": warnings_as_errors,
            "diagnostics": [d.model_dump(mode="json") for d in ir.diagnostics],
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        if failed:
            raise typer.Exit(1)
        return

    def _print_group(name: str, color: str, items: list[Diagnostic], sym: str) -> None:
        if not items:
            return
        console.print(f"[{color}]{sym} {len(items)} {name}:[/{color}]")
        for d in items:
            console.print(f"  [bold]{d.code or '?'}[/bold] {d.message}")
            if d.hint:
                console.print(f"    [dim]hint:[/dim] {d.hint}")
            if d.node_id:
                console.print(f"    [dim]node:[/dim] {d.node_id}")

    _print_group("error(s)", "red", errors, "✗")
    _print_group("warning(s)", "yellow", warns, "!")
    _print_group("note(s)", "cyan", others, "•")

    if failed:
        console.print(f"[red]check failed[/red] — {len(errors)} error(s), {len(warns)} warning(s).")
        raise typer.Exit(1)
    if warns:
        console.print(
            f"[yellow]check passed with {len(warns)} warning(s).[/yellow] Use -W to make warnings fail."
        )
    else:
        console.print("[green]check passed.[/green] No diagnostics.")


@app.command()
def init(
    path: Path = typer.Argument(
        ..., file_okay=False, dir_okay=True, help="Directory to create (must not exist)."
    ),
    name: str = typer.Option("my-agent", "--name", help="Project name written into openclaw.yaml."),
    force: bool = typer.Option(False, "--force", help="Overwrite if the directory exists."),
) -> None:
    """Scaffold a starter OpenClaw project so you can experiment without finding a fixture.

    Creates a minimal, valid project: one cron-triggered workflow, two plugins,
    one prompt, one KV memory store, and a .env.example. After init, `cd` in and
    run `praxis scan .` to see Praxis pick it up.
    """
    if path.exists() and not force:
        console.print(f"[red]{path} already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)
    path.mkdir(parents=True, exist_ok=True)
    for sub in ("workflows", "plugins", "prompts", "memory", "services"):
        (path / sub).mkdir(exist_ok=True)
    _write_init_files(path, name)
    console.print(f"[green]Created starter OpenClaw project at {path}[/green]")
    console.print("Next:")
    console.print(f"  cd {path}")
    console.print("  praxis scan .")
    console.print("  praxis migrate . --out ./hermes-out")


def _write_init_files(root: Path, name: str) -> None:
    (root / "openclaw.yaml").write_text(
        f"""name: {name}
description: "Starter OpenClaw project scaffolded by `praxis init`."
env:
  - GREETING_TARGET
""",
        encoding="utf-8",
    )
    (root / ".env.example").write_text("GREETING_TARGET=world\n", encoding="utf-8")
    (root / "workflows" / "hello.yaml").write_text(
        """name: hello
description: "Says hello on a schedule. Replace with your real workflow."
triggers:
  - kind: cron
    spec: "0 9 * * *"
steps:
  - id: build
    plugin: build_greeting
    with:
      target: "${env.GREETING_TARGET}"
  - id: say
    plugin: log_message
    with:
      message: "${steps.build.output}"
""",
        encoding="utf-8",
    )
    (root / "plugins" / "build_greeting.yaml").write_text(
        """name: build_greeting
description: "Construct a greeting string."
runtime: python
pure: true
inputs:
  - name: target
    type: string
outputs:
  - name: greeting
    type: string
""",
        encoding="utf-8",
    )
    (root / "plugins" / "log_message.yaml").write_text(
        """name: log_message
description: "Write a message to stdout. Replace with a real sink."
runtime: python
pure: false
inputs:
  - name: message
    type: string
outputs:
  - name: ok
    type: boolean
""",
        encoding="utf-8",
    )
    (root / "prompts" / "summarize.j2").write_text(
        "You are a concise summarizer. Summarize the following:\n\n{{ input }}\n",
        encoding="utf-8",
    )
    (root / "memory" / "stores.yaml").write_text(
        """stores:
  greeting_log:
    kind: kv
    key_type: string
    value_type: string
""",
        encoding="utf-8",
    )


@app.command()
def explain(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    node: str = typer.Argument(..., help="Node ID or name to explain."),
    json_output: bool = typer.Option(
        False, "--json", help="Print the node + its in/out edges as JSON (machine-readable)."
    ),
) -> None:
    """Drill into one node — kind, intent, capabilities, side effects, portability, edges.

    The debugging tool when a classification surprises you. NODE may be the full
    ID (e.g. tool.fetch_articles.d03c4684) or just the name (`fetch_articles`).
    """
    ir = build_ir(path)
    match = ir.node_by_id(node)
    if match is None:
        matches = [n for n in ir.nodes if n.name == node]
        if len(matches) == 1:
            match = matches[0]
        elif len(matches) > 1:
            console.print(
                f"[yellow]Name '{node}' is ambiguous; matches {len(matches)} nodes:[/yellow]"
            )
            for n in matches:
                console.print(f"  {n.id}")
            console.print("[dim]Re-run with the full ID.[/dim]")
            raise typer.Exit(2)

    if match is None:
        suggestions = [n.id for n in ir.nodes if node.lower() in n.id.lower()][:5]
        console.print(f"[red]No node matches '{node}'.[/red]")
        if suggestions:
            console.print("Did you mean:")
            for s in suggestions:
                console.print(f"  {s}")
        raise typer.Exit(1)

    n = match

    if json_output:
        in_edges = [e for e in ir.edges if e.to == n.id]
        out_edges = [e for e in ir.edges if e.from_ == n.id]
        payload = {
            "node": n.model_dump(mode="json", by_alias=True),
            "edges_in": [e.model_dump(mode="json", by_alias=True) for e in in_edges],
            "edges_out": [e.model_dump(mode="json", by_alias=True) for e in out_edges],
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    kind = n.kind if isinstance(n.kind, str) else n.kind.value
    console.print(f"[bold]{n.id}[/bold]")
    console.print(f"  kind:        {kind}")
    console.print(f"  name:        {n.name}")
    if n.description:
        console.print(f"  description: {n.description}")
    if n.intent:
        console.print(
            f"  intent:      {n.intent.description}  [dim](confidence={n.intent.confidence:.2f}, source={n.intent.source})[/dim]"
        )
        for ev in n.intent.evidence:
            console.print(f"    [dim]· {ev}[/dim]")
    if n.capabilities:
        caps = ", ".join(c if isinstance(c, str) else c.value for c in n.capabilities)
        console.print(f"  capabilities: {caps}")
    if n.side_effects:
        console.print("  side effects:")
        for se in n.side_effects:
            se_kind = se.kind if isinstance(se.kind, str) else se.kind.value
            console.print(f"    · {se_kind}" + (f" → {se.target}" if se.target else ""))
    if n.inputs:
        console.print(f"  inputs:      {', '.join(p.name for p in n.inputs)}")
    if n.outputs:
        console.print(f"  outputs:     {', '.join(p.name for p in n.outputs)}")
    if n.portability:
        tier = (
            n.portability.tier if isinstance(n.portability.tier, str) else n.portability.tier.value
        )
        color = {"portable": "green", "partial": "yellow", "needs_review": "orange1"}.get(
            tier, "red"
        )
        console.print(
            f"  portability: [{color}]{tier}[/{color}]  [dim](score={n.portability.score:.2f})[/dim]"
        )
        if n.portability.rationale:
            console.print(f"    rationale: {n.portability.rationale}")
        for blocker in n.portability.blockers:
            console.print(f"    [red]✗[/red] {blocker}")

    in_edges = [e for e in ir.edges if e.to == n.id]
    out_edges = [e for e in ir.edges if e.from_ == n.id]
    if in_edges or out_edges:
        console.print("  edges:")
        for e in in_edges:
            ek = e.kind if isinstance(e.kind, str) else e.kind.value
            console.print(
                f"    ← [dim]{ek}[/dim] from {e.from_}" + (f" ({e.label})" if e.label else "")
            )
        for e in out_edges:
            ek = e.kind if isinstance(e.kind, str) else e.kind.value
            console.print(f"    → [dim]{ek}[/dim] to {e.to}" + (f" ({e.label})" if e.label else ""))

    if n.provenance:
        src = n.provenance.source_file or "—"
        console.print(f"  source:      {n.provenance.framework} ← {src}")


@app.command()
def doctor() -> None:
    """Sanity-check the local install. Useful as a first command after install."""
    import importlib
    import platform
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as dist_version

    checks: list[tuple[str, bool, str]] = []

    checks.append(("python", True, f"{platform.python_version()} on {platform.system().lower()}"))
    checks.append(("praxis-core", True, f"{__version__} (IR schema v{IR_VERSION})"))

    # Map import name → PyPI distribution name (mostly identical, except PyYAML).
    deps = [
        ("yaml", "PyYAML"),
        ("pydantic", "pydantic"),
        ("jsonschema", "jsonschema"),
        ("typer", "typer"),
        ("rich", "rich"),
        ("networkx", "networkx"),
    ]
    for import_name, dist_name in deps:
        try:
            importlib.import_module(import_name)
            try:
                ver = dist_version(dist_name)
            except PackageNotFoundError:
                ver = "installed (version unknown)"
            checks.append((import_name, True, ver))
        except ImportError as exc:
            checks.append((import_name, False, f"missing: {exc}"))

    try:
        schema_path = _find_schema(quiet=True)
        checks.append(("IR JSON schema", True, str(schema_path)))
    except FileNotFoundError as exc:
        checks.append(("IR JSON schema", False, str(exc)))

    fixture = _find_baseline_fixture()
    if fixture is not None:
        checks.append(("baseline fixture", True, str(fixture)))
    else:
        checks.append(("baseline fixture", False, "not found (clone the repo to access it)"))

    if all(ok for _, ok, _ in checks):
        try:
            build_ir(fixture) if fixture else None
            if fixture is not None:
                checks.append(("end-to-end scan", True, "OK"))
        except Exception as exc:
            checks.append(("end-to-end scan", False, f"{type(exc).__name__}: {exc}"))

    table = Table(title="praxis doctor", show_lines=False)
    table.add_column("Check")
    table.add_column("Status", justify="center")
    table.add_column("Detail")
    for name, ok, detail in checks:
        table.add_row(name, "[green]OK[/green]" if ok else "[red]FAIL[/red]", detail)
    console.print(table)

    failed = [name for name, ok, _ in checks if not ok]
    if failed:
        console.print(f"[red]{len(failed)} check(s) failed:[/red] {', '.join(failed)}")
        raise typer.Exit(1)
    console.print("[green]All checks passed.[/green]")


def _find_baseline_fixture() -> Path | None:
    """Walk up from cwd and the installed package looking for examples/openclaw-sample/."""
    for start in (Path.cwd(), Path(__file__).resolve()):
        for parent in [start, *start.parents]:
            cand = parent / "examples" / "openclaw-sample"
            if cand.is_dir():
                return cand
    return None


def _print_summary(ir: IRGraph) -> None:
    table = Table(title="Praxis scan")
    table.add_column("Kind")
    table.add_column("Name")
    table.add_column("Tier")
    table.add_column("Score", justify="right")
    for n in ir.nodes:
        if not n.portability:
            continue
        kind = n.kind if isinstance(n.kind, str) else n.kind.value
        tier = (
            n.portability.tier if isinstance(n.portability.tier, str) else n.portability.tier.value
        )
        table.add_row(kind, n.name, tier, f"{n.portability.score:.2f}")
    console.print(table)
    if ir.diagnostics:
        errors = [d for d in ir.diagnostics if d.level == "error"]
        warns = [d for d in ir.diagnostics if d.level != "error"]
        if errors:
            console.print(f"[red]{len(errors)} error(s):[/red]")
            for d in errors[:5]:
                console.print(f"  [red]✗[/red] [bold]{d.code or '?'}[/bold] {d.message}")
                if d.hint:
                    console.print(f"     [dim]hint:[/dim] {d.hint}")
            if len(errors) > 5:
                console.print(f"  [dim]…and {len(errors) - 5} more.[/dim]")
        if warns:
            console.print(
                f"[yellow]{len(warns)} warning(s).[/yellow] Run `praxis report` for details."
            )


def _find_schema(quiet: bool = False) -> Path:
    """Locate schemas/praxis-ir.schema.json relative to the repo root.

    Raises FileNotFoundError if `quiet=True` and the schema can't be found;
    otherwise prints a red error and exits with code 2 (CLI default).
    """
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / "schemas" / "praxis-ir.schema.json"
        if candidate.exists():
            return candidate
    # Fallback: look relative to the installed package (development checkout layout).
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "schemas" / "praxis-ir.schema.json"
        if candidate.exists():
            return candidate
    if quiet:
        raise FileNotFoundError(
            "praxis-ir.schema.json not found by walking up from cwd or the installed package."
        )
    console.print("[red]Could not locate praxis-ir.schema.json[/red]")
    raise typer.Exit(2)


if __name__ == "__main__":
    app()

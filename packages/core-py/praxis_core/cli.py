"""praxis — CLI entry point."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from praxis_core import IR_VERSION
from praxis_core.extract import extract_prompt_clusters
from praxis_core.ir import IRGraph
from praxis_core.ir.models import NodeKind
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


@app.command()
def scan(
    path: Path = typer.Argument(
        ..., exists=True, file_okay=False, dir_okay=True, help="Source project root."
    ),
    emit_ir: Path | None = typer.Option(None, "--emit-ir", help="Write the IR JSON to this path."),
) -> None:
    """Walk the project, build the IR, and print a summary table."""
    ir = build_ir(path)
    _print_summary(ir)
    if emit_ir:
        emit_ir.write_text(ir_to_json(ir), encoding="utf-8")
        console.print(f"[dim]IR written to {emit_ir}[/dim]")


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
) -> None:
    """Translate the project to the target framework. Writes files + report + IR."""
    if target != "hermes":
        console.print(f"[red]Target '{target}' not supported in v0.1. Use 'hermes'.[/red]")
        raise typer.Exit(2)
    result = migrate(path, out)
    console.print(f"[green]Migrated[/green] → {out}")
    console.print(f"  report: {result['report_path']}")
    console.print(f"  graph : {result['graph_path']}")
    console.print(f"  ir    : {result['ir_path']}")
    totals = {k: len(v) for k, v in result["written"].items()}
    console.print(f"  files : {totals}")


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
    """Cluster prompts by structural similarity; surface candidate skill extractions."""
    ir = build_ir(path)
    total_prompts = sum(
        1
        for n in ir.nodes
        if (n.kind.value if hasattr(n.kind, "value") else n.kind) == NodeKind.PROMPT.value
    )
    clusters = extract_prompt_clusters(ir, threshold=threshold)

    table = Table(title=f"Prompt clusters (threshold={threshold:.2f})")
    table.add_column("#", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Min sim", justify="right")
    table.add_column("Max sim", justify="right")
    table.add_column("Members")
    for i, c in enumerate(clusters, start=1):
        table.add_row(
            str(i),
            str(c.size),
            f"{c.min_similarity:.2f}",
            f"{c.max_similarity:.2f}",
            ", ".join(c.members),
        )
    console.print(table)
    console.print(f"[dim]{total_prompts} prompt(s) scanned, {len(clusters)} cluster(s).[/dim]")

    if report:
        report.write_text(
            render_extract_report(clusters, threshold, total_prompts), encoding="utf-8"
        )
        console.print(f"[dim]Report written to {report}[/dim]")


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
        console.print(f"[yellow]{len(ir.diagnostics)} diagnostic(s).[/yellow]")


def _find_schema() -> Path:
    """Locate schemas/praxis-ir.schema.json relative to the repo root."""
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
    console.print("[red]Could not locate praxis-ir.schema.json[/red]")
    raise typer.Exit(2)


if __name__ == "__main__":
    app()

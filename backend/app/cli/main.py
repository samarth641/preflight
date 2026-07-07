"""Trainwise CLI — Typer application (future commands)."""

import typer

app = typer.Typer(
    name="trainwise",
    help="Preflight AI Training Intelligence CLI",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Preflight training copilot for planning, analysis, and recommendations."""


@app.command("doctor")
def doctor() -> None:
    """Check system health and knowledge base status."""
    from rich.console import Console
    from rich.table import Table

    from app.core.bootstrap import setup_plugins
    from app.core.plugins.registry import registry

    setup_plugins()
    console = Console()
    plugin = registry.get_default()
    health = plugin.health_check()

    table = Table(title="Preflight Doctor")
    table.add_column("Check", style="cyan")
    table.add_column("Value", style="green")

    for key, value in health.items():
        table.add_row(key, str(value))

    console.print(table)

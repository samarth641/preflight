"""Trainwise CLI — Typer application."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import typer

app = typer.Typer(
    name="trainwise",
    help="Preflight AI Training Intelligence CLI",
    no_args_is_help=True,
)


class OutputFormat(str, Enum):
    rich = "rich"
    json = "json"
    markdown = "markdown"


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


@app.command("analyze-dataset")
def analyze_dataset(
    path: Path = typer.Argument(..., help="Path to dataset directory", exists=True, file_okay=False),
    max_images: int | None = typer.Option(None, "--max-images", "-n", help="Limit images to scan"),
    output_format: OutputFormat = typer.Option(
        OutputFormat.rich, "--format", "-f", help="Output format"
    ),
) -> None:
    """Analyze an image dataset for quality issues and training readiness."""
    from rich.console import Console

    from app.cli.formatters import render_dataset_analysis, render_dataset_json
    from app.core.analyzers import DatasetAnalyzer

    analyzer = DatasetAnalyzer()
    result = analyzer.analyze(path, max_images=max_images)

    if output_format == OutputFormat.json:
        typer.echo(render_dataset_json(result))
    elif output_format == OutputFormat.markdown:
        typer.echo(_dataset_markdown(result))
    else:
        render_dataset_analysis(result, Console())


def _dataset_markdown(result) -> str:
    m = result.metrics
    lines = [
        f"# Dataset Analysis: {result.dataset_path}",
        "",
        f"**Score:** {result.score}/100 ({result.grade})",
        "",
        "## Metrics",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Images | {m.image_count} |",
        f"| Classes | {m.class_count} |",
        f"| Class Imbalance | {m.class_imbalance_ratio}:1 |",
        f"| Duplicates | {m.duplicate_percent}% |",
        f"| Blurry | {m.blur_percent}% |",
        f"| Missing Labels | {m.missing_label_percent}% |",
        f"| Median Resolution | {m.median_resolution}px |",
        "",
        f"## Expected Accuracy Impact: -{result.accuracy_impact.estimated_loss_percent}%",
        "",
    ]
    for factor in result.accuracy_impact.factors:
        lines.append(f"- {factor}")
    if result.recommendations:
        lines.extend(["", "## Recommendations", ""])
        for rec in result.recommendations:
            lines.append(f"- **{rec.title}:** {rec.recommendation}")
    return "\n".join(lines)


@app.command("analyze-training")
def analyze_training(
    path: Path = typer.Argument(..., help="Path to training log CSV or JSON", exists=True, dir_okay=False),
    output_format: OutputFormat = typer.Option(
        OutputFormat.rich, "--format", "-f", help="Output format"
    ),
) -> None:
    """Analyze a training log for health issues and rule-based recommendations."""
    from rich.console import Console

    from app.cli.formatters import render_training_analysis, render_training_json
    from app.core.analyzers import TrainingAnalyzer

    result = TrainingAnalyzer().analyze(path)

    if output_format == OutputFormat.json:
        typer.echo(render_training_json(result))
    elif output_format == OutputFormat.markdown:
        typer.echo(_training_markdown(result))
    else:
        render_training_analysis(result, Console())


def _training_markdown(result) -> str:
    m = result.metrics
    lines = [
        f"# Training Log Analysis: {result.log_path}",
        "",
        f"**Health:** {result.score}/100 ({result.grade})",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Epochs | {m.epoch_count} |",
        f"| Latest Train Loss | {m.latest_train_loss} |",
        f"| Latest Val Loss | {m.latest_val_loss} |",
        f"| Best Val Loss | {m.best_val_loss} (epoch {m.best_epoch}) |",
        f"| Overfitting Gap | {m.overfitting_gap} |",
        f"| Avg GPU Utilization | {m.avg_gpu_utilization} |",
        "",
    ]
    if result.trends:
        lines.extend(["## Trends", ""])
        for trend in result.trends:
            lines.append(f"- **[{trend.severity}] {trend.name}:** {trend.description}")
        lines.append("")
    if result.recommendations:
        lines.extend(["## Recommendations", ""])
        for rec in result.recommendations:
            lines.append(f"- **{rec.title}:** {rec.recommendation}")
    return "\n".join(lines)


@app.command("recommend-gpu")
def recommend_gpu(
    params_billion: float = typer.Option(..., "--params-billion", "-p", help="Model size in billions"),
    batch_size: int = typer.Option(8, "--batch-size", "-b", help="Training batch size"),
    precision: str = typer.Option("fp16", "--precision", help="fp32, fp16, or int8"),
    mode: str = typer.Option("full", "--mode", "-m", help="full, lora, or inference"),
    model_type: str = typer.Option("vision", "--type", "-t", help="vision, cnn, or transformer"),
    image_size: int = typer.Option(224, "--image-size", help="Input image size for vision models"),
    budget: str | None = typer.Option(None, "--budget", help="entry, mid, high, enthusiast, datacenter"),
    vendor: str | None = typer.Option(None, "--vendor", help="nvidia or amd"),
    max_results: int = typer.Option(5, "--max-results", help="Number of GPUs to show"),
    no_cloud: bool = typer.Option(False, "--no-cloud", help="Skip cloud provider suggestions"),
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """Recommend GPUs based on model size and training requirements."""
    from rich.console import Console

    from app.cli.formatters import render_gpu_json, render_gpu_recommendation
    from app.core.recommenders.gpu import GPURecommendationRequest, GPURecommender, TrainingMode
    from app.core.recommenders.gpu.models import BudgetTier, ModelType

    request = GPURecommendationRequest(
        parameter_count_billion=params_billion,
        batch_size=batch_size,
        precision=precision,
        training_mode=TrainingMode(mode),
        model_type=ModelType(model_type),
        image_size=image_size,
        budget_tier=BudgetTier(budget) if budget else None,
        preferred_vendor=vendor,
        max_results=max_results,
        include_cloud=not no_cloud,
    )

    result = GPURecommender().recommend(request)

    if output_format == OutputFormat.json:
        typer.echo(render_gpu_json(result))
    else:
        render_gpu_recommendation(result, Console())


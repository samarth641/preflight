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
    epochs: int = typer.Option(10, "--epochs", "-e", help="Training epochs for cost estimate"),
    dataset_samples: int = typer.Option(10_000, "--dataset-samples", help="Dataset size for cost estimate"),
    no_cloud: bool = typer.Option(False, "--no-cloud", help="Skip cloud provider suggestions"),
    no_cost: bool = typer.Option(False, "--no-cost", help="Skip cost estimates"),
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
        include_cost=not no_cost,
        epochs=epochs,
        dataset_samples=dataset_samples,
    )

    result = GPURecommender().recommend(request)

    if output_format == OutputFormat.json:
        typer.echo(render_gpu_json(result))
    else:
        render_gpu_recommendation(result, Console())


@app.command("estimate-cost")
def estimate_cost(
    params_billion: float = typer.Option(..., "--params-billion", "-p"),
    gpu_id: str = typer.Option(..., "--gpu", "-g", help="GPU id e.g. rtx-4090, a100-80gb"),
    epochs: int = typer.Option(10, "--epochs", "-e"),
    dataset_samples: int = typer.Option(10_000, "--dataset-samples"),
    batch_size: int = typer.Option(8, "--batch-size", "-b"),
    model_type: str = typer.Option("transformer", "--type", "-t"),
    deployment: str = typer.Option("cloud", "--deployment", help="local or cloud"),
    provider: str | None = typer.Option(None, "--provider", help="Cloud provider e.g. runpod, aws"),
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """Estimate training cost for a GPU and workload."""
    from rich.console import Console

    from app.cli.formatters import render_cost_estimate, render_cost_json
    from app.core.calculators import CostCalculator, CostEstimateRequest
    from app.core.calculators.cost.models import DeploymentType

    request = CostEstimateRequest(
        parameter_count_billion=params_billion,
        gpu_id=gpu_id,
        epochs=epochs,
        dataset_samples=dataset_samples,
        batch_size=batch_size,
        model_type=model_type,
        deployment=DeploymentType(deployment),
        cloud_provider=provider,
    )
    result = CostCalculator().estimate(request)

    if output_format == OutputFormat.json:
        typer.echo(render_cost_json(result))
    else:
        render_cost_estimate(result, Console())


@app.command("predict-duration")
def predict_duration(
    params_billion: float = typer.Option(..., "--params-billion", "-p"),
    dataset_tokens: float = typer.Option(..., "--dataset-tokens", "-d",
                                         help="Training tokens (LLM) or samples"),
    gpu_id: str = typer.Option(..., "--gpu", "-g", help="GPU id e.g. mi300x, rtx-4090"),
    n_gpus: int = typer.Option(1, "--n-gpus", "-n"),
    epochs: int = typer.Option(1, "--epochs", "-e"),
    domain: str = typer.Option("language", "--domain",
                               help="language|vision|multimodal|image generation|biology|other"),
    provider: str | None = typer.Option(None, "--provider", help="Cloud provider for cost"),
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """ML prediction of training duration (and cost) before execution."""
    import json as _json

    from rich.console import Console
    from rich.table import Table

    from app.core.calculators.cost.pricing import PricingRegistry
    from app.core.predictors import DurationPredictor, DurationRequest

    result = DurationPredictor().predict(DurationRequest(
        parameter_count_billion=params_billion,
        dataset_tokens=dataset_tokens,
        gpu_id=gpu_id,
        n_gpus=n_gpus,
        epochs=epochs,
        domain=domain,
    ))
    rate = PricingRegistry().cloud_hourly_rate(gpu_id, provider)
    cost = round(result.estimated_hours * n_gpus * rate, 2) if rate else None

    if output_format == OutputFormat.json:
        payload = {
            "estimated_hours": result.estimated_hours,
            "theoretical_hours": result.theoretical_hours,
            "gpu_id": result.gpu_id,
            "n_gpus": result.n_gpus,
            "model_version": result.model_version,
            "estimated_cost_usd": cost,
            "hourly_rate_usd": rate,
        }
        typer.echo(_json.dumps(payload, indent=2))
        return

    table = Table(title="Training Duration Prediction (ML)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    h = result.estimated_hours
    human = f"{h * 60:.0f}m" if h < 1 else (f"{h:.1f}h" if h < 48 else f"{h / 24:.1f} days")
    table.add_row("Estimated duration", human)
    table.add_row("Estimated hours", f"{h:.2f}")
    table.add_row("Physics-formula hours", f"{result.theoretical_hours:.2f}")
    table.add_row("GPU", f"{result.gpu_id} x{result.n_gpus}")
    if cost is not None:
        table.add_row("Estimated cost", f"${cost:,.2f} (@ ${rate}/h)")
    table.add_row("Model", result.model_version)
    Console().print(table)


@app.command("dashboard-stats")
def dashboard_stats_cmd(
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """Rule-based experiment dashboard stats (demo fixtures)."""
    import json as _json

    from rich.console import Console
    from rich.table import Table

    from app.core.monitors import TrainingMonitor

    stats = TrainingMonitor().dashboard_stats()
    if output_format == OutputFormat.json:
        typer.echo(_json.dumps(stats.model_dump(), indent=2))
        return

    table = Table(title="Dashboard Stats (rule-based demo)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Total experiments", str(stats.total_experiments))
    table.add_row("Running", str(stats.running))
    table.add_row("Completed", str(stats.completed))
    table.add_row("Failed", str(stats.failed))
    table.add_row("100M-class models", str(stats.experiments_100m))
    table.add_row("Avg accuracy", f"{stats.avg_accuracy:.1%}" if stats.avg_accuracy else "—")
    table.add_row("Best accuracy", f"{stats.best_accuracy:.1%}" if stats.best_accuracy else "—")
    table.add_row("Total GPU hours", f"{stats.total_gpu_hours:.1f}")
    table.add_row("Convergence rate", f"{stats.convergence_rate_percent:.1f}%")
    table.add_row("Active experiment", stats.active_experiment_id or "—")
    Console().print(table)


@app.command("list-experiments")
def list_experiments_cmd(
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """Experiment history from rule-based demo store."""
    import json as _json

    from rich.console import Console
    from rich.table import Table

    from app.core.monitors import TrainingMonitor

    history = TrainingMonitor().list_experiments()
    if output_format == OutputFormat.json:
        typer.echo(_json.dumps(history.model_dump(), indent=2))
        return

    table = Table(title="Experiment History (demo)")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Params")
    table.add_column("Status")
    table.add_column("Accuracy", justify="right")
    table.add_column("Convergence")
    for exp in history.experiments:
        acc = f"{exp.final_accuracy:.1%}" if exp.final_accuracy is not None else "—"
        table.add_row(
            exp.id,
            exp.name[:28],
            f"{exp.params_million:.0f}M",
            exp.status,
            acc,
            exp.convergence or "—",
        )
    Console().print(table)


@app.command("monitor-training")
def monitor_training_cmd(
    experiment_id: str | None = typer.Option(None, "--experiment", "-e", help="Experiment id (default: active)"),
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    """Live training monitor — convergence, accuracy, rule-based alerts (demo)."""
    import json as _json

    from rich.console import Console
    from rich.table import Table

    from app.core.monitors import TrainingMonitor

    try:
        live = TrainingMonitor().live_monitor(experiment_id)
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    if output_format == OutputFormat.json:
        typer.echo(_json.dumps(live.model_dump(), indent=2))
        return

    console = Console()
    table = Table(title=f"Live Monitor — {live.experiment_name}")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Experiment", live.experiment_id)
    table.add_row("Params", f"{live.params_million:.0f}M")
    table.add_row("Epoch", f"{live.epoch} / {live.total_epochs}")
    table.add_row("Progress", f"{live.epoch_progress_percent:.1f}%")
    table.add_row("Samples seen", f"{live.samples_seen_million:.1f}M")
    table.add_row("Accuracy", f"{live.accuracy:.1%}" if live.accuracy is not None else "—")
    table.add_row("Val loss", f"{live.val_loss:.4f}" if live.val_loss is not None else "—")
    table.add_row("GPU util", f"{live.gpu_utilization:.0f}%" if live.gpu_utilization else "—")
    table.add_row("Convergence", live.convergence_status)
    table.add_row("Health", f"{live.health_score:.0f} ({live.health_grade})")
    console.print(table)

    if live.warnings:
        console.print("\n[bold yellow]Warnings[/]")
        for w in live.warnings:
            console.print(f"  • {w.title}: {w.message}")
    if live.recommendations:
        console.print("\n[bold cyan]Recommendations[/]")
        for r in live.recommendations:
            console.print(f"  • {r.title}: {r.recommendation}")


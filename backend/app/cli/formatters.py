"""CLI output formatters for dataset analysis."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.core.analyzers.dataset.models import DatasetAnalysisResult

GRADE_COLORS = {"A": "green", "B": "cyan", "C": "yellow", "D": "orange1", "F": "red"}


def render_dataset_analysis(result: DatasetAnalysisResult, console: Console | None = None) -> None:
    """Render dataset analysis as rich terminal output."""
    console = console or Console()

    grade_color = GRADE_COLORS.get(result.grade, "white")
    score_text = Text(f"{result.score}/100 ", style="bold")
    score_text.append(f"({result.grade})", style=f"bold {grade_color}")

    console.print(Panel(score_text, title="Dataset Score", border_style=grade_color))

    metrics_table = Table(title="Dataset Metrics", show_header=True)
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="white")

    m = result.metrics
    metrics_table.add_row("Images", str(m.image_count))
    metrics_table.add_row("Classes", str(m.class_count))
    metrics_table.add_row("Layout", m.layout.value)
    metrics_table.add_row("Class Imbalance", f"{m.class_imbalance_ratio}:1")
    metrics_table.add_row("Duplicates", f"{m.duplicate_count} ({m.duplicate_percent}%)")
    metrics_table.add_row("Blurry", f"{m.blur_count} ({m.blur_percent}%)")
    metrics_table.add_row("Missing Labels", f"{m.missing_label_count} ({m.missing_label_percent}%)")
    metrics_table.add_row("Median Resolution", f"{m.median_resolution}px")
    metrics_table.add_row("Resolution Range", f"{m.min_resolution}px – {m.max_resolution}px")

    console.print(metrics_table)

    if m.class_stats:
        class_table = Table(title="Class Distribution", show_header=True)
        class_table.add_column("Class", style="cyan")
        class_table.add_column("Count", justify="right")
        class_table.add_column("Percent", justify="right")
        for stat in m.class_stats:
            class_table.add_row(stat.name, str(stat.count), f"{stat.percent}%")
        console.print(class_table)

    impact = result.accuracy_impact
    impact_panel = Panel(
        "\n".join(f"• {factor}" for factor in impact.factors),
        title=f"Expected Accuracy Impact: -{impact.estimated_loss_percent}% "
        f"(confidence {impact.confidence:.0%})",
        border_style="yellow" if impact.estimated_loss_percent > 0 else "green",
    )
    console.print(impact_panel)

    if result.warnings:
        warn_table = Table(title="Warnings", show_header=True)
        warn_table.add_column("Warning", style="yellow")
        warn_table.add_column("Confidence", justify="right")
        for warning in result.warnings:
            warn_table.add_row(warning.title, f"{warning.confidence:.0%}")
        console.print(warn_table)

    if result.recommendations:
        rec_table = Table(title="Recommendations", show_header=True)
        rec_table.add_column("Recommendation", style="green")
        rec_table.add_column("Source")
        for rec in result.recommendations:
            rec_table.add_row(rec.recommendation, rec.source)
        console.print(rec_table)


def render_dataset_json(result: DatasetAnalysisResult) -> str:
    """Serialize dataset analysis to JSON."""
    return json.dumps(result.model_dump(mode="json"), indent=2)


def render_training_analysis(result, console: Console | None = None) -> None:
    """Render training log analysis as rich terminal output."""
    from app.core.analyzers.training.models import TrainingAnalysisResult

    assert isinstance(result, TrainingAnalysisResult)
    console = console or Console()

    grade_color = GRADE_COLORS.get(result.grade, "white")
    score_text = Text(f"{result.score}/100 ", style="bold")
    score_text.append(f"({result.grade})", style=f"bold {grade_color}")

    console.print(Panel(score_text, title="Training Health", border_style=grade_color))

    m = result.metrics
    metrics_table = Table(title="Training Metrics", show_header=True)
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Value", style="white")

    metrics_table.add_row("Epochs", str(m.epoch_count))
    metrics_table.add_row("Latest Train Loss", str(m.latest_train_loss))
    metrics_table.add_row("Latest Val Loss", str(m.latest_val_loss))
    metrics_table.add_row("Best Val Loss", f"{m.best_val_loss} (epoch {m.best_epoch})")
    metrics_table.add_row("Overfitting Gap", str(m.overfitting_gap))
    if m.avg_gpu_utilization is not None:
        metrics_table.add_row("Avg GPU Utilization", f"{m.avg_gpu_utilization}%")
    if m.cpu_utilization is not None:
        metrics_table.add_row("Avg CPU Utilization", f"{m.cpu_utilization}%")
    if m.vram_usage_percent is not None:
        metrics_table.add_row("VRAM Usage", f"{m.vram_usage_percent}%")

    console.print(metrics_table)

    if result.trends:
        trend_table = Table(title="Detected Trends", show_header=True)
        trend_table.add_column("Trend", style="cyan")
        trend_table.add_column("Severity")
        trend_table.add_column("Description")
        for trend in result.trends:
            trend_table.add_row(trend.name, trend.severity, trend.description)
        console.print(trend_table)

    if result.warnings:
        warn_table = Table(title="Warnings", show_header=True)
        warn_table.add_column("Warning", style="yellow")
        warn_table.add_column("Confidence", justify="right")
        for warning in result.warnings:
            warn_table.add_row(warning.title, f"{warning.confidence:.0%}")
        console.print(warn_table)

    if result.recommendations:
        rec_table = Table(title="Recommendations", show_header=True)
        rec_table.add_column("Recommendation", style="green")
        rec_table.add_column("Source")
        for rec in result.recommendations:
            rec_table.add_row(rec.recommendation, rec.source)
        console.print(rec_table)


def render_training_json(result) -> str:
    """Serialize training log analysis to JSON."""
    return json.dumps(result.model_dump(mode="json"), indent=2)


FIT_COLORS = {
    "excellent": "green",
    "good": "cyan",
    "tight": "yellow",
    "overkill": "blue",
    "insufficient": "red",
}


def render_gpu_recommendation(result, console: Console | None = None) -> None:
    """Render GPU recommendation as rich terminal output."""
    from app.core.recommenders.gpu.models import GPURecommendationResult

    assert isinstance(result, GPURecommendationResult)
    console = console or Console()

    console.print(
        Panel(
            f"Estimated VRAM required: [bold]{result.required_vram_gb} GB[/bold]",
            title="GPU Recommendation",
            border_style="cyan",
        )
    )

    if result.best_pick:
        best = result.best_pick
        console.print(
            f"\n[bold green]Best pick:[/bold green] {best.gpu.name} "
            f"({best.fit_rating.value}, score {best.score:.2f})"
        )

    if result.candidates:
        table = Table(title="Recommended GPUs", show_header=True)
        table.add_column("Rank", justify="right")
        table.add_column("GPU", style="cyan")
        table.add_column("VRAM")
        table.add_column("TFLOPS")
        table.add_column("Fit")
        table.add_column("Score", justify="right")
        table.add_column("Utilization", justify="right")

        for index, candidate in enumerate(result.candidates, 1):
            fit_color = FIT_COLORS.get(candidate.fit_rating.value, "white")
            table.add_row(
                str(index),
                candidate.gpu.name,
                f"{candidate.gpu.vram_gb}GB",
                f"{candidate.gpu.tflops_fp16:.0f}",
                f"[{fit_color}]{candidate.fit_rating.value}[/{fit_color}]",
                f"{candidate.score:.2f}",
                f"{candidate.vram_utilization:.0%}",
            )
        console.print(table)

        for candidate in result.candidates[:3]:
            console.print(f"\n[bold]{candidate.gpu.name}[/bold]")
            for reason in candidate.reasons:
                console.print(f"  • {reason}")

    if result.cloud_offerings:
        cloud_table = Table(title="Cloud Providers", show_header=True)
        cloud_table.add_column("Provider", style="cyan")
        cloud_table.add_column("Instance")
        cloud_table.add_column("GPU")
        cloud_table.add_column("Notes")
        for offering in result.cloud_offerings:
            cloud_table.add_row(
                offering.provider_name,
                offering.instance_type,
                offering.gpu_name,
                offering.notes,
            )
        console.print(cloud_table)

    if result.knowledge_recommendations:
        rec_table = Table(title="Knowledge Recommendations", show_header=True)
        rec_table.add_column("Recommendation", style="green")
        rec_table.add_column("Source")
        for rec in result.knowledge_recommendations:
            rec_table.add_row(rec.recommendation, rec.source)
        console.print(rec_table)


def render_gpu_json(result) -> str:
    """Serialize GPU recommendation to JSON."""
    return json.dumps(result.model_dump(mode="json"), indent=2)

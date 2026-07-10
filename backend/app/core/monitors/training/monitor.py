"""Rule-based live training monitor and experiment dashboard."""

from __future__ import annotations

from pathlib import Path

from app.core.analyzers.training.analyzer import TrainingAnalyzer
from app.core.parsers.training_log import TrainingLogParser
from app.core.engine.engine import KnowledgeEngine
from app.core.monitors.training.demo_store import default_fixtures_dir, load_demo_history, resolve_log_path
from app.core.monitors.training.models import (
    DashboardStats,
    EpochPoint,
    ExperimentHistoryResponse,
    ExperimentRecord,
    LiveTrainingMonitor,
)

CONVERGENCE_TARGET_ACCURACY = 0.85


class TrainingMonitor:
    """Rule-based training monitor backed by demo experiment fixtures."""

    def __init__(
        self,
        fixtures_dir: Path | None = None,
        analyzer: TrainingAnalyzer | None = None,
        engine: KnowledgeEngine | None = None,
    ) -> None:
        self._fixtures = fixtures_dir or default_fixtures_dir()
        self._analyzer = analyzer or TrainingAnalyzer()
        self._engine = engine or KnowledgeEngine()

    def list_experiments(self) -> ExperimentHistoryResponse:
        records, active_id = load_demo_history(self._fixtures)
        return ExperimentHistoryResponse(experiments=records, active_experiment_id=active_id)

    def dashboard_stats(self) -> DashboardStats:
        records, active_id = load_demo_history(self._fixtures)
        completed = [r for r in records if r.status == "completed"]
        failed = [r for r in records if r.status == "failed"]
        running = [r for r in records if r.status == "running"]
        accuracies = [r.final_accuracy for r in completed if r.final_accuracy is not None]
        converged = [r for r in completed if r.convergence == "converged"]
        hundred_m = [r for r in records if r.params_million <= 150]

        return DashboardStats(
            total_experiments=len(records),
            running=len(running),
            completed=len(completed),
            failed=len(failed),
            experiments_100m=len(hundred_m),
            avg_accuracy=round(sum(accuracies) / len(accuracies), 3) if accuracies else None,
            best_accuracy=max(accuracies) if accuracies else None,
            total_gpu_hours=round(sum(r.duration_hours or 0 for r in records), 1),
            convergence_rate_percent=round(len(converged) / len(completed) * 100, 1) if completed else 0.0,
            active_experiment_id=active_id,
        )

    def live_monitor(self, experiment_id: str | None = None) -> LiveTrainingMonitor:
        records, active_id = load_demo_history(self._fixtures)
        exp_id = experiment_id or active_id
        if not exp_id:
            raise ValueError("No active experiment configured in demo data")

        record = next((r for r in records if r.id == exp_id), None)
        if record is None:
            raise ValueError(f"Experiment not found: {exp_id}")

        log_path = resolve_log_path(exp_id, self._fixtures)
        if log_path is None or not log_path.is_file():
            raise FileNotFoundError(f"No training log for experiment {exp_id}")

        analysis = self._analyzer.analyze(log_path)
        epochs = TrainingLogParser().parse(log_path)
        latest = epochs[-1] if epochs else None
        if latest is None:
            raise ValueError(f"Training log for {exp_id} has no epochs")

        total_epochs = record.total_epochs
        current_epoch = latest.epoch
        progress = round(current_epoch / total_epochs * 100, 1) if total_epochs else 0.0
        samples_m = round(record.params_million * 0.5 * (current_epoch / total_epochs), 2) if total_epochs else 0.0

        convergence = self._convergence_status(analysis.metrics, latest.accuracy, record.target_accuracy)
        monitor_ctx = {
            "monitor": {
                "accuracy": latest.accuracy or 0.0,
                "params_million": record.params_million,
                "epoch_progress_percent": progress,
                "gpu_utilization": latest.gpu_utilization or analysis.metrics.avg_gpu_utilization or 0.0,
                "convergence_status": convergence,
            },
            "training": analysis.metrics.to_context(),
        }
        engine_result = self._engine.evaluate(monitor_ctx, categories=["training", "optimization"])

        curve = [
            EpochPoint(
                epoch=e.epoch,
                train_loss=e.train_loss,
                val_loss=e.val_loss,
                accuracy=e.accuracy,
                gpu_utilization=e.gpu_utilization,
            )
            for e in epochs
        ]

        return LiveTrainingMonitor(
            experiment_id=record.id,
            experiment_name=record.name,
            status=record.status,
            params_million=record.params_million,
            epoch=current_epoch,
            total_epochs=total_epochs,
            epoch_progress_percent=progress,
            samples_seen_million=samples_m,
            train_loss=latest.train_loss,
            val_loss=latest.val_loss,
            accuracy=latest.accuracy,
            gpu_utilization=latest.gpu_utilization,
            convergence_status=convergence,
            health_score=analysis.score,
            health_grade=analysis.grade,
            curve=curve,
            warnings=engine_result.warnings + analysis.warnings,
            recommendations=engine_result.recommendations + analysis.recommendations,
        )

    @staticmethod
    def _convergence_status(metrics, accuracy: float | None, target: float | None) -> str:
        target_acc = target or CONVERGENCE_TARGET_ACCURACY
        acc = accuracy or 0.0
        if metrics.loss_diverging:
            return "diverging"
        if metrics.overfitting_detected and acc >= target_acc * 0.9:
            return "converged"
        if acc >= target_acc and not metrics.validation_loss_increasing:
            return "converged"
        if metrics.accuracy_plateau:
            return "plateau"
        if metrics.train_loss_stagnant:
            return "stagnant"
        return "training"

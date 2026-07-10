"""API route handlers."""

from fastapi import APIRouter, HTTPException

from app.core.analyzers import DatasetAnalyzer, TrainingAnalyzer
from app.core.calculators import CostCalculator
from app.core.config import settings
from app.core.monitors import TrainingMonitor
from app.core.predictors import DurationPredictor, DurationRequest
from app.core.recommenders.gpu import GPURecommender
from app.schemas.common import HealthResponse
from app.schemas.cost import CostEstimateBody, CostEstimateResponse
from app.schemas.dataset import DatasetAnalyzeRequest, DatasetAnalyzeResponse
from app.schemas.gpu import GPURecommendBody, GPURecommendResponse
from app.schemas.monitor import (
    DashboardStatsResponse,
    ExperimentHistoryResponseSchema,
    LiveTrainingMonitorResponse,
)
from app.schemas.predict import DurationPredictBody, DurationPredictResponse
from app.schemas.training import TrainingAnalyzeRequest, TrainingAnalyzeResponse

router = APIRouter()
_monitor = TrainingMonitor()


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@router.post("/dataset/analyze", response_model=DatasetAnalyzeResponse, tags=["dataset"])
def analyze_dataset(body: DatasetAnalyzeRequest) -> DatasetAnalyzeResponse:
    try:
        result = DatasetAnalyzer().analyze(body.path, max_images=body.max_images)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DatasetAnalyzeResponse.model_validate(result.model_dump())


@router.post("/training/analyze", response_model=TrainingAnalyzeResponse, tags=["training"])
def analyze_training(body: TrainingAnalyzeRequest) -> TrainingAnalyzeResponse:
    try:
        result = TrainingAnalyzer().analyze(body.path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TrainingAnalyzeResponse.model_validate(result.model_dump())


@router.get("/dashboard/stats", response_model=DashboardStatsResponse, tags=["monitor"])
def dashboard_stats() -> DashboardStatsResponse:
    """Aggregate experiment dashboard stats (rule-based demo data)."""
    return DashboardStatsResponse.model_validate(_monitor.dashboard_stats().model_dump())


@router.get("/experiments", response_model=ExperimentHistoryResponseSchema, tags=["monitor"])
def list_experiments() -> ExperimentHistoryResponseSchema:
    """Experiment history from demo fixtures."""
    return ExperimentHistoryResponseSchema.model_validate(_monitor.list_experiments().model_dump())


@router.get("/training/monitor", response_model=LiveTrainingMonitorResponse, tags=["monitor"])
def live_training_monitor(experiment_id: str | None = None) -> LiveTrainingMonitorResponse:
    """Live training snapshot with convergence + rule-based alerts (demo data)."""
    try:
        result = _monitor.live_monitor(experiment_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LiveTrainingMonitorResponse.model_validate(result.model_dump())


@router.post("/gpu/recommend", response_model=GPURecommendResponse, tags=["gpu"])
def recommend_gpu(body: GPURecommendBody) -> GPURecommendResponse:
    try:
        result = GPURecommender().recommend(body.to_request())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GPURecommendResponse.model_validate(result.model_dump())


@router.post("/cost/estimate", response_model=CostEstimateResponse, tags=["cost"])
def estimate_cost(body: CostEstimateBody) -> CostEstimateResponse:
    try:
        result = CostCalculator().estimate(body.to_request())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CostEstimateResponse.model_validate(result.model_dump())


@router.post("/predict/duration", response_model=DurationPredictResponse, tags=["predict"])
def predict_duration(body: DurationPredictBody) -> DurationPredictResponse:
    """ML-based training duration prediction (+ optional cost)."""
    from app.core.calculators.cost.pricing import PricingRegistry

    try:
        result = DurationPredictor().predict(DurationRequest(
            parameter_count_billion=body.parameter_count_billion,
            dataset_tokens=body.dataset_tokens,
            gpu_id=body.gpu_id,
            n_gpus=body.n_gpus,
            epochs=body.epochs,
            domain=body.domain,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    hours = result.estimated_hours
    human = (f"{hours * 60:.0f}m" if hours < 1
             else f"{hours:.1f}h" if hours < 48
             else f"{hours / 24:.1f} days")

    rate = PricingRegistry().cloud_hourly_rate(body.gpu_id, body.cloud_provider)
    cost = round(hours * body.n_gpus * rate, 2) if rate else None

    return DurationPredictResponse(
        estimated_hours=hours,
        estimated_duration_human=human,
        theoretical_hours=result.theoretical_hours,
        gpu_id=result.gpu_id,
        n_gpus=result.n_gpus,
        model_version=result.model_version,
        estimated_cost_usd=cost,
        cost_provider=body.cloud_provider if rate else None,
        hourly_rate_usd=rate,
    )

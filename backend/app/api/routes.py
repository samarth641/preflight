"""API route handlers."""

from fastapi import APIRouter, HTTPException

from app.core.analyzers import DatasetAnalyzer, TrainingAnalyzer
from app.core.calculators import CostCalculator
from app.core.config import settings
from app.core.recommenders.gpu import GPURecommender
from app.schemas.common import HealthResponse
from app.schemas.cost import CostEstimateBody, CostEstimateResponse
from app.schemas.dataset import DatasetAnalyzeRequest, DatasetAnalyzeResponse
from app.schemas.gpu import GPURecommendBody, GPURecommendResponse
from app.schemas.training import TrainingAnalyzeRequest, TrainingAnalyzeResponse

router = APIRouter()


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

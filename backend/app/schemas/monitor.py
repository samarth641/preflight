"""API schemas for training monitor and experiment dashboard."""

from pydantic import BaseModel

from app.core.monitors.training.models import (
    DashboardStats,
    ExperimentHistoryResponse,
    LiveTrainingMonitor,
)


class DashboardStatsResponse(DashboardStats):
    pass


class ExperimentHistoryResponseSchema(ExperimentHistoryResponse):
    pass


class LiveTrainingMonitorResponse(LiveTrainingMonitor):
    pass

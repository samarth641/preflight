"""Engine output models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """A scored recommendation produced by the engine."""

    rule_id: str
    title: str
    recommendation: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int
    category: str
    source: str
    documentation_url: str
    references: list[str] = Field(default_factory=list)
    score: float = Field(ge=0.0, le=1.0)


class Warning(BaseModel):
    """A warning produced when conditions indicate risk."""

    rule_id: str
    title: str
    message: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    documentation_url: str


class EngineResult(BaseModel):
    """Complete output from a knowledge engine evaluation."""

    recommendations: list[Recommendation] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    sources: list[str] = Field(default_factory=list)
    matched_rule_count: int = 0
    evaluated_rule_count: int = 0

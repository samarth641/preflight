"""Pydantic models for knowledge base rules."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator


class RuleCondition(BaseModel):
    """Structured condition for rule evaluation.

    Supports simple field comparisons and compound logic via nested conditions.
  """

    field: str | None = None
    operator: str | None = None
    value: Any = None
    all: list[RuleCondition] | None = Field(default=None, alias="and")
    any: list[RuleCondition] | None = Field(default=None, alias="or")
    not_: RuleCondition | None = Field(default=None, alias="not")

    model_config = {"populate_by_name": True}


class Rule(BaseModel):
    """A single recommendation rule from the knowledge base."""

    id: str
    title: str
    source: str
    documentation_url: str
    category: str
    condition: RuleCondition | dict[str, Any] | str
    recommendation: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = Field(ge=1, le=10, default=5)
    references: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, value: float | int | str) -> float:
        """Accept confidence as 0-1 float or 0-100 percentage."""
        if isinstance(value, str):
            value = float(value.rstrip("%"))
        numeric = float(value)
        if numeric > 1.0:
            return numeric / 100.0
        return numeric


class KnowledgeBase(BaseModel):
    """Loaded collection of rules from the knowledge directory."""

    rules: list[Rule] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    load_errors: list[str] = Field(default_factory=list)

    @property
    def rule_count(self) -> int:
        return len(self.rules)

    def rules_by_category(self, category: str) -> list[Rule]:
        return [rule for rule in self.rules if rule.category == category]

    def rule_by_id(self, rule_id: str) -> Rule | None:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

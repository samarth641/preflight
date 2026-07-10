"""Knowledge rule engine — evaluates rules and produces recommendations."""

from __future__ import annotations

import logging
from collections import defaultdict

from app.core.engine.models import EngineResult, Recommendation, Warning
from app.core.knowledge.loader import RuleLoader
from app.core.knowledge.models import KnowledgeBase, Rule
from app.core.rules.evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class KnowledgeEngine:
    """Rule-based expert system that loads YAML knowledge and evaluates conditions.

    The engine is designed as a pluggable backend. An LLM-based engine can
    implement the same interface via the plugin system later.
    """

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        loader: RuleLoader | None = None,
    ) -> None:
        self._loader = loader or RuleLoader()
        self._evaluator = ConditionEvaluator()
        self._knowledge_base = knowledge_base or self._loader.load()

    @property
    def knowledge_base(self) -> KnowledgeBase:
        return self._knowledge_base

    def reload(self) -> KnowledgeBase:
        """Reload rules from disk."""
        self._knowledge_base = self._loader.load()
        return self._knowledge_base

    def evaluate(
        self,
        context: dict,
        *,
        categories: list[str] | None = None,
        min_confidence: float = 0.0,
        max_recommendations: int | None = None,
    ) -> EngineResult:
        """Evaluate all rules against context and return scored recommendations."""
        rules = self._filter_rules(categories, min_confidence)
        matched: list[tuple[Rule, float]] = []

        for rule in rules:
            try:
                if self._evaluator.matches(rule, context):
                    score = self._score_rule(rule)
                    matched.append((rule, score))
            except Exception as exc:
                logger.warning("Failed to evaluate rule %s: %s", rule.id, exc)

        recommendations = self._build_recommendations(matched)
        recommendations = self._resolve_conflicts(recommendations)

        if max_recommendations is not None:
            recommendations = recommendations[:max_recommendations]

        warnings = self._build_warnings(recommendations)
        overall_confidence = self._compute_overall_confidence(recommendations)
        sources = sorted({rec.source for rec in recommendations})

        return EngineResult(
            recommendations=recommendations,
            warnings=warnings,
            confidence=overall_confidence,
            sources=sources,
            matched_rule_count=len(matched),
            evaluated_rule_count=len(rules),
        )

    def explain(self, rule_id: str) -> Rule | None:
        """Return full rule details for the Knowledge Explorer / CLI explain command."""
        return self._knowledge_base.rule_by_id(rule_id)

    def _filter_rules(
        self,
        categories: list[str] | None,
        min_confidence: float,
    ) -> list[Rule]:
        rules = self._knowledge_base.rules

        if categories:
            category_set = set(categories)
            rules = [rule for rule in rules if rule.category in category_set]

        return [rule for rule in rules if rule.confidence >= min_confidence]

    @staticmethod
    def _score_rule(rule: Rule) -> float:
        """Combine confidence and priority into a single score (0-1)."""
        priority_weight = rule.priority / 10.0
        return min(1.0, (rule.confidence * 0.7) + (priority_weight * 0.3))

    def _build_recommendations(self, matched: list[tuple[Rule, float]]) -> list[Recommendation]:
        recommendations: list[Recommendation] = []

        for rule, score in matched:
            recommendations.append(
                Recommendation(
                    rule_id=rule.id,
                    title=rule.title,
                    recommendation=rule.recommendation,
                    reason=rule.reason,
                    confidence=rule.confidence,
                    priority=rule.priority,
                    category=rule.category,
                    source=rule.source,
                    documentation_url=rule.documentation_url,
                    references=rule.references,
                    score=score,
                )
            )

        return sorted(recommendations, key=lambda r: (-r.score, -r.priority))

    def _resolve_conflicts(self, recommendations: list[Recommendation]) -> list[Recommendation]:
        """Keep the top-scoring recommendations per category (avoid one rule silencing a whole topic)."""
        max_per_category = 8
        by_category: dict[str, list[Recommendation]] = defaultdict(list)

        for rec in recommendations:
            by_category[rec.category].append(rec)

        resolved: list[Recommendation] = []
        for category_recs in by_category.values():
            category_recs.sort(key=lambda r: (-r.score, -r.priority))
            kept = category_recs[:max_per_category]
            resolved.extend(kept)

            for suppressed in category_recs[max_per_category:]:
                logger.debug(
                    "Suppressed lower-ranked rule %s in category %s",
                    suppressed.rule_id,
                    suppressed.category,
                )

        return sorted(resolved, key=lambda r: (-r.score, -r.priority))

    @staticmethod
    def _build_warnings(recommendations: list[Recommendation]) -> list[Warning]:
        warnings: list[Warning] = []

        for rec in recommendations:
            if rec.confidence >= 0.8 and rec.priority >= 7:
                warnings.append(
                    Warning(
                        rule_id=rec.rule_id,
                        title=rec.title,
                        message=rec.reason,
                        confidence=rec.confidence,
                        source=rec.source,
                        documentation_url=rec.documentation_url,
                    )
                )

        return warnings

    @staticmethod
    def _compute_overall_confidence(recommendations: list[Recommendation]) -> float:
        if not recommendations:
            return 0.0
        return sum(rec.confidence for rec in recommendations) / len(recommendations)

"""Tests for the knowledge rule engine."""

from pathlib import Path

import pytest

from app.core.engine.engine import KnowledgeEngine
from app.core.knowledge.loader import RuleLoader
from app.core.plugins.implementations.rule_based import RuleBasedEnginePlugin
from app.core.plugins.registry import PluginRegistry
from app.core.rules.evaluator import ConditionEvaluator


@pytest.fixture
def knowledge_root() -> Path:
    return Path(__file__).resolve().parents[1] / "knowledge"


@pytest.fixture
def loader(knowledge_root: Path) -> RuleLoader:
    return RuleLoader(knowledge_root=knowledge_root)


@pytest.fixture
def engine(loader: RuleLoader) -> KnowledgeEngine:
    return KnowledgeEngine(loader=loader)


class TestRuleLoader:
    def test_loads_all_yaml_files(self, loader: RuleLoader) -> None:
        kb = loader.load()
        assert kb.rule_count >= 10
        assert len(kb.categories) >= 3
        assert len(kb.sources) >= 3
        assert not kb.load_errors

    def test_deduplicates_by_id(self, loader: RuleLoader) -> None:
        kb = loader.load()
        ids = [rule.id for rule in kb.rules]
        assert len(ids) == len(set(ids))

    def test_rule_by_id(self, loader: RuleLoader) -> None:
        kb = loader.load()
        rule = kb.rule_by_id("pytorch-overfitting-early-stopping")
        assert rule is not None
        assert rule.source == "PyTorch Documentation"


class TestConditionEvaluator:
    def test_simple_eq(self) -> None:
        evaluator = ConditionEvaluator()
        condition = {"field": "hardware.gpu_vendor", "operator": "eq", "value": "nvidia"}
        assert evaluator.evaluate(condition, {"hardware": {"gpu_vendor": "nvidia"}})

    def test_compound_and(self) -> None:
        evaluator = ConditionEvaluator()
        condition = {
            "and": [
                {"field": "training.epoch", "operator": "gte", "value": 3},
                {"field": "training.validation_loss_increasing", "operator": "eq", "value": True},
            ]
        }
        context = {"training": {"epoch": 5, "validation_loss_increasing": True}}
        assert evaluator.evaluate(condition, context)

    def test_missing_field_returns_false(self) -> None:
        evaluator = ConditionEvaluator()
        condition = {"field": "missing.field", "operator": "eq", "value": 1}
        assert not evaluator.evaluate(condition, {})


class TestKnowledgeEngine:
    def test_overfitting_detection(self, engine: KnowledgeEngine) -> None:
        context = {
            "training": {
                "epoch": 10,
                "validation_loss_increasing": True,
            }
        }
        result = engine.evaluate(context, categories=["training"])
        assert result.matched_rule_count >= 1
        assert any("early stopping" in r.recommendation.lower() for r in result.recommendations)
        assert result.confidence > 0

    def test_vram_warning(self, engine: KnowledgeEngine) -> None:
        context = {"hardware": {"vram_usage_percent": 95}}
        result = engine.evaluate(context, categories=["hardware"])
        assert result.matched_rule_count >= 1

    def test_no_match_returns_empty(self, engine: KnowledgeEngine) -> None:
        result = engine.evaluate({})
        assert result.matched_rule_count == 0
        assert result.confidence == 0.0

    def test_explain_rule(self, engine: KnowledgeEngine) -> None:
        rule = engine.explain("pytorch-mixed-precision-amp")
        assert rule is not None
        assert "amp" in rule.recommendation.lower()


class TestPluginSystem:
    def test_rule_based_plugin(self, loader: RuleLoader) -> None:
        plugin = RuleBasedEnginePlugin(loader=loader)
        assert plugin.metadata.is_default
        result = plugin.evaluate(
            {"hardware": {"gpu_vendor": "nvidia"}, "model": {"supports_amp": True}}
        )
        assert len(result.recommendations) >= 1

    def test_registry(self, loader: RuleLoader) -> None:
        reg = PluginRegistry()
        plugin = RuleBasedEnginePlugin(loader=loader)
        reg.register(plugin, set_default=True)
        health = reg.get_default().health_check()
        assert health["status"] == "ok"
        assert health["rule_count"] >= 10

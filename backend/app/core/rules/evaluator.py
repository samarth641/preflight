"""Condition evaluation for knowledge rules."""

from __future__ import annotations

from typing import Any

from app.core.knowledge.models import Rule, RuleCondition


class ConditionEvaluator:
    """Evaluates rule conditions against a runtime context dictionary."""

    SUPPORTED_OPERATORS = frozenset(
        {
            "eq",
            "ne",
            "gt",
            "gte",
            "lt",
            "lte",
            "in",
            "not_in",
            "contains",
            "exists",
            "not_exists",
        }
    )

    def evaluate(self, condition: RuleCondition | dict[str, Any] | str, context: dict[str, Any]) -> bool:
        if isinstance(condition, str):
            return self._evaluate_expression(condition, context)

        if isinstance(condition, dict):
            condition = RuleCondition.model_validate(condition)

        return self._evaluate_structured(condition, context)

    def _evaluate_structured(self, condition: RuleCondition, context: dict[str, Any]) -> bool:
        if condition.all is not None:
            return all(self._evaluate_structured(sub, context) for sub in condition.all)

        if condition.any is not None:
            return any(self._evaluate_structured(sub, context) for sub in condition.any)

        if condition.not_ is not None:
            return not self._evaluate_structured(condition.not_, context)

        if condition.field is None or condition.operator is None:
            return False

        return self._compare(
            field=condition.field,
            operator=condition.operator,
            expected=condition.value,
            context=context,
        )

    def _compare(
        self,
        field: str,
        operator: str,
        expected: Any,
        context: dict[str, Any],
    ) -> bool:
        if operator not in self.SUPPORTED_OPERATORS:
            raise ValueError(f"Unsupported operator: {operator}")

        actual = self._resolve_field(field, context)

        if operator == "exists":
            return actual is not None

        if operator == "not_exists":
            return actual is None

        if actual is None:
            return False

        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "gt":
            return actual > expected
        if operator == "gte":
            return actual >= expected
        if operator == "lt":
            return actual < expected
        if operator == "lte":
            return actual <= expected
        if operator == "in":
            return actual in expected
        if operator == "not_in":
            return actual not in expected
        if operator == "contains":
            if isinstance(actual, str):
                return str(expected) in actual
            if isinstance(actual, (list, tuple, set)):
                return expected in actual
            return False

        return False

    @staticmethod
    def _resolve_field(field: str, context: dict[str, Any]) -> Any:
        """Resolve dot-notation fields (e.g. training.validation_loss)."""
        current: Any = context
        for part in field.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _evaluate_expression(self, expression: str, context: dict[str, Any]) -> bool:
        """Evaluate simple boolean expressions for advanced rules.

        Example: "training.validation_loss > training.train_loss"
        """
        safe_globals: dict[str, Any] = {"__builtins__": {}}
        safe_locals = self._flatten_context(context)
        try:
            return bool(eval(expression, safe_globals, safe_locals))  # noqa: S307
        except Exception:
            return False

    @staticmethod
    def _flatten_context(context: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in context.items():
            full_key = f"{prefix}.{key}" if prefix else key
            flat[full_key] = value
            flat[key] = value
            if isinstance(value, dict):
                flat.update(ConditionEvaluator._flatten_context(value, full_key))
        return flat

    def matches(self, rule: Rule, context: dict[str, Any]) -> bool:
        return self.evaluate(rule.condition, context)

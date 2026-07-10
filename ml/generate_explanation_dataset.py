"""Generate a LoRA fine-tuning dataset for the AI Explanation Engine (Core Objective #10).

Turns every rule in knowledge/*.yaml into several synthetic "matched" scenarios,
each paired with a house-style natural-language explanation. The model learns to
go from structured engine output (matched recommendations/warnings + signal
values) to the explanation format the Core Objectives doc specifies:

    <what's happening>, because:
    - <reason 1>
    - <reason 2>
    Recommended actions:
    [x] <recommendation 1>
    [x] <recommendation 2>
    Estimated impact: <derived from confidence/priority>

Reuses the real RuleLoader so training data never drifts from what the engine
actually produces. No hand-written gold explanations required — the rule's own
`reason` + `recommendation` fields ARE the supervision signal; the model's job
is fluent multi-signal synthesis, not new domain knowledge.

Usage:
    python ml/generate_explanation_dataset.py
Output:
    data/processed/explanation_train.jsonl
"""
from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.knowledge.loader import RuleLoader  # noqa: E402
from app.core.knowledge.models import Rule, RuleCondition  # noqa: E402

OUT_PATH = REPO / "data" / "processed" / "explanation_train.jsonl"
VARIANTS_PER_RULE = 9
COMPANION_PROBABILITY = 0.4  # chance of bundling a second rule from the same category
SEED = 42

INSTRUCTION = (
    "You are Preflight's AI Explanation Engine. Given the matched training-analysis "
    "signals below, write a short, plain-language explanation of what's happening, "
    "why, and what to do about it. Follow this exact structure: an opening sentence, "
    "a 'because:' bullet list of reasons, a 'Recommended actions:' checklist, and an "
    "'Estimated impact:' line."
)


@dataclass
class Signal:
    field: str
    value: object


def _leaf_conditions(cond: RuleCondition | dict | str, out: list[RuleCondition]) -> None:
    """Flatten a (possibly compound and/or/not) condition into its leaf comparisons."""
    if isinstance(cond, str) or cond is None:
        return
    if isinstance(cond, dict):
        cond = RuleCondition.model_validate(cond)
    if cond.field is not None:
        out.append(cond)
    for sub in (cond.all or []) + (cond.any or []):
        _leaf_conditions(sub, out)
    if cond.not_ is not None:
        _leaf_conditions(cond.not_, out)


def _sample_value(leaf: RuleCondition, rng: random.Random) -> object:
    """Pick a plausible concrete value that would satisfy this leaf condition."""
    op, val = leaf.operator, leaf.value
    try:
        if op in ("gt", "gte") and isinstance(val, (int, float)):
            jitter = val * rng.uniform(0.02, 0.25) + 1
            return round(val + jitter, 2)
        if op in ("lt", "lte") and isinstance(val, (int, float)):
            jitter = abs(val) * rng.uniform(0.02, 0.25) + 1
            return round(max(val - jitter, 0), 2)
        if op == "eq":
            return val
        if op == "ne":
            return f"not_{val}"
        if op == "in" and isinstance(val, list) and val:
            return rng.choice(val)
        if op == "not_in" and isinstance(val, list) and val:
            return f"other_than_{rng.choice(val)}"
        if op == "exists":
            return True
        if op == "not_exists":
            return None
        if op == "contains":
            return val
    except (TypeError, ValueError):
        pass
    return val


def _signals_for_rule(rule: Rule, rng: random.Random) -> list[Signal]:
    leaves: list[RuleCondition] = []
    _leaf_conditions(rule.condition, leaves)
    return [Signal(field=leaf.field, value=_sample_value(leaf, rng)) for leaf in leaves if leaf.field]


def _nest(flat: dict[str, object]) -> dict:
    """Turn {'hardware.vram_usage_percent': 92} into {'hardware': {'vram_usage_percent': 92}}."""
    nested: dict = {}
    for dotted, value in flat.items():
        parts = dotted.split(".")
        cur = nested
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return nested


def _format_reason(rule: Rule, signals: list[Signal]) -> str:
    signal_bits = ", ".join(f"{s.field}={s.value}" for s in signals) if signals else ""
    reason = rule.reason.rstrip(".")
    return f"{reason} (observed: {signal_bits})." if signal_bits else f"{reason}."


def _impact_line(rules: list[Rule]) -> str:
    avg_conf = sum(r.confidence for r in rules) / len(rules)
    pct = round(avg_conf * (10 + max(r.priority for r in rules)) , 0)
    pct = max(5, min(int(pct), 60))
    return f"Estimated impact: acting on this should meaningfully reduce risk/cost (~{pct}% confidence-weighted priority)."


def _build_example(primary: Rule, companion: Rule | None, rng: random.Random) -> dict:
    rules = [primary] + ([companion] if companion else [])
    flat_context: dict[str, object] = {}
    per_rule_signals: dict[str, list[Signal]] = {}
    for r in rules:
        sig = _signals_for_rule(r, rng)
        per_rule_signals[r.id] = sig
        for s in sig:
            flat_context[s.field] = s.value

    matched = [
        {
            "rule_id": r.id,
            "title": r.title,
            "category": r.category,
            "confidence": round(r.confidence, 2),
            "priority": r.priority,
            "source": r.source,
        }
        for r in rules
    ]
    engine_input = {"context": _nest(flat_context), "matched": matched}

    opening = f"Preflight flagged {'an issue' if len(rules) == 1 else str(len(rules)) + ' related issues'} in your setup"
    reasons = "\n".join(f"- {_format_reason(r, per_rule_signals[r.id])}" for r in rules)
    actions = "\n".join(f"[x] {r.recommendation}" for r in rules)
    target = (
        f"{opening}, because:\n{reasons}\n\n"
        f"Recommended actions:\n{actions}\n\n"
        f"{_impact_line(rules)}"
    )

    return {
        "instruction": INSTRUCTION,
        "input": json.dumps(engine_input, indent=2, default=str),
        "output": target,
    }


def main() -> None:
    rng = random.Random(SEED)
    kb = RuleLoader().load()
    if kb.load_errors:
        print(f"warning: {len(kb.load_errors)} rule load errors: {kb.load_errors}")

    by_category: dict[str, list[Rule]] = {}
    for rule in kb.rules:
        by_category.setdefault(rule.category, []).append(rule)

    examples: list[dict] = []
    for rule in kb.rules:
        for _ in range(VARIANTS_PER_RULE):
            companion = None
            siblings = [r for r in by_category.get(rule.category, []) if r.id != rule.id]
            if siblings and rng.random() < COMPANION_PROBABILITY:
                companion = rng.choice(siblings)
            examples.append(_build_example(rule, companion, rng))

    rng.shuffle(examples)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")

    print(f"rules loaded: {kb.rule_count}")
    print(f"examples generated: {len(examples)}")
    print(f"wrote: {OUT_PATH}")


if __name__ == "__main__":
    main()

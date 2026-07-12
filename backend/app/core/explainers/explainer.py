"""AI Explanation Engine (Core Objective #10).

Converts a KnowledgeEngine EngineResult into a natural-language explanation.
Two backends:
- "gemma-finetuned": the LoRA-fine-tuned Gemma model (GGUF), trained on AMD
  MI300X via ml/finetune_gemma_explainer.py + ml/generate_explanation_dataset.py.
  Used automatically once the artifact is present.
- "template": deterministic house-style fallback (the exact format the model
  was trained to imitate), so the app is always demoable, model or not — same
  graceful-degradation pattern as DurationPredictor.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.engine.models import EngineResult

_ARTIFACT = Path(__file__).parent / "artifacts" / "gemma-explainer.gguf"

INSTRUCTION = (
    "You are Preflight's AI Explanation Engine. Given the matched training-analysis "
    "signals below, write a short, plain-language explanation of what's happening, "
    "why, and what to do about it. Follow this exact structure: an opening sentence, "
    "a 'because:' bullet list of reasons, a 'Recommended actions:' checklist, and an "
    "'Estimated impact:' line."
)


@dataclass
class ExplanationResult:
    explanation: str
    backend: str  # "gemma-finetuned" or "template"


def _dedupe_by_rule_id(result: EngineResult) -> list[Any]:
    """Recommendations and warnings can share a rule_id (the engine promotes
    high-confidence recommendations to warnings too) — keep the richer
    Recommendation version when both are present for the same rule."""
    seen: dict[str, Any] = {}
    for w in result.warnings:
        seen[w.rule_id] = w
    for r in result.recommendations:
        seen[r.rule_id] = r  # recommendations win: they carry .recommendation too
    return list(seen.values())


def _engine_result_to_payload(result: EngineResult, context: dict[str, Any] | None) -> dict:
    items = _dedupe_by_rule_id(result)
    matched = [
        {
            "rule_id": i.rule_id,
            "title": i.title,
            "category": getattr(i, "category", "warning"),
            "confidence": round(i.confidence, 2),
            "priority": getattr(i, "priority", 10),
            "source": i.source,
        }
        for i in items
    ]
    return {"context": context or {}, "matched": matched}


@lru_cache(maxsize=1)
def _model():
    from llama_cpp import Llama  # optional dependency — imported lazily

    return Llama(model_path=str(_ARTIFACT), n_ctx=1024, verbose=False)


class ExplanationEngine:
    """Explains a KnowledgeEngine result in plain language."""

    def explain(self, result: EngineResult, context: dict[str, Any] | None = None) -> ExplanationResult:
        payload = _engine_result_to_payload(result, context)
        try:
            text = self._model_explain(payload)
            return ExplanationResult(explanation=text, backend="gemma-finetuned")
        except Exception:
            return ExplanationResult(explanation=self._template_explain(result), backend="template")

    @staticmethod
    def _model_explain(payload: dict) -> str:
        if not _ARTIFACT.exists():
            raise FileNotFoundError(_ARTIFACT)
        prompt = (
            f"<start_of_turn>user\n{INSTRUCTION}\n\n"
            f"{json.dumps(payload, indent=2)}<end_of_turn>\n<start_of_turn>model\n"
        )
        out = _model()(prompt, max_tokens=300, stop=["<end_of_turn>"], temperature=0.3)
        text = out["choices"][0]["text"].strip()
        if not text:
            raise ValueError("empty generation")
        return text

    @staticmethod
    def _template_explain(result: EngineResult) -> str:
        items = _dedupe_by_rule_id(result)
        if not items:
            return "No issues detected — current configuration looks healthy."

        count = len(items)
        opening = f"Preflight flagged {'an issue' if count == 1 else f'{count} related issues'} in your setup"

        def reason_of(item: Any) -> str:
            return getattr(item, "reason", None) or getattr(item, "message", "")

        reasons = "\n".join(f"- {reason_of(i)}" for i in items)
        recs = [i.recommendation for i in items if hasattr(i, "recommendation")]
        actions = "\n".join(f"[x] {r}" for r in recs) or "[x] Review the warnings above."
        avg_conf = sum(i.confidence for i in items) / count
        pct = max(5, min(int(avg_conf * 40), 60))

        return (
            f"{opening}, because:\n{reasons}\n\n"
            f"Recommended actions:\n{actions}\n\n"
            f"Estimated impact: acting on this should meaningfully reduce risk/cost "
            f"(~{pct}% confidence-weighted priority)."
        )

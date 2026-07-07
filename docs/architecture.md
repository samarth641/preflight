# Preflight Architecture

## Overview

Preflight is a **rule-based expert system** for AI training intelligence. It is not an AI model — recommendations come from structured knowledge extracted from official documentation.

Both the web dashboard and CLI (`trainwise`) share the same backend. Business logic is never duplicated.

```
┌─────────────────────────────────────────────────────────┐
│                     Interfaces                          │
│  ┌──────────────────┐    ┌──────────────────────────┐ │
│  │  Next.js Web UI  │    │  trainwise CLI (Typer)   │ │
│  └────────┬─────────┘    └────────────┬─────────────┘ │
│           │                           │               │
│           └───────────┬───────────────┘               │
│                       ▼                               │
│              ┌─────────────────┐                      │
│              │   FastAPI API   │                      │
│              └────────┬────────┘                      │
│                       ▼                               │
│              ┌─────────────────┐                      │
│              │ Plugin Registry │                      │
│              └────────┬────────┘                      │
│                       ▼                               │
│     ┌─────────────────────────────────────┐           │
│     │     EnginePlugin (abstract)         │           │
│     ├─────────────────┬───────────────────┤           │
│     │ RuleBasedPlugin │ LLMPlugin (future)│           │
│     └────────┬────────┴───────────────────┘           │
│              ▼                                        │
│     ┌─────────────────┐                               │
│     │ KnowledgeEngine │                               │
│     └────────┬────────┘                               │
│              ▼                                        │
│     ┌─────────────────┐    ┌──────────────────┐     │
│     │ RuleLoader      │───▶│ knowledge/*.yaml │     │
│     └─────────────────┘    └──────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Knowledge Base (`knowledge/`)

YAML files organized by domain:

| Directory     | Source                          |
|---------------|---------------------------------|
| `pytorch/`    | PyTorch Documentation           |
| `cuda/`       | NVIDIA CUDA Documentation       |
| `rocm/`       | AMD ROCm Documentation          |
| `huggingface/`| Hugging Face Documentation      |
| `deepspeed/`  | DeepSpeed Documentation         |
| `datasets/`   | Dataset quality best practices  |
| `hardware/`   | GPU specifications and rules    |

### 2. Rule Schema

Every rule contains:

```yaml
id: unique-rule-id
title: Human-readable title
source: PyTorch Documentation
documentation_url: https://...
category: training | optimization | dataset | hardware
condition:
  field: training.validation_loss_increasing
  operator: eq
  value: true
recommendation: What to do
reason: Why this matters
confidence: 0.92        # 0-1 or 0-100
priority: 9             # 1-10
references:
  - "Source citation"
```

Conditions support compound logic via `and`, `or`, `not` operators.

### 3. Rule Loader (`app/core/knowledge/loader.py`)

- Recursively scans `knowledge/` for `.yaml` / `.yml`
- Validates each rule with Pydantic
- Deduplicates by `id` (keeps highest priority)
- Reports load errors without failing silently

### 4. Condition Evaluator (`app/core/rules/evaluator.py`)

Evaluates rule conditions against a runtime context dictionary:

```python
context = {
    "training": {"epoch": 10, "validation_loss_increasing": True},
    "hardware": {"gpu_vendor": "nvidia", "vram_gb": 24},
    "model": {"parameter_count": 7_000_000_000},
    "dataset": {"class_imbalance_ratio": 8},
}
```

Supported operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `exists`, `not_exists`.

### 5. Knowledge Engine (`app/core/engine/engine.py`)

Pipeline:

1. **Filter** rules by category and minimum confidence
2. **Evaluate** each rule's condition against context
3. **Score** matched rules: `score = confidence × 0.7 + priority/10 × 0.3`
4. **Resolve conflicts** — keep highest-scored rule per category
5. **Generate warnings** for high-confidence, high-priority matches
6. **Return** `EngineResult` with recommendations, warnings, confidence, sources

### 6. Plugin System (`app/core/plugins/`)

```python
class EnginePlugin(ABC):
    def evaluate(context, **kwargs) -> EngineResult: ...
    def reload() -> None: ...
    def health_check() -> dict: ...
```

The `PluginRegistry` supports:
- Manual registration
- Auto-discovery from `app/core/plugins/implementations/`
- Default plugin selection
- Future LLM backend swap without API changes

## Backend Structure

```
backend/app/
├── api/              # FastAPI routes (future)
├── core/
│   ├── knowledge/    # Models + RuleLoader
│   ├── rules/        # ConditionEvaluator
│   ├── engine/       # KnowledgeEngine
│   ├── plugins/      # Plugin system
│   ├── calculators/  # Cost calculator (future)
│   ├── analyzers/    # Dataset/training analyzers (future)
│   ├── recommenders/ # GPU recommender (future)
│   ├── parsers/      # Log parsers (future)
│   └── reports/      # Report generation (future)
├── models/           # MongoDB documents (future)
├── schemas/          # API schemas (future)
├── services/         # Business services (future)
├── database/         # MongoDB connection (future)
└── cli/              # trainwise CLI
```

## Design Principles

1. **Rules never hardcoded** — all knowledge in YAML
2. **Single backend** — web and CLI share engine
3. **Pluggable engine** — swap rule-based for LLM later
4. **Modular** — each analyzer/calculator is independent
5. **Testable** — engine tested without HTTP or CLI
6. **Production-ready** — Pydantic validation, structured logging, error reporting

## Next Steps (Phase 2)

- Dataset Analyzer module
- Training Log Analyzer module
- GPU Recommender + hardware database
- Cost Calculator
- FastAPI endpoints
- CLI commands (`plan`, `analyze-dataset`, `estimate-cost`, etc.)
- Next.js dashboard

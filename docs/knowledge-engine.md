# Knowledge Engine

## Rule File Format

Rules can be defined as a single object or a list:

```yaml
# Single rule
id: my-rule
title: ...
# ...

# Multiple rules
- id: rule-one
  title: ...
- id: rule-two
  title: ...

# Wrapped in a rules key (for files with metadata)
gpus:
  - id: rtx-4090
    name: ...
rules:
  - id: hardware-rule
    title: ...
```

## Condition Syntax

### Simple condition

```yaml
condition:
  field: hardware.vram_gb
  operator: lt
  value: 16
```

### Compound conditions

```yaml
condition:
  and:
    - field: training.epoch
      operator: gte
      value: 3
    - field: training.validation_loss_increasing
      operator: eq
      value: true

condition:
  or:
    - field: hardware.gpu_vendor
      operator: eq
      value: nvidia
    - field: hardware.gpu_vendor
      operator: eq
      value: amd

condition:
  not:
    field: training.mixed_precision
    operator: eq
    value: true
```

### Expression strings (advanced)

```yaml
condition: "training.validation_loss > training.train_loss"
```

## Adding New Rules

1. Create or edit a `.yaml` file in the appropriate `knowledge/` subdirectory
2. Follow the rule schema (all fields required except `tags` and `references`)
3. Run `trainwise doctor` to verify loading
4. Run `pytest tests/test_engine.py` to validate evaluation

## Confidence Values

Accept either decimal (0.0–1.0) or percentage (0–100):

```yaml
confidence: 0.92    # preferred
confidence: 92      # auto-normalized to 0.92
```

## Priority Scale

| Priority | Meaning        |
|----------|----------------|
| 1–3      | Informational  |
| 4–6      | Suggested      |
| 7–8      | Recommended    |
| 9–10     | Critical       |

Higher priority rules win during conflict resolution within the same category.

## Engine Usage

```python
from app.core.engine import KnowledgeEngine

engine = KnowledgeEngine()
result = engine.evaluate({
    "training": {"epoch": 10, "validation_loss_increasing": True},
})

for rec in result.recommendations:
    print(f"[{rec.confidence:.0%}] {rec.title}: {rec.recommendation}")
```

## Plugin Usage

```python
from app.core.bootstrap import setup_plugins
from app.core.plugins.registry import registry

setup_plugins()
result = registry.evaluate(context={"hardware": {"vram_gb": 8}})
```

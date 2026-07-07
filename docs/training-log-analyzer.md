# Training Log Analyzer — Implementation Guide

This document is for developers implementing the **Training Log Analyzer** module in Preflight. Follow the same patterns used by the Dataset Analyzer and GPU Recommender.

---

## 1. Goal

Build a module that reads training logs, detects health issues (overfitting, stagnation, bottlenecks), scores training health, and returns **rule-based recommendations** from the YAML knowledge engine.

**It is NOT an AI model.** All recommendations come from structured rules in `knowledge/`.

### Inputs (per READ.MD)

| Field | Description |
|-------|-------------|
| Epoch | Training epoch number |
| Train Loss | Training loss value |
| Validation Loss | Validation loss value |
| Accuracy | Training or validation accuracy (optional) |
| GPU Usage | GPU utilization % (optional) |
| CPU Usage | CPU utilization % (optional) |
| VRAM | VRAM used in GB or % (optional) |
| Power | GPU power draw in watts (optional) |

### Outputs

| Field | Description |
|-------|-------------|
| Health Score | 0–100 numeric score |
| Grade | A / B / C / D / F |
| Warnings | High-priority issues |
| Recommendations | Actionable fixes from knowledge rules |
| Trends | Detected patterns (overfitting, plateau, etc.) |
| Sources | Documentation references |

### Example behavior

```
Validation loss increasing for 3+ epochs
  → Warning: Possible overfitting
  → Recommendation: Enable early stopping
  → Confidence: 92%
  → Source: PyTorch Documentation
```

This rule already exists in `knowledge/pytorch/training.yaml` (`pytorch-overfitting-early-stopping`).

---

## 2. How it works (pipeline)

```
Training log file (CSV / JSON)
        │
        ▼
   Log Parser          ← app/core/parsers/training_log.py
        │
        ▼
  List[EpochMetrics]   ← one row per epoch
        │
        ▼
  Trend Analyzer       ← app/core/analyzers/training/metrics.py
        │
        ▼
  TrainingMetrics      ← derived signals (loss increasing, GPU low, etc.)
        │
        ├──► Health Score (0–100)
        │
        └──► Knowledge Engine  ← categories: training, optimization, hardware
                    │
                    ▼
           TrainingAnalysisResult
```

**Key principle:** Compute derived boolean/numeric signals, pass them as context to `KnowledgeEngine.evaluate()`, let YAML rules produce recommendations.

---

## 3. Files to create

```
backend/app/core/
├── parsers/
│   ├── __init__.py              # export TrainingLogParser
│   └── training_log.py          # parse CSV / JSON logs
│
└── analyzers/
    ├── __init__.py              # add TrainingAnalyzer export
    └── training/
        ├── __init__.py
        ├── models.py            # Pydantic models
        ├── metrics.py           # trend detection + health score
        └── analyzer.py          # orchestrator (like dataset/analyzer.py)

backend/app/cli/
├── main.py                      # add `analyze-training` command
└── formatters.py                # add render_training_analysis()

knowledge/
├── pytorch/
│   └── training.yaml            # extend with more rules
└── training/                    # (optional new folder)
    └── health.yaml              # training-specific health rules

tests/
└── test_training_analyzer.py
```

---

## 4. Data models (`models.py`)

Use Pydantic, matching the style in `dataset/models.py` and `gpu/models.py`.

### `EpochMetrics` — one epoch of log data

```python
class EpochMetrics(BaseModel):
    epoch: int
    train_loss: float | None = None
    val_loss: float | None = None
    accuracy: float | None = None
    gpu_utilization: float | None = None      # 0–100
    cpu_utilization: float | None = None      # 0–100
    vram_gb: float | None = None
    vram_percent: float | None = None
    power_watts: float | None = None
```

### `TrainingMetrics` — computed from full log

```python
class TrainingMetrics(BaseModel):
    epoch_count: int
    current_epoch: int
    latest_train_loss: float | None
    latest_val_loss: float | None
    best_val_loss: float | None
    best_epoch: int | None

    # Derived trend signals (used by rule engine)
    validation_loss_increasing: bool = False
    train_loss_stagnant: bool = False
    overfitting_gap: float = 0.0          # val_loss - train_loss
    overfitting_detected: bool = False
    loss_diverging: bool = False
    accuracy_plateau: bool = False

    # Resource signals
    gpu_utilization: float | None = None    # latest or avg
    cpu_utilization: float | None = None
    avg_gpu_utilization: float | None = None
    vram_usage_percent: float | None = None
    vram_near_limit: bool = False

    def to_context(self) -> dict:
        return {
            "epoch": self.current_epoch,
            "epoch_count": self.epoch_count,
            "validation_loss_increasing": self.validation_loss_increasing,
            "train_loss_stagnant": self.train_loss_stagnant,
            "overfitting_detected": self.overfitting_detected,
            "overfitting_gap": self.overfitting_gap,
            "loss_diverging": self.loss_diverging,
            "accuracy_plateau": self.accuracy_plateau,
            "gpu_utilization": self.avg_gpu_utilization or self.gpu_utilization,
            "cpu_utilization": self.cpu_utilization,
            "vram_usage_percent": self.vram_usage_percent,
            "train_loss": self.latest_train_loss,
            "val_loss": self.latest_val_loss,
        }
```

### `TrainingTrend` — human-readable detected pattern

```python
class TrainingTrend(BaseModel):
    name: str           # e.g. "overfitting", "stagnation"
    description: str
    severity: str       # low, medium, high
    epochs_affected: list[int] = []
```

### `TrainingAnalysisResult` — final output

```python
class TrainingAnalysisResult(BaseModel):
    log_path: Path | None = None
    metrics: TrainingMetrics
    trends: list[TrainingTrend]
    score: float = Field(ge=0.0, le=100.0)
    grade: str
    warnings: list[Warning]           # from app.core.engine.models
    recommendations: list[Recommendation]
    sources: list[str]
```

---

## 5. Log parser (`parsers/training_log.py`)

Support at minimum **CSV** and **JSON**. Auto-detect format from file extension or content.

### Expected CSV format

```csv
epoch,train_loss,val_loss,accuracy,gpu_util,cpu_util,vram_gb,power_w
1,2.31,2.45,0.42,85,30,8.2,220
2,1.89,2.10,0.55,88,32,8.4,230
3,1.52,2.15,0.61,90,28,8.5,235
```

Column names should be **flexible** (aliases):

| Canonical field | Accepted aliases |
|----------------|------------------|
| `epoch` | `epoch`, `step`, `e` |
| `train_loss` | `train_loss`, `loss`, `training_loss` |
| `val_loss` | `val_loss`, `validation_loss`, `valid_loss` |
| `accuracy` | `accuracy`, `acc`, `val_accuracy` |
| `gpu_utilization` | `gpu_util`, `gpu_usage`, `gpu_utilization` |
| `cpu_utilization` | `cpu_util`, `cpu_usage`, `cpu_utilization` |
| `vram_gb` | `vram_gb`, `vram`, `gpu_memory` |
| `vram_percent` | `vram_percent`, `vram_usage` |
| `power_watts` | `power_w`, `power`, `gpu_power` |

### JSON format

```json
{
  "epochs": [
    {"epoch": 1, "train_loss": 2.31, "val_loss": 2.45, "accuracy": 0.42},
    {"epoch": 2, "train_loss": 1.89, "val_loss": 2.10, "accuracy": 0.55}
  ]
}
```

Also accept a plain list: `[{...}, {...}]`.

### Parser interface

```python
class TrainingLogParser:
    def parse(self, path: Path) -> list[EpochMetrics]:
        ...
```

Raise `ValueError` with a clear message if required columns are missing.

---

## 6. Trend detection (`metrics.py`)

Implement pure functions — no I/O, easy to test.

### 6.1 Validation loss increasing

```python
def is_loss_increasing(losses: list[float], window: int = 3) -> bool:
    """True if loss rose for `window` consecutive epochs at the end."""
    if len(losses) < window + 1:
        return False
    recent = losses[-(window + 1):]
    return all(recent[i] < recent[i + 1] for i in range(window))
```

Set `validation_loss_increasing = True` when this returns True on `val_loss` series.

> This directly triggers the existing rule `pytorch-overfitting-early-stopping`.

### 6.2 Overfitting gap

```python
overfitting_gap = latest_val_loss - latest_train_loss
overfitting_detected = overfitting_gap > threshold  # e.g. 0.5 or relative 20%
```

### 6.3 Train loss stagnant

Train loss changed less than 1% over the last N epochs (default N=5).

### 6.4 Loss diverging

Train or val loss increased by more than 2× from the best value.

### 6.5 Accuracy plateau

Accuracy improved less than 0.5% over the last N epochs.

### 6.6 GPU bottleneck

`avg_gpu_utilization < 70` and `cpu_utilization < 50` → data loading bottleneck.

> Triggers existing rule `pytorch-dataloader-workers`.

### 6.7 VRAM near limit

`vram_percent >= 90` or `vram_gb` close to known GPU limit.

> Triggers existing rule in `knowledge/cuda/memory.yaml`.

---

## 7. Health score (`metrics.py`)

Start at **100**, subtract for issues (same pattern as Dataset Analyzer):

```python
def compute_health_score(metrics: TrainingMetrics) -> float:
    score = 100.0

    if metrics.validation_loss_increasing:
        score -= 20
    if metrics.overfitting_detected:
        score -= 15
    if metrics.loss_diverging:
        score -= 25
    if metrics.train_loss_stagnant:
        score -= 10
    if metrics.accuracy_plateau:
        score -= 8
    if metrics.avg_gpu_utilization and metrics.avg_gpu_utilization < 50:
        score -= 10
    if metrics.vram_near_limit:
        score -= 12

    return max(0.0, min(100.0, round(score, 1)))
```

Reuse `score_to_grade()` pattern from dataset analyzer (copy or extract to shared util).

---

## 8. Orchestrator (`analyzer.py`)

Mirror `DatasetAnalyzer` exactly:

```python
class TrainingAnalyzer:
    def __init__(
        self,
        engine: KnowledgeEngine | None = None,
        parser: TrainingLogParser | None = None,
    ) -> None:
        self._engine = engine or KnowledgeEngine()
        self._parser = parser or TrainingLogParser()

    def analyze(self, path: Path | str) -> TrainingAnalysisResult:
        epochs = self._parser.parse(Path(path))
        metrics = compute_training_metrics(epochs)
        return self._build_result(metrics, log_path=Path(path))

    def analyze_epochs(self, epochs: list[EpochMetrics]) -> TrainingAnalysisResult:
        metrics = compute_training_metrics(epochs)
        return self._build_result(metrics)

    def _build_result(self, metrics, log_path=None) -> TrainingAnalysisResult:
        score = compute_health_score(metrics)
        trends = detect_trends(metrics, epochs)  # optional: pass epochs for detail

        engine_result = self._engine.evaluate(
            {"training": metrics.to_context()},
            categories=["training", "optimization"],
        )

        return TrainingAnalysisResult(
            log_path=log_path,
            metrics=metrics,
            trends=trends,
            score=score,
            grade=score_to_grade(score),
            warnings=engine_result.warnings,
            recommendations=engine_result.recommendations,
            sources=engine_result.sources,
        )
```

**Important:** Context key must be `"training"` — existing rules use `training.*` fields.

---

## 9. Knowledge rules to add

Extend `knowledge/pytorch/training.yaml` or create `knowledge/training/health.yaml`:

```yaml
- id: training-loss-divergence
  title: Training Loss Diverging
  source: PyTorch Documentation
  documentation_url: https://pytorch.org/docs/stable/optim.html
  category: training
  condition:
    field: training.loss_diverging
    operator: eq
    value: true
  recommendation: Reduce learning rate by 10x or check for data/label issues.
  reason: Rapidly increasing loss often indicates learning rate is too high or labels are corrupted.
  confidence: 0.88
  priority: 9
  references:
    - "PyTorch learning rate scheduling"

- id: training-loss-stagnant
  title: Training Loss Has Plateaued
  source: PyTorch Documentation
  documentation_url: https://pytorch.org/docs/stable/optim.html
  category: training
  condition:
    field: training.train_loss_stagnant
    operator: eq
    value: true
  recommendation: Try learning rate warmup, a different optimizer, or unfreeze more layers.
  reason: Loss plateau suggests the model stopped learning with the current hyperparameters.
  confidence: 0.80
  priority: 6
  references:
    - "PyTorch optimizer documentation"

- id: training-overfitting-gap
  title: Train/Validation Loss Gap Detected
  source: PyTorch Documentation
  documentation_url: https://pytorch.org/docs/stable/nn.html
  category: training
  condition:
    field: training.overfitting_detected
    operator: eq
    value: true
  recommendation: Add dropout, weight decay, or data augmentation to reduce overfitting.
  reason: Large gap between training and validation loss indicates the model is memorizing training data.
  confidence: 0.90
  priority: 8
  references:
    - "Regularization best practices"
```

---

## 10. CLI command

Add to `backend/app/cli/main.py`:

```bash
trainwise analyze-training path/to/log.csv
trainwise analyze-training path/to/log.json --format json
trainwise analyze-training path/to/log.csv --format markdown
```

### Typer signature

```python
@app.command("analyze-training")
def analyze_training(
    path: Path = typer.Argument(..., help="Path to training log CSV or JSON"),
    output_format: OutputFormat = typer.Option(OutputFormat.rich, "--format", "-f"),
) -> None:
    from app.core.analyzers.training import TrainingAnalyzer
    ...
```

### Rich formatter (`formatters.py`)

Display:
- Health score panel (like dataset score)
- Metrics table (epochs, latest losses, GPU util)
- Trends list
- Warnings + recommendations tables

---

## 11. Tests (`tests/test_training_analyzer.py`)

Create fixture log files in `tests/fixtures/training/`:

### `overfitting.csv` — val loss rises while train loss falls

```csv
epoch,train_loss,val_loss,accuracy,gpu_util
1,2.0,2.1,0.40,85
2,1.5,1.8,0.55,88
3,1.0,1.9,0.60,90
4,0.7,2.1,0.62,90
5,0.5,2.4,0.63,91
```

### `healthy.csv` — both losses decrease

```csv
epoch,train_loss,val_loss,accuracy,gpu_util
1,2.0,2.1,0.40,85
2,1.5,1.7,0.55,88
3,1.0,1.3,0.65,90
4,0.7,1.0,0.72,90
5,0.5,0.8,0.78,91
```

### `gpu_bottleneck.csv` — low GPU util

```csv
epoch,train_loss,val_loss,gpu_util,cpu_util
1,2.0,2.1,45,30
2,1.8,1.9,42,28
3,1.6,1.7,40,25
```

### Test cases

| Test | Assert |
|------|--------|
| `test_parse_csv` | Correct epoch count and values |
| `test_overfitting_detected` | `validation_loss_increasing == True` |
| `test_overfitting_recommendation` | Early stopping rule fires |
| `test_healthy_log_high_score` | Score >= 80 |
| `test_gpu_bottleneck` | Dataloader workers rule fires |
| `test_json_format` | JSON log parses correctly |
| `test_missing_file_raises` | `FileNotFoundError` |

Run:

```bash
cd backend
pytest ../tests/test_training_analyzer.py -v
```

---

## 12. Implementation checklist

Use this order:

- [ ] **Step 1:** Create `models.py` with all Pydantic models
- [ ] **Step 2:** Implement `TrainingLogParser` (CSV + JSON)
- [ ] **Step 3:** Implement `compute_training_metrics()` and trend functions
- [ ] **Step 4:** Implement `compute_health_score()` and `detect_trends()`
- [ ] **Step 5:** Implement `TrainingAnalyzer` orchestrator
- [ ] **Step 6:** Add knowledge rules to YAML
- [ ] **Step 7:** Add CLI command + rich formatter
- [ ] **Step 8:** Write tests with fixture CSV files
- [ ] **Step 9:** Export from `app/core/analyzers/__init__.py`
- [ ] **Step 10:** Update `README.md` with usage section
- [ ] **Step 11:** Run full test suite: `pytest ../tests -v`

---

## 13. Conventions to follow

| Convention | Example |
|------------|---------|
| No hardcoded recommendations | All fixes come from YAML rules |
| Context key for engine | `{"training": metrics.to_context()}` |
| Engine categories | `["training", "optimization"]` |
| Pydantic for all models | Same as dataset/gpu modules |
| Orchestrator pattern | `analyze(path)` + `analyze_epochs(list)` |
| CLI output formats | `rich`, `json`, `markdown` |
| Tests use real fixture files | `tests/fixtures/training/*.csv` |

---

## 14. Reference: existing code to copy patterns from

| Pattern | File |
|---------|------|
| Orchestrator | `backend/app/core/analyzers/dataset/analyzer.py` |
| Metrics + scoring | `backend/app/core/analyzers/dataset/metrics.py` |
| Pydantic models | `backend/app/core/analyzers/dataset/models.py` |
| CLI command | `backend/app/cli/main.py` → `analyze-dataset` |
| Rich formatter | `backend/app/cli/formatters.py` |
| Engine integration | `tests/test_engine.py` → `test_overfitting_detection` |
| Existing training rules | `knowledge/pytorch/training.yaml` |

---

## 15. Example usage (after implementation)

### CLI

```bash
trainwise analyze-training training_log.csv
trainwise analyze-training wandb_export.json --format json
```

### Python

```python
from app.core.analyzers.training import TrainingAnalyzer

result = TrainingAnalyzer().analyze("training_log.csv")
print(f"Health: {result.score}/100 ({result.grade})")
print(f"Overfitting: {result.metrics.overfitting_detected}")

for trend in result.trends:
    print(f"  [{trend.severity}] {trend.name}: {trend.description}")

for rec in result.recommendations:
    print(f"  → {rec.recommendation} ({rec.source})")
```

### Programmatic (no file)

```python
from app.core.analyzers.training import TrainingAnalyzer
from app.core.analyzers.training.models import EpochMetrics

epochs = [
    EpochMetrics(epoch=1, train_loss=2.0, val_loss=2.1),
    EpochMetrics(epoch=2, train_loss=1.5, val_loss=2.5),
    EpochMetrics(epoch=3, train_loss=1.0, val_loss=2.8),
]
result = TrainingAnalyzer().analyze_epochs(epochs)
```

---

## 16. Future extensions (out of scope for v1)

- TensorBoard event file parser (`tensorboard` library)
- Weights & Biases API integration
- MLflow run import
- Real-time streaming analysis during training
- Convergence prediction (heuristic curves)

Keep v1 focused on **CSV/JSON file input** and **rule-based analysis**.

---

## 17. Acceptance criteria

The module is done when:

1. `trainwise analyze-training log.csv` prints health score, trends, and recommendations
2. Overfitting CSV triggers early stopping recommendation (92% confidence)
3. Low GPU util CSV triggers dataloader workers recommendation
4. All tests pass: `pytest ../tests/test_training_analyzer.py -v`
5. No recommendations are hardcoded in Python — all from YAML
6. `README.md` updated with a Training Log Analyzer section

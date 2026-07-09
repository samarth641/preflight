# Preflight VS Code / Cursor Extension

Animated developer dashboard for **GPU recommendations**, **ML training duration**, **dataset quality**, and **training log analysis** — powered by the Preflight FastAPI backend.

## Prerequisites

1. **Backend running** (from repo root):

```powershell
cd backend
pip install -e .
uvicorn app.main:app --reload --port 8000
```

2. **Node.js** (for compiling TypeScript)

## Install (development)

```powershell
cd extension
npm install
npm run compile
```

Then in VS Code / Cursor:

1. Open the `extension` folder (or the repo root)
2. Press **F5** → "Run Extension" — opens a new Extension Development Host window
3. Click the **Preflight** icon in the activity bar, or run **Preflight: Open Dashboard** from the command palette

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `preflight.apiUrl` | `http://localhost:8000` | Preflight API base URL |

## Commands

- **Preflight: Open Dashboard** — full tabbed panel
- **Preflight: Recommend GPU** — opens GPU tab
- **Preflight: Predict Training Duration** — opens duration tab

## Features

| Tab | Engine | API |
|-----|--------|-----|
| GPU | Benchmark-ranked scoring | `POST /api/v1/gpu/recommend` |
| Duration | XGBoost ML | `POST /api/v1/predict/duration` |
| Dataset | Rule engine (23 rules) | `POST /api/v1/dataset/analyze` |
| Training | Rule engine | `POST /api/v1/training/analyze` |

## Package for distribution

```powershell
npm install -g @vscode/vsce
npm run compile
vsce package
```

Install the resulting `.vsix` via **Extensions → … → Install from VSIX**.

## Hackathon demo flow

1. Start API: `uvicorn app.main:app --port 8000`
2. F5 the extension
3. **GPU** tab → 7B LoRA transformer → see H100/MI300X ranked cards animate in
4. **Duration** tab → MI300X ×4, Azure → ML hours + cost
5. **Dataset** → browse to `tests/_cli_sample` → rule warnings
6. **Training** → `tests/fixtures/training/overfitting.csv` → overfitting detected

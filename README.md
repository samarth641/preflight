# Preflight

AI Training Intelligence Platform — a rule-based expert system for ML training recommendations.

## Status

**Phase 1 complete:** Foundation architecture, knowledge engine, rule loader, and plugin system.

## Quick Start

```bash
cd backend
pip install -e ".[dev]"
trainwise doctor
pytest ../tests -v
```

## Architecture

```
preflight/
├── backend/          # FastAPI + Knowledge Engine
├── frontend/         # Next.js dashboard (future)
├── knowledge/        # YAML rule knowledge base
├── packages/         # Shared packages (future)
├── docs/             # Documentation
└── tests/            # Test suite
```

See [docs/architecture.md](docs/architecture.md) for full system design.

## Knowledge Engine

Rules live in `knowledge/` as YAML files. The engine:

1. Auto-loads all YAML from `knowledge/`
2. Evaluates conditions against runtime context
3. Scores and ranks recommendations
4. Resolves conflicts by category
5. Returns recommendations, warnings, confidence, and sources

## Plugin System

The engine is pluggable. The default `rule-based` plugin wraps the YAML knowledge engine.
An LLM-based plugin can be added later without changing API or CLI interfaces.

## License

MIT

"""Smoke-test all Preflight API endpoints used by the VS Code extension."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8000/api/v1"


def post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def main() -> int:
    tests: list[tuple[str, callable]] = [
        ("health", lambda: get("/health")),
        ("gpu/recommend", lambda: post("/gpu/recommend", {
            "parameter_count_billion": 7,
            "training_mode": "lora",
            "model_type": "transformer",
            "epochs": 5,
            "max_results": 3,
        })),
        ("predict/duration", lambda: post("/predict/duration", {
            "parameter_count_billion": 7,
            "dataset_tokens": 100_000_000_000,
            "gpu_id": "mi300x",
            "n_gpus": 4,
            "epochs": 10,
            "cloud_provider": "azure",
        })),
        ("dataset/analyze", lambda: post("/dataset/analyze", {
            "path": "F:/PREFLIIGHT/tests/_cli_sample",
        })),
        ("training/analyze", lambda: post("/training/analyze", {
            "path": "F:/PREFLIIGHT/tests/fixtures/training/overfitting.csv",
        })),
    ]

    failed = 0
    for name, fn in tests:
        try:
            data = fn()
            print(f"OK  {name}")
            if name == "health":
                print(f"    version={data.get('version')}")
            elif name == "gpu/recommend":
                print(f"    candidates={len(data.get('candidates', []))}")
            elif name == "predict/duration":
                print(f"    hours={data.get('estimated_hours')}")
            elif name.endswith("analyze"):
                print(f"    score={data.get('score')} grade={data.get('grade')}")
        except urllib.error.HTTPError as exc:
            failed += 1
            body = exc.read().decode()
            print(f"FAIL {name}: HTTP {exc.code} {body[:200]}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {name}: {exc}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

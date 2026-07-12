"""One-time download of the fine-tuned explainer GGUF into the serving artifacts dir.

The GGUF (~1.6-5 GB) is NOT committed to git — it lives on the Hugging Face Hub and
is fetched into place by running this script once. `ExplanationEngine` then loads it
from the local path with no download logic of its own.

Run it:
    # locally (defaults to the repo/file below; override via env or flags)
    python scripts/download_explainer_model.py

    # explicit
    python scripts/download_explainer_model.py \
        --repo selva-k-r/preflight-gemma-2-2b-explainer-gguf \
        --file gemma-explainer.gguf

    # in a Dockerfile
    RUN python scripts/download_explainer_model.py

Private repo? Set HF_TOKEN in the environment before running.
Idempotent: if the file is already in place it does nothing (use --force to re-fetch).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Where ExplanationEngine expects the model (must match _ARTIFACT in explainer.py).
DEST = (
    Path(__file__).resolve().parent.parent
    / "backend" / "app" / "core" / "explainers" / "artifacts" / "gemma-explainer.gguf"
)

DEFAULT_REPO = os.getenv("EXPLAINER_GGUF_REPO", "selva-k-r/preflight-gemma-2-2b-explainer")
DEFAULT_FILE = os.getenv("EXPLAINER_GGUF_FILE", "gemma-explainer.gguf")


def main() -> int:
    ap = argparse.ArgumentParser(description="Download the explainer GGUF into the artifacts dir.")
    ap.add_argument("--repo", default=DEFAULT_REPO, help="Hugging Face repo id")
    ap.add_argument("--file", default=DEFAULT_FILE, help="filename within the repo")
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    args = ap.parse_args()

    if DEST.exists() and not args.force:
        print(f"[skip] already present: {DEST}  ({DEST.stat().st_size/1e9:.2f} GB)")
        return 0

    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        print("[error] huggingface_hub not installed. Run: pip install huggingface_hub", file=sys.stderr)
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    print(f"[download] {args.repo}/{args.file} -> {DEST}")
    try:
        path = hf_hub_download(
            repo_id=args.repo,
            filename=args.file,
            local_dir=str(DEST.parent),
            token=os.getenv("HF_TOKEN"),  # None for public repos
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[error] download failed: {exc}", file=sys.stderr)
        print("        check the repo id, that it's public (or HF_TOKEN is set), and network access.", file=sys.stderr)
        return 1

    # hf_hub_download lands the file under local_dir/<file>; make sure it's exactly DEST.
    downloaded = Path(path)
    if downloaded != DEST and downloaded.exists():
        downloaded.replace(DEST)

    print(f"[ok] saved: {DEST}  ({DEST.stat().st_size/1e9:.2f} GB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

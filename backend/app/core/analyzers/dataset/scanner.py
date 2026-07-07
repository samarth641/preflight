"""Dataset directory scanner."""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.analyzers.dataset.image_utils import (
    BLUR_THRESHOLD,
    NEAR_DUPLICATE_THRESHOLD,
    analyze_image,
    file_hash,
    hamming_distance,
    is_image_file,
)
from app.core.analyzers.dataset.models import DatasetLayout, ImageSample

logger = logging.getLogger(__name__)

UNLABELED_NAMES = frozenset({"__unlabeled__", "unlabeled", "unknown", "none", ""})


class DatasetScanner:
    """Scans a dataset directory and extracts image metadata."""

    def scan(self, root: Path, *, max_images: int | None = None) -> tuple[list[ImageSample], DatasetLayout]:
        root = root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Dataset path not found: {root}")
        if not root.is_dir():
            raise ValueError(f"Dataset path is not a directory: {root}")

        layout = self._detect_layout(root)
        samples = self._collect_samples(root, layout)

        if max_images is not None:
            samples = samples[:max_images]

        self._analyze_samples(samples)
        self._detect_duplicates(samples)
        return samples, layout

    def _detect_layout(self, root: Path) -> DatasetLayout:
        subdirs = [entry for entry in root.iterdir() if entry.is_dir()]
        image_files = [entry for entry in root.iterdir() if entry.is_file() and is_image_file(entry)]

        has_class_folders = any(
            not entry.name.startswith(".") and entry.name.lower() not in UNLABELED_NAMES
            for entry in subdirs
        )
        has_root_images = len(image_files) > 0

        if has_class_folders and has_root_images:
            return DatasetLayout.MIXED
        if has_class_folders:
            return DatasetLayout.CLASS_FOLDERS
        return DatasetLayout.FLAT

    def _collect_samples(self, root: Path, layout: DatasetLayout) -> list[ImageSample]:
        samples: list[ImageSample] = []

        if layout == DatasetLayout.CLASS_FOLDERS:
            for class_dir in sorted(root.iterdir()):
                if not class_dir.is_dir() or class_dir.name.startswith("."):
                    continue
                label = None if class_dir.name.lower() in UNLABELED_NAMES else class_dir.name
                for image_path in sorted(class_dir.rglob("*")):
                    if image_path.is_file() and is_image_file(image_path):
                        samples.append(
                            ImageSample(
                                path=image_path,
                                label=label,
                                has_label=label is not None,
                            )
                        )
        else:
            for image_path in sorted(root.rglob("*")):
                if image_path.is_file() and is_image_file(image_path):
                    samples.append(ImageSample(path=image_path, label=None, has_label=False))

        return samples

    def _analyze_samples(self, samples: list[ImageSample]) -> None:
        for sample in samples:
            try:
                width, height, blur_score, perceptual_hash = analyze_image(sample.path)
                sample.width = width
                sample.height = height
                sample.blur_score = blur_score
                sample.perceptual_hash = perceptual_hash
                sample.is_blurry = blur_score < BLUR_THRESHOLD
                sample.file_hash = file_hash(sample.path)
            except Exception as exc:
                logger.warning("Failed to analyze %s: %s", sample.path, exc)

    def _detect_duplicates(self, samples: list[ImageSample]) -> None:
        exact_hashes: dict[str, ImageSample] = {}
        perceptual_hashes: list[tuple[int, ImageSample]] = []

        for sample in samples:
            if not sample.file_hash:
                continue

            if sample.file_hash in exact_hashes:
                sample.is_duplicate = True
                continue

            exact_hashes[sample.file_hash] = sample

            if sample.perceptual_hash:
                for existing_hash, existing_sample in perceptual_hashes:
                    if (
                        hamming_distance(sample.perceptual_hash, existing_hash)
                        <= NEAR_DUPLICATE_THRESHOLD
                    ):
                        sample.is_duplicate = True
                        existing_sample.is_duplicate = True
                        break
                else:
                    perceptual_hashes.append((sample.perceptual_hash, sample))

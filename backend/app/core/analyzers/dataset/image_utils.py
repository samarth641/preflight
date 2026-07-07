"""Image analysis utilities for dataset scanning."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tiff", ".tif"}
BLUR_THRESHOLD = 100.0
HASH_SIZE = 8
NEAR_DUPLICATE_THRESHOLD = 5


def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def file_hash(path: Path) -> str:
    """Compute MD5 hash of file contents for exact duplicate detection."""
    hasher = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def average_hash(image: Image.Image, hash_size: int = HASH_SIZE) -> int:
    """Compute average perceptual hash for near-duplicate detection."""
    gray = image.convert("L").resize((hash_size, hash_size), Image.Resampling.LANCZOS)
    pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    result = 0
    for index, pixel in enumerate(pixels):
        if pixel >= avg:
            result |= 1 << index
    return result


def hamming_distance(hash_a: int, hash_b: int) -> int:
    return (hash_a ^ hash_b).bit_count()


def laplacian_variance(image: Image.Image) -> float:
    """Estimate image sharpness using Laplacian variance on a downscaled grayscale image."""
    gray = image.convert("L").resize((64, 64), Image.Resampling.LANCZOS)
    width, height = gray.size
    pixels = list(gray.getdata())

    def pixel_at(x: int, y: int) -> float:
        return float(pixels[y * width + x])

    laplacian_values: list[float] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            value = (
                -4 * pixel_at(x, y)
                + pixel_at(x - 1, y)
                + pixel_at(x + 1, y)
                + pixel_at(x, y - 1)
                + pixel_at(x, y + 1)
            )
            laplacian_values.append(value)

    if not laplacian_values:
        return 0.0

    mean = sum(laplacian_values) / len(laplacian_values)
    variance = sum((value - mean) ** 2 for value in laplacian_values) / len(laplacian_values)
    return variance


def analyze_image(path: Path) -> tuple[int, int, float, int]:
    """Return width, height, blur_score, and perceptual hash for an image."""
    with Image.open(path) as image:
        width, height = image.size
        blur_score = laplacian_variance(image)
        perceptual_hash = average_hash(image)
    return width, height, blur_score, perceptual_hash

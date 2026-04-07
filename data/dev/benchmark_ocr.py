"""Benchmark OCR extraction: GPU vs CPU timing comparison.

Usage (from repo root):
    PYTHONPATH=services/ocr-tool python data/dev/benchmark_ocr.py

Measures:
  1. OpenCV template matching (always CPU, no GPU path)
  2. PaddleOCR inference — CPU (paddlepaddle==3.2.0, CPU-only build)
  3. PaddleOCR inference — GPU attempt (requires paddlepaddle-gpu; will report
     if unavailable or falls back to CPU)

Each stage is timed N_RUNS times (excluding first-run model-load) and averaged.
"""

from __future__ import annotations

import base64
import sys
import time
from pathlib import Path

import cv2
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "pierre_shop_001.png"
TEMPLATES_DIR = REPO_ROOT / "datasets" / "assets" / "templates"
TEMPLATE_FILE = TEMPLATES_DIR / "pierres_detail_panel_corner.png"
LAYOUT_FILE = TEMPLATES_DIR / "pierre_panel_layout.json"

N_RUNS = 5  # timed runs after warm-up

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_image_b64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def decode_image(image_b64: str) -> np.ndarray:
    img_bytes = base64.b64decode(image_b64)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")
    return img


def load_template() -> np.ndarray:
    tmpl = cv2.imread(str(TEMPLATE_FILE))
    if tmpl is None:
        raise FileNotFoundError(f"Template not found: {TEMPLATE_FILE}")
    return tmpl


def locate_and_crop(img: np.ndarray, template: np.ndarray) -> np.ndarray:
    """OpenCV template matching + crop. Returns cropped panel."""
    import json

    from stardew_ocr.crop_pierres_detail_panel import locate_panel, crop_panel

    with open(LAYOUT_FILE) as f:
        layout = json.load(f)
    panel_rel = layout["panel_rel"]

    rel_x, rel_y, _, _, scale, _ = locate_panel(img, template)
    scaled_w = panel_rel["w"] * scale
    scaled_h = panel_rel["h"] * scale
    return crop_panel(img, (rel_x, rel_y, scaled_w, scaled_h))


def make_ocr(device: str | None = None):
    """Return a PaddleOCR instance configured for the given device."""
    from paddleocr import PaddleOCR

    kwargs = dict(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        lang="en",
    )
    if device is not None:
        kwargs["device"] = device
    return PaddleOCR(**kwargs)


def run_ocr_on_crop(ocr, panel_crop: np.ndarray) -> list[dict]:
    upscaled = cv2.resize(panel_crop, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    result = ocr.predict(upscaled)
    if not result or not result[0] or not isinstance(result[0], dict):
        return []
    page = result[0]
    texts = page.get("rec_texts", [])
    scores = page.get("rec_scores", [])
    polys = page.get("rec_polys", [])
    records = []
    panel_h = upscaled.shape[0]
    for text, score, poly in zip(texts, scores, polys):
        if poly is None:
            continue
        ys = [pt[1] for pt in poly]
        centre_y = (min(ys) + max(ys)) / 2
        rel_y = centre_y / panel_h if panel_h > 0 else 0.0
        records.append({"text": text, "score": float(score), "rel_y": rel_y})
    return records


def time_stage(label: str, fn, n: int = N_RUNS) -> float:
    """Run fn() n times, return mean elapsed seconds."""
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t0)
    mean = sum(times) / len(times)
    print(f"  {label}: {mean*1000:.1f} ms avg ({min(times)*1000:.1f}–{max(times)*1000:.1f} ms) over {n} runs")
    return mean


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print(f"\n{'='*60}")
    print("  Stardew Vision — OCR Pipeline Benchmark")
    print(f"  Fixture: {FIXTURE.name}  |  Runs per stage: {N_RUNS}")
    print(f"{'='*60}\n")

    # ---- setup ----
    image_b64 = load_image_b64(FIXTURE)
    img = decode_image(image_b64)
    template = load_template()

    # ---- Stage 1: OpenCV template matching ----
    print("[Stage 1] OpenCV template matching (always CPU)")
    # warm-up
    locate_and_crop(img, template)
    panel_crop = locate_and_crop(img, template)  # reuse for OCR stages
    time_stage("Template match + crop", lambda: locate_and_crop(img, template))
    print()

    # ---- Stage 2: PaddleOCR — CPU (default paddlepaddle 3.2.0 CPU build) ----
    print("[Stage 2] PaddleOCR — CPU (paddlepaddle==3.2.0, CPU-only build)")
    print("  Loading CPU OCR model (warm-up)...", end="", flush=True)
    t0 = time.perf_counter()
    ocr_cpu = make_ocr(device="cpu")
    run_ocr_on_crop(ocr_cpu, panel_crop)  # warm-up inference
    print(f" done ({(time.perf_counter()-t0)*1000:.0f} ms, excluded from timing)")
    time_stage("PaddleOCR inference (CPU)", lambda: run_ocr_on_crop(ocr_cpu, panel_crop))
    print()

    # ---- Stage 3: PaddleOCR — GPU attempt ----
    print("[Stage 3] PaddleOCR — GPU (requires paddlepaddle-gpu; attempting...)")
    try:
        import paddle

        gpu_available = paddle.device.get_device() != "cpu"
        print(f"  paddle.device.get_device() = {paddle.device.get_device()!r}")

        if not gpu_available:
            print("  ⚠  paddlepaddle reports CPU-only build — GPU inference unavailable.")
            print("     Install paddlepaddle-gpu to enable GPU inference.")
            print("     (ROCm/HIP paddlepaddle-gpu is not officially available for gfx1151)")
        else:
            print("  Loading GPU OCR model (warm-up)...", end="", flush=True)
            t0 = time.perf_counter()
            ocr_gpu = make_ocr(device="gpu")
            run_ocr_on_crop(ocr_gpu, panel_crop)
            print(f" done ({(time.perf_counter()-t0)*1000:.0f} ms, excluded from timing)")
            time_stage("PaddleOCR inference (GPU)", lambda: run_ocr_on_crop(ocr_gpu, panel_crop))

    except Exception as exc:
        print(f"  ✗  GPU attempt failed: {exc}")
    print()

    # ---- Summary ----
    print("[Summary]")
    print("  The OpenCV template matching is pure NumPy/C++ — always CPU.")
    print("  PaddleOCR PP-OCRv5 uses paddlepaddle==3.2.0 (CPU-only build).")
    print("  paddlepaddle-gpu for AMD ROCm/gfx1151 is not officially released.")
    print("  If GPU OCR is needed, consider ONNX Runtime with ROCm execution provider.")
    print()


if __name__ == "__main__":
    main()

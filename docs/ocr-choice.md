# OCR Library Selection: Research and Decision

**Date**: 2026-03-17
**Decision**: PaddleOCR (PP-OCRv5)
**Rejected**: EasyOCR, Surya OCR

---

## Context

The Stardew Vision extraction layer (ADR-010) requires a CPU-only OCR library to read text from OpenCV-cropped UI regions — specifically Pierre's shop detail panel at MVP, and additional panel types in later phases. Requirements:

- Runs headless on Linux with Python 3.12 — no GUI, no human guidance
- CPU-only inference (extraction agents are intentionally CPU-bound per ADR-010)
- Handles rendered game UI screenshots (not scanned documents or handwriting)
- Must coexist cleanly with `transformers`, `peft`, and `vLLM` in the same Python environment
- Permissive license (MIT or Apache 2.0) for a conference talk artifact and potential open-source release
- No Tesseract (rule-based, poor on stylized fonts)

Three candidates were evaluated: **EasyOCR**, **PaddleOCR**, and **Surya OCR**.

---

## Candidate 1: EasyOCR

**Framework**: PyTorch | **License**: MIT | **Language support**: 80+

### Pros
- Simplest API in its class — three lines to first result
- Pure PyTorch, same ecosystem as `transformers` and vLLM — zero dependency conflict risk
- Confidence scores per text span
- Handles stylized and variable-width fonts reasonably well
- CPU mode is well-documented and requires no special configuration
- 24k+ GitHub stars, widely used in the community

### Cons
- **Slow on CPU for full-page images** — benchmarks show 10–50+ seconds per full document image on CPU; only competitive with small pre-cropped regions (1–3s)
- **Outputs lowercase by default** — item names like `"Parsnip Seeds"` become `"parsnip seeds"`, degrading TTS narration quality without post-processing
- Higher Word Error Rate than PaddleOCR in head-to-head benchmarks, despite similar Character Error Rate — struggles with word segmentation
- No layout analysis (acceptable here since OpenCV handles cropping)
- Large disk footprint (~2.8 GB) due to PyTorch model weights
- Last major release was 2023; development pace has slowed

### Verdict
Solid choice for simplicity and ecosystem fit. The CPU slowness is largely mitigated by pre-cropping with OpenCV. The **capitalization issue is the decisive weakness** — a narration tool that reads item names in lowercase is meaningfully worse in quality.

---

## Candidate 2: PaddleOCR

**Framework**: PaddlePaddle (Baidu) | **License**: Apache 2.0 | **Language support**: 100+

### Pros
- **Fastest CPU throughput** among deep-learning OCR tools — PP-OCRv5 mobile models are as small as 2 MB (vs Tesseract's 23 MB) with Intel MKL-DNN acceleration built in
- **State-of-the-art accuracy** — PP-OCRv5 (released May 2025) is the benchmark leader for printed text recognition; 13% accuracy improvement over previous generation
- **Preserves original capitalization** — output matches source text exactly
- Modular pipeline with per-flag control: `use_doc_orientation_classify=False`, `use_doc_unwarping=False`, `use_textline_orientation=False` — skip unnecessary steps for a known-horizontal game UI
- Mobile vs Server model choice — tune for speed or accuracy per use case
- Fine-tuning pipeline documented for custom fonts
- Python 3.12 officially supported
- Very actively developed (v3.0 May 2025, v3.0.3 June 2025)
- `cpu_threads` parameter gives explicit CPU utilization control

### Cons
- PaddlePaddle is a second deep-learning framework alongside PyTorch — additional cognitive overhead and installation surface
- AMD ROCm GPU support is absent for standard `paddlepaddle-gpu`; only the Docker-only PaddleOCR-VL-1.5 variant supports AMD Instinct MI-series GPUs. **Not a concern here** — extraction agents are intentionally CPU-only, and production GPU deployment will be on NVIDIA accelerators
- Setup complexity higher than EasyOCR — common first-run issues include import errors and environment isolation
- Some reported issues with periods and commas in early PP-OCR versions (largely resolved in PP-OCRv5)
- Result objects (`.rec_texts`, `.rec_scores`, `.boxes`) are slightly more verbose to parse than EasyOCR's flat tuples

### Verdict
Superior to EasyOCR on every performance dimension relevant to this project. The only real cost is PaddlePaddle as an additional framework, which is acceptable given it runs entirely independently from the PyTorch/transformers stack.

---

## Candidate 3: Surya OCR

**Framework**: HuggingFace Transformers | **License**: GPL-3.0 | **Language support**: 90+

### Pros
- SOTA accuracy for document OCR; outperforms Tesseract on inference time and accuracy
- Line-level bounding boxes (vs word-level in alternatives)
- Full layout analysis: tables, headers, reading order, LaTeX
- Fine-tunable via Hugging Face Trainer

### Cons
- **GPL-3.0 license** — incompatible with a conference artifact and potential open-source release without full copyleft compliance or a commercial license negotiation
- **Critical transformers version conflict** — Surya has a long history of pinning specific `transformers` versions (historically required `==4.36.2`; issued a hotfix specifically for `4.56.0`). Our environment must satisfy `transformers` version requirements simultaneously for Qwen2.5-VL-7B, vLLM 0.7.x, and Surya — a fragile and ongoing maintenance burden
- **CPU is extremely slow** — designed GPU-first; 10x–20x slower on CPU than GPU, making it impractical for CPU-only inference
- **Not suitable for game UI or photos** — explicitly designed for document OCR (scanned pages, PDFs); Surya's own documentation states it does not work on photos or non-document images
- vLLM native integration is an open unresolved GitHub issue (#13172) as of early 2026

### Verdict
Eliminated on three independent grounds: license, dependency conflict, and CPU performance. Would not be the right tool even without those constraints, since it is trained on document data rather than rendered UI screenshots.

---

## Head-to-Head: EasyOCR vs PaddleOCR

| Criterion | EasyOCR | PaddleOCR |
|---|---|---|
| **API complexity** | 3 lines to first result | ~8 lines; flags make intent explicit |
| **CPU speed (small crop)** | ~1–3s | ~0.3–1s |
| **CPU speed (full page)** | 10–50s | 3–8s |
| **Accuracy (printed text)** | Good | Excellent (PP-OCRv5 SOTA) |
| **Capitalization preserved** | No — outputs lowercase | Yes |
| **Dependency conflict risk** | None | None |
| **Framework** | PyTorch (shared) | PaddlePaddle (separate, CPU-only here) |
| **Disable unneeded pipeline steps** | No | Yes (per-flag control) |
| **Model size options** | One size | Mobile (fast) vs Server (accurate) |
| **Fine-tuning on custom fonts** | Limited | Yes — documented pipeline |
| **License** | MIT | Apache 2.0 |
| **Active development** | Moderate (last major: 2023) | Very active (v3.0: May 2025) |

---

## Decision: PaddleOCR

PaddleOCR (PP-OCRv5) is selected. The two decisive factors:

1. **Capitalization**: Stardew Vision reads item names aloud via TTS. EasyOCR's default lowercase output ("parsnip seeds") is a meaningful quality regression vs PaddleOCR's case-preserving output ("Parsnip Seeds"). Post-processing to restore case is error-prone.

2. **CPU throughput**: PaddleOCR is 3–10x faster than EasyOCR on CPU, even on pre-cropped images. For a user-facing accessibility tool, lower latency matters.

The cost — a second framework (`paddlepaddle`) in the environment — is acceptable. PaddlePaddle installs cleanly alongside PyTorch and has no interaction with the `transformers`/vLLM stack.

**Install**:
```
paddlepaddle>=3.0.0
paddleocr>=3.0.0
```

**Usage pattern** (extraction agents):
```python
from paddleocr import PaddleOCR

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    lang='en',
    device='cpu',
)
results = ocr.predict(cropped_image)
for res in results:
    text = " ".join(
        t for t, s in zip(res.rec_texts, res.rec_scores) if s > 0.5
    )
```

---

## Sources

- [EasyOCR GitHub — JaidedAI](https://github.com/JaidedAI/EasyOCR)
- [EasyOCR Official Tutorial — Jaided AI](https://www.jaided.ai/easyocr/tutorial/)
- [EasyOCR CPU speed problem — GitHub Issue #1206](https://github.com/JaidedAI/EasyOCR/issues/1206)
- [I accidentally doubled the speed of EasyOCR — Medium](https://medium.com/@phuocnguyen90/i-accidentally-doubled-the-speed-of-easyocr-3779ec951424)
- [OCR Engine Comparison: Tesseract vs EasyOCR — Medium](https://medium.com/swlh/ocr-engine-comparison-tesseract-vs-easyocr-729be893d3ae)
- [PaddleOCR GitHub — PaddlePaddle](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR PyPI](https://pypi.org/project/paddleocr/)
- [PaddleOCR Python API Usage — DeepWiki](https://deepwiki.com/PaddlePaddle/PaddleOCR/3.3-python-api-usage)
- [PaddleOCR v3.2 Fine-Grained Benchmark — Medium](https://medium.com/@alex_paddleocr/pinpoint-performance-bottlenecks-with-paddleocr-v3-2s-fine-grained-benchmark-d7ba18d63f7d)
- [PaddleOCR vs Tesseract — Koncile](https://www.koncile.ai/en/ressources/paddleocr-analyse-avantages-alternatives-open-source)
- [Unlocking PaddleOCR-VL-1.5 on AMD GPUs — AMD Developer Blog](https://www.amd.com/en/developer/resources/technical-articles/2026/unlocking-high-performance-document-parsing-of-paddleocr-vl-1-5-.html)
- [Improving PPOCR Recognition Time — Medium/Quantrium](https://medium.com/quantrium-tech/optimizing-ppocr-recognition-time-in-python-59f9f6206926)
- [Comparison of Paddle OCR, EasyOCR, KerasOCR, and Tesseract — Plugger.ai](https://www.plugger.ai/blog/comparison-of-paddle-ocr-easyocr-kerasocr-and-tesseract-ocr)
- [OCR comparison: Tesseract vs EasyOCR vs PaddleOCR vs MMOCR — Medium](https://toon-beerten.medium.com/ocr-comparison-tesseract-versus-easyocr-vs-paddleocr-vs-mmocr-a366d9c79e66)
- [Surya OCR GitHub — datalab-to](https://github.com/datalab-to/surya)
- [Surya OCR Releases — GitHub](https://github.com/datalab-to/surya/releases)
- [Surya OCR: New Model request in vLLM — GitHub Issue #13172](https://github.com/vllm-project/vllm/issues/13172)
- [Transformers Version Conflict (DeepSeek-OCR/vLLM parallel case) — GitHub Issue #161](https://github.com/deepseek-ai/DeepSeek-OCR/issues/161)
- [Thorough Comparison of 6 Free and Open Source OCR Tools 2025 — Cisdem](https://www.cisdem.com/resource/open-source-ocr.html)
- [8 Top Open-Source OCR Models Compared — Modal](https://modal.com/blog/8-top-open-source-ocr-models-compared)

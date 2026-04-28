# Talk Outline: Fine-Tuning Vision Language Models for Game Accessibility

## 1. Introduction to the Problem

### a. Explanation
- Stardew Valley is a popular farming/life simulation game
- The game has no built-in accessibility features for visually impaired players
- Key information is presented visually: TV dialogs, shop items, caught fish notifications, menu screens
- Goal: create a system that can "read" the screen and narrate what's happening via text-to-speech

### b. Show Screenshots from Actual Gameplay
- Walk through real gameplay showing the variety of screens a player encounters
- Highlight how much critical information is purely visual
- Show the challenge: screens vary in layout, content, and complexity

### c. Show Annotated Screenshots for Each Screen Type We Help With
- **TV Dialog** — weather forecasts, recipes, tips displayed on the in-game TV
- **Caught Fish** — notification popup when a fish is caught (name, size)
- **Pierre's Shop** — item detail panel showing stats, price, description
- **No Tools (negative class)** — all other screens where no extraction applies

---

## 2. How We Proposed to Solve the Problem

### a. Agentic Workflow Custom for This Problem
- The VLM acts as a dispatcher: looks at the screen, decides which extraction tool to call
- Tools handle the actual data extraction (cropping, OCR, structured output)
- A second pass generates natural language narration from the extracted data
- This is a multi-turn tool-calling pattern, not a single prompt-in/text-out model

### b. "Small" Models Finely Tuned for the Problem Space
- Using Qwen2.5-VL-7B — a 7 billion parameter vision-language model
- Fine-tuned with LoRA (Low-Rank Adaptation) so only ~0.5% of parameters are trained
- Result: a small adapter (~12MB) that teaches the base model our specific screen types and tools
- Trade-off: smaller model = faster inference, runs on consumer hardware, but needs fine-tuning to be accurate

### c. Only Use GPU-Based Models Where They Deliver Bang for the Buck
- GPU for what needs it: screen classification (VLM) and tool selection
- CPU for what doesn't: OCR text extraction (PaddleOCR), image cropping, text-to-speech
- Principle: don't pay GPU costs for tasks a CPU handles well
- Keeps the production deployment cost-effective

---

## 3. Proposed Architecture — Diagram
- High-level diagram showing:
    - Screenshot input
    - VLM (fine-tuned Qwen) classifies screen and selects tool
    - Extraction tool crops and OCRs the relevant region (CPU)
    - VLM generates natural language narration from structured OCR output
    - Text-to-speech output
- Show where GPU vs CPU resources are used
- Show the training pipeline vs production serving pipeline

---

## 4. Now the Steps to Get to Our Solution

### a. Prototype the App with One Screen Type from Start to Finish
- Started with TV dialog as the first screen type
- Built the full pipeline: screenshot -> classification -> crop -> OCR -> narration
- Validated the approach end-to-end before expanding to other screen types

### b. Default VLM Model — Qwen Out of the Box
- First tested Qwen2.5-VL-7B-Instruct with zero fine-tuning
- Results: the base model can describe what it sees but doesn't know our tools or screen types
- Show examples of base model output vs what we need

### c. Why We Picked Qwen
- Open weights, permissive license
- Strong vision-language capabilities at the 7B scale
- Good tool-calling support in the instruction-tuned variant
- Active community and well-documented fine-tuning path
- Runs on consumer AMD GPU hardware (ROCm support)

### d. Why Didn't We Pick Something Like Docling for the OCR
- Docling is designed for document understanding (PDFs, scanned pages)
- Game UI screenshots are not documents — they have pixel art, custom fonts, overlapping sprites
- PaddleOCR handles the raw text extraction well enough for our structured UI regions
- The hard problem isn't OCR — it's knowing *where* to look and *what tool* to call
- That's what the VLM fine-tuning solves

---

## 5. What We Learned from This Prototype
- TODO: Fill in lessons learned from the prototyping phase

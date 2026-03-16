# How to Submit Stardew Valley Screenshots

Thank you for helping us build an accessibility tool for visually impaired Stardew Valley players!

## What We're Building

We're training AI models to describe loot box contents aloud, helping players with low vision understand what items they have without reading tiny pixel-art sprites. Your screenshots help us train these models.

---

## What to Screenshot

1. **Open a chest or storage container** in Stardew Valley
2. **Take a screenshot** showing the chest contents
3. **You do NOT need to crop the screenshot** — it's perfectly fine if your player inventory is also visible!

We'll automatically detect the chest grid and ignore your inventory.

---

## What We Support

✅ **Any chest type**:
- Regular chests (3×12 grid, 36 slots)
- Large chests (3×24 grid, 72 slots)
- Treasure chests from fishing or combat
- Junimo huts, shipping bins, or other containers

✅ **Any platform**:
- PC (Windows, Mac, Linux)
- Nintendo Switch
- iPad / mobile
- Any other platform

✅ **Any resolution or UI scale setting**:
- We support all screen resolutions (1080p, 1440p, 4K, iPad Retina, etc.)
- All in-game UI scale percentages (75%-150%)
- Both windowed and fullscreen modes

✅ **Screenshots with inventory visible**:
- You do NOT need to crop your screenshot
- It's fine if both the chest and your player inventory are visible
- We'll automatically analyze only the chest contents

---

## What to Avoid

❌ **Screenshots during combat or dialogue**
- Make sure the chest UI is fully visible and not obscured by other menus

❌ **Edited or filtered screenshots**
- No brightness adjustments, filters, or overlays
- Submit the original, unedited screenshot from the game

❌ **Modded items** (for now)
- We currently only support vanilla (unmodded) Stardew Valley items
- Mod support may be added in the future!

❌ **Blurry or cropped screenshots**
- Make sure the entire chest grid is visible
- Avoid screenshots that are heavily compressed or low-quality

---

## How to Submit

**[Google Form link will be added here]**

### What We'll Ask For

- **Screenshot upload**: The image file from your device
- **Platform**: PC / Switch / iPad / other
- **Game version**: 1.6.x (check in-game settings)
- **Consent**: Permission to use your screenshot in our public training dataset

---

## Privacy and Credit

- **No personal information**: We only collect the screenshot and basic platform info
- **Public dataset**: Your screenshot will be published in a public HuggingFace dataset for research
- **Optional credit**: If you'd like to be credited in the dataset card, you can provide a username/handle

---

## Technical Details (Optional)

If you're curious about how this works:

- We use Vision Language Models (VLMs) to analyze screenshots and identify items
- The models output structured JSON describing each item, quantity, and quality
- We synthesize this into audio using Text-to-Speech (TTS) for accessibility
- Your screenshots help us train the models to be more accurate!

**Questions?** Open an issue at: https://github.com/[username]/stardew-vision

---

Thank you for helping make Stardew Valley more accessible! 🌟

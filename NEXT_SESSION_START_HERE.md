# 👋 Start Here - Next Session

## ✅ After Annotation is Complete

1. Validate:
   ```bash
   python scripts/annotate_pierre_shop.py --mode validate \
     --annotations datasets/annotated/pierre_shop/annotations.jsonl
   ```

2. Identify test images (where left panel ≠ right panel)

3. Create split generator script (not yet implemented)

4. Generate train/val/test splits (65%/20%/15%)

5. Begin VLM orchestrator work 🚀

## 🔧 Files You'll Use

- `annotation_viewer.html` - Open on host to view images
- `scripts/interactive_annotate.py` - Run in container
- `datasets/annotated/pierre_shop/annotations.jsonl` - Auto-saved progress

##  What's Already Done

- ✅ 22 screenshots copied to `datasets/raw/pierre_shop/`
- ✅ Annotation schema created
- ✅ 22 annotations auto-generated (2 succeeded, 20 need manual input)
- ✅ Interactive script ready
- ✅ HTML viewer generated
- ✅ Complete documentation written

Everything is ready - just need to run the annotation workflow!

---

**Questions?** Check `docs/ANNOTATION_WORKFLOW.md` for troubleshooting and details.

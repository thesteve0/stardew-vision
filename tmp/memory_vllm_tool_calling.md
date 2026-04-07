---
name: vLLM Tool Calling Fixes
description: Bugs found and fixes applied to get Qwen2.5-VL tool calling working with vLLM
type: project
---

Several bugs were found and fixed during 2026-04-04 session. All fixes are in the codebase.

**Bug 1: localhost vs host.docker.internal**
Devcontainer cannot reach host via localhost. Must use host.docker.internal.
VLLM_BASE_URL=http://host.docker.internal:8001/v1 is already set in devcontainer.json.

**Bug 2: Missing custom chat template**
Qwen2.5-VL default chat template has no tool-calling support. Added:
- configs/serving/qwen2_5_vl_tool_template.jinja (merged multi-modal + tool-call format)
- scripts/start_vllm_host.sh mounts it into the vLLM container at /chat_template.jinja
- vLLM started with --chat-template /chat_template.jinja

**Bug 3: finish_reason=stop instead of tool_calls (known vLLM bug)**
vLLM returns tool_calls populated but finish_reason=stop for Qwen2.5-VL.
Fix: in src/stardew_vision/serving/inference.py, changed condition from
`if choice.finish_reason == "tool_calls" and msg.tool_calls:` to `if msg.tool_calls:`

**Bug 4: Qwen ignoring tools without forced tool_choice**
Qwen2.5-VL answers directly from the image without calling tools when tool_choice=auto.
Previous fix: forced tool_choice on turn 0 to crop_pierres_detail_panel.
NOTE (2026-04-05): This forced tool_choice is being REMOVED as part of the ADR-011 design change
(system prompt now general, Qwen decides freely). If zero-shot Qwen still ignores tools,
may need to revisit — but fine-tuning is the intended long-term fix.

**vLLM start command:**
Use scripts/start_vllm_host.sh on the host machine. Includes:
- --enable-auto-tool-choice --tool-call-parser hermes --chat-template /chat_template.jinja
- VLLM_DEBUG_LOG_API_SERVER_RESPONSE=True for response body logging
- VLLM_LOGGING_LEVEL=DEBUG commented out (breaks tool calling per vllm bug #34792)

**Why:** Qwen2.5-VL is a VLM and its chat template doesn't natively merge vision + tool formats.
**How to apply:** If tool calling breaks again, check these four bugs in order.

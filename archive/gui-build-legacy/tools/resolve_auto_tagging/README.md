# Resolve Auto-Tagging Toolkit

DaVinci Resolve projects helper scripts for AI-driven keyword tagging and Smart Bin generation.

## Scripts
- `run_auto_tagging.py` — generate mid-point thumbnails, call OpenAI/Gemini to suggest tags from `config/controlled_vocab.yaml`, and write them to clip metadata.
- `create_smart_bins_poc.py` — rebuild Smart Bins based on keyword rules; supports prefix cleanup and AND/OR matching (default AND).

## Quickstart
```bash
cd /Users/hiroshikodera/repos/_active/tools/davinciauto
export VOCAB_PATH="$PWD/config/controlled_vocab.yaml"
export GEMINI_API_KEY="..."  # or OPENAI_API_KEY

# Tag all clips in the current Resolve project
"/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
  tools/resolve_auto_tagging/run_auto_tagging.py --provider gemini --model gemini-2.5-pro

# Refresh Smart Bins for selected keywords
"/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
  tools/resolve_auto_tagging/create_smart_bins_poc.py \
  --prefix "AI Keywords/" --replace \
  --tags 屋外 自然 夜 女性 Bロール \
  --multi "屋内,都市" --multi "森林,静かな"
```

## Notes
- Scripts expect Resolve scripting modules to be available (run via Resolve console or the bundled Python).
- `run_auto_tagging.py` stores temporary thumbnails in `tools/resolve_auto_tagging/thumbnails/`.
- Additional match logic (e.g. `CombineOp = "Or"`) can be added by extending `create_smart_bins_poc.py`.

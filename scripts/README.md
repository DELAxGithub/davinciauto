# Pipeline Scripts

This directory collects reusable automation scripts. Key entries:

- `orion_ep7_pipeline.py`: end-to-end TTS/timeline/SRT generator for Orion Episode 7 assets.

Call the Orion pipeline from the repo root:

```bash
python scripts/orion_ep7_pipeline.py
```

Remember to export `GOOGLE_APPLICATION_CREDENTIALS` and any voice override environment variables before running.

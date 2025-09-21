DaVinci Auto CLI Bundle
=======================

1. Run `./davinciauto-cli --self-check --json` to verify the environment (ffmpeg, licenses, bundle integrity).
2. Execute a fake run (no API key required):
   `./davinciauto-cli run --script samples/sample_script.txt --output ./out --fake-tts`
3. Configure provider credentials before real runs (e.g., export ELEVENLABS_API_KEY).
4. Refer to docs/CLI_SETUP.md for detailed usage and troubleshooting.

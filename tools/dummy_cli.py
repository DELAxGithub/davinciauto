"""Dummy CLI for GUI integration testing."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--progress-log", required=True)
    parser.add_argument("--self-check", action="store_true")
    args, _ = parser.parse_known_args(argv)

    log = Path(args.progress_log)
    log.write_text("", encoding="utf-8")

    events = [
        {"ts": _now(), "level": "info", "code": "PIPELINE.START", "msg": "Dummy start"},
        {"ts": _now(), "level": "progress", "code": "STEP.PROGRESS", "msg": "Step 1", "progress": {"current": 1, "total": 3}},
        {"ts": _now(), "level": "artifact", "code": "ARTIFACT.CREATED", "msg": "Dummy file", "payload": {"path": "/tmp/dummy.wav"}},
        {"ts": _now(), "level": "progress", "code": "STEP.PROGRESS", "msg": "Step 2", "progress": {"current": 2, "total": 3}},
        {"ts": _now(), "level": "info", "code": "PIPELINE.END", "msg": "Done"},
    ]
    with log.open("a", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
            handle.flush()
            time.sleep(0.3)
    return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

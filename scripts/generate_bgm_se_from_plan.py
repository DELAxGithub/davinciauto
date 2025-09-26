#!/usr/bin/env python3
"""CLI wrapper around `davinciauto_core.bgm.generate_bgm_and_se`."""

from __future__ import annotations

import pathlib
import sys

from davinciauto_core.bgm import (
    BGMGenerationError,
    StableAudioAPIError,
    StableAudioAPIKeyError,
    StableAudioDependencyError,
    generate_bgm_and_se,
)


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python scripts/generate_bgm_se_from_plan.py <plan.json> [--only bgm|sfx]",
            file=sys.stderr,
        )
        return 2

    plan_path = pathlib.Path(sys.argv[1]).expanduser()
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}", file=sys.stderr)
        return 3

    only_mode = None
    if "--only" in sys.argv:
        try:
            only_mode = sys.argv[sys.argv.index("--only") + 1].strip()
        except Exception:
            only_mode = None

    try:
        bgm_tracks, se_tracks, errors = generate_bgm_and_se(plan_path, only=only_mode)
    except StableAudioDependencyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 5
    except StableAudioAPIKeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    except StableAudioAPIError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 6
    except BGMGenerationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 7

    print("BGM SAVED:")
    for path in bgm_tracks:
        print(path)

    print("SE SAVED:")
    for path in se_tracks:
        print(path)

    if errors:
        print("ERRORS:")
        for err in errors:
            print(err)

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Call the shared place-bgm helper from resolve_cli.py run-script."""

from __future__ import annotations

import json


HELPER = "/Users/delaxpro/src/claude-config/skills/place-bgm/scripts/place_bgm_from_plan.py"

with open(HELPER, encoding="utf-8") as handle:
    exec(compile(handle.read(), HELPER, "exec"), globals())

result = place_bgm_from_plan(
    plan_csv=PLAN_CSV,
    timeline_name=TIMELINE_NAME,
    bgm_root=BGM_ROOT,
    dry=DRY,
)
print(json.dumps(result, ensure_ascii=False, indent=2))

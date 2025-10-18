# Orion Auto-Tagging Implementation Tickets

## Issue OAT-001: Implement `import_metadata.py`
**Priority**: Blocker | **Effort**: 2-3 days | **Type**: feature

**Objective**
- Create `tools/resolve_auto_tagging/import_metadata.py` to upsert keywords/comments from `/Orion/data/tags_sanitized.csv` into Resolve Media Pool clips.

**Scope**
- Input CSV: `/Orion/data/tags_sanitized.csv` (UTF-8, headers `Source File`, `Keywords`, `Comments` optional) plus optional columns `Clip Name`, `Bin Path` for lookup fallbacks.
- Resolve metadata targets: Clip `Keywords` (list) and `Comments` fields; match primarily by `File Path` with fallback to `Clip Name` + `Bin Path`.
- Upsert policy: default `append_unique` (set-union with duplicate elimination, lexical sort); flag-driven `replace` to overwrite keywords/comments entirely.
- CLI args: `--csv`, `--project`, `--update-policy`, `--dry-run`, `--log` (file path), `--batch` (commit interval).

**Acceptance Criteria**
1. Ten-line fixture CSV applies without duplicate keywords when using `append_unique`.
2. `--update-policy replace` replaces both keywords/comments when provided.
3. Missing clips emit WARN, continue processing, exit code remains 0.
4. `--dry-run` logs intended operations without writing Resolve metadata.
5. Summary log reports processed/skipped/error counts.

**Technical Notes**
- Use Resolve scripting API (`DaVinciResolveScript`) via existing connection helper.
- Reuse `tags_sanitized.csv` controlled vocabulary as truth source; sanitize tokens by trimming whitespace, normalizing full-width/half-width.
- Provide unit-friendly structure (extract CSV parsing / Resolve adapter for mocking).

---

## Issue OAT-002: Extend `run_auto_tagging.py` CLI controls
**Priority**: High | **Effort**: 1-2 days | **Type**: enhancement

**Objective**
- Introduce staged CLI flags to control project targeting, batching, and dry-run workflows.

**Scope & Rollout**
- **Phase 1**: add `--project`, `--limit`, `--log`; ensure validation, load requested project, enforce limit, duplicate stdout to log file.
- **Phase 2**: add `--batch`, `--merge-policy append_unique|replace`; integrate with metadata write pipeline.
- **Phase 3**: add `--dry-run`, `--thumbnails <dir>` to skip writes and override thumbnail output path.

**Acceptance Criteria**
- Phase 1: `--limit 20` restricts processed clips to 20; `--log` creates/append log file; invalid `--project` exits with code 1.
- Phase 2: `--batch 5` shows batch commits; `--merge-policy replace` overwrites existing keywords.
- Phase 3: `--dry-run` prevents Resolve writes and tags log entries with `[DRY-RUN]`; `--thumbnails /tmp/foo` outputs JPEGs there.

**Technical Notes**
- Ensure backward compatibility with existing flags (`--provider`, `--model`, `--vocab`, `--env`).
- Centralize argument parsing using argparse subroutine; add unit coverage for argument validation.
- Update README/help text with new examples.

---

## Task OAT-003: Provision Orion data directories & seed files
**Priority**: Medium | **Effort**: <1 day | **Type**: chore

**Objective**
- Create `/Orion/{data,proxy,stills,logs}` and place controlled vocab/CSV seeds for immediate testing.

**Work Steps**
1. `sudo mkdir -p /Orion/{data,proxy,stills,logs}` (root may be read-only without elevated perms).
2. Copy template files from repo or latest spec:
   - `/Orion/data/controlled_vocab.yaml`
   - `/Orion/data/tags_sanitized.csv`
   - `/Orion/data/smartbins_intent.csv`
3. Verify with `ls -l /Orion/data` and `shasum -a 256 /Orion/data/*`.

**Notes**
- Current CLI environment lacks write permission to `/Orion`; run locally with sufficient rights.
- Keep seed CSV synchronized with `projects/Orioncommon/assistantreport.md` definitions.

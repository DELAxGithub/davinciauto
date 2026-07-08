# Storyblocks Search Plan

Project: `JAL_雲上書斎_Pilot`

## Download Handling

Chrome downloads stay in the browser's fixed download folder. After visual
selection and download, move the selected files in one batch to:

`/Users/delaxpro/Dropbox/JAL/雲上書斎_Pilot/storyblocks/raw/`

Then copy or symlink approved files into this project:

`/Users/delaxpro/src/20_tools/davinciauto/projects/jal/kumojo-shosai-pilot/assets/storyblocks/raw/`

Keep original filenames until the asset log is written.

## Review Rule

Select fewer, stronger shots. This pilot can work with 10-14 clips.

Avoid:

- visible non-JAL airline logos
- comedy/business-stock acting
- stormy or anxiety-heavy flight imagery
- overly saturated tourism montage
- skyline/travel footage that feels unrelated to flight/time

Prefer:

- calm aircraft window and wing shots
- premium, slow, reflective motion
- clean clocks/maps/timetables
- abstract time-zone or meridian visuals
- subdued colors that can sit under narration and subtitles

## Search Batches

### Batch 1: Signature Cloud / Window

1. `airplane window clouds`
2. `above clouds airplane wing`
3. `cloudscape above clouds`
4. `airplane cabin window cinematic`

Goal: 3-4 candidates.

### Batch 2: Time Hook

1. `wristwatch close up travel`
2. `watch airplane window`
3. `clock close up cinematic`
4. `world clock close up`

Goal: 1-2 candidates.

### Batch 3: Railway / Timetable

1. `train station clock`
2. `railway timetable`
3. `train departure board clock`
4. `railway tracks clock`

Goal: 2 candidates.

### Batch 4: Maps / Time Zones

1. `world map time zones`
2. `globe longitude lines`
3. `world clock map`
4. `prime meridian`
5. `greenwich observatory`

Goal: 2-3 candidates.

### Batch 5: Closing / Wing Shadow

1. `airplane shadow clouds`
2. `wing shadow clouds`
3. `airplane wing sunset clouds`
4. `open book cinematic`
5. `library desk light`

Goal: 2-3 candidates.

## After Download

Create:

`assets/asset_log.csv`

Columns:

`asset_id,shot_id,filename,source,source_url,target_bin,status,notes`

Use statuses:

- `candidate`
- `approved`
- `rejected`
- `placed`


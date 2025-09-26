#!/usr/bin/env python3
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if len(sys.argv) != 4:
    print("Usage: add_markers_from_csv.py <timeline_csv> <imagecuts_csv> <fcpxml>")
    sys.exit(1)

timeline_csv = Path(sys.argv[1])
imagecuts_csv = Path(sys.argv[2])
fcpxml_path = Path(sys.argv[3])

if not timeline_csv.exists() or not imagecuts_csv.exists() or not fcpxml_path.exists():
    print("Error: one or more input files do not exist")
    sys.exit(1)

with timeline_csv.open(newline='', encoding='utf-8') as f:
    timeline_rows = list(csv.DictReader(f))

with imagecuts_csv.open(newline='', encoding='utf-8') as f:
    image_rows = list(csv.DictReader(f))

if not timeline_rows:
    print("Timeline CSV is empty")
    sys.exit(1)

if not image_rows:
    print("Imagecuts CSV is empty")
    sys.exit(1)

# Build lookup of comments/keywords per narration index
FPS = 30
suggestions = []
for row in image_rows:
    try:
        start_sec = float(row.get('start_sec', ''))
    except (TypeError, ValueError):
        start_sec = None
    comment = (row.get('comment') or row.get('Comments') or '').strip()
    keywords = (row.get('keywords') or row.get('Keywords') or '').strip()
    notes = (row.get('notes') or row.get('Notes') or '').strip()
    parts = [p for p in [comment, keywords, notes] if p]
    note_text = ' | '.join(parts)
    if start_sec is None or not note_text:
        continue
    start_frame = int(round(start_sec * FPS))
    suggestions.append({'frame': start_frame, 'text': note_text})

suggestions.sort(key=lambda x: x['frame'])

# Parse XML
ET.register_namespace('', "")
tree = ET.parse(fcpxml_path)
root = tree.getroot()
sequence_elem = root.find('.//sequence')
if sequence_elem is None:
    print("Could not locate <sequence> element in XML")
    sys.exit(1)

# Remove existing Guide markers at sequence level to avoid duplicates
for existing_marker in list(sequence_elem.findall('marker')):
    if existing_marker.findtext('name', '') and existing_marker.findtext('name').startswith('Guide'):
        sequence_elem.remove(existing_marker)

# Collect narration clipitems in order of start frame
clipitems = []
for clip in root.findall('.//clipitem'):
    file_elem = clip.find('file')
    path_elem = file_elem.find('pathurl') if file_elem is not None else None
    path_text = path_elem.text if path_elem is not None else ''
    if 'Narration' in path_text or path_text.endswith('-NA.mp3'):
        start = int(clip.findtext('start', '0'))
        try:
            clip_duration = int(clip.findtext('duration', '0'))
        except ValueError:
            clip_duration = 0
        in_frame = int(clip.findtext('in', '0'))
        out_frame = int(clip.findtext('out', '0'))
        if clip_duration <= 0:
            clip_duration = max(out_frame - in_frame, 1)
        clipitems.append((start, clip, clip_duration))

clipitems.sort(key=lambda x: x[0])

if not clipitems:
    print("No narration clipitems found.")
    sys.exit(1)

def acquire_suggestion(frame: int, window: int = 45):
    if not suggestions:
        return None
    best_idx = None
    best_diff = None
    for idx, entry in enumerate(suggestions):
        diff = abs(entry['frame'] - frame)
        if best_diff is None or diff < best_diff:
            best_idx = idx
            best_diff = diff
    if best_idx is not None and best_diff is not None and best_diff <= window:
        return suggestions.pop(best_idx)
    return None

marker_count = 0
for clip_start, clip, clip_duration in clipitems:
    suggestion = acquire_suggestion(clip_start)
    if not suggestion:
        continue
    note_text = suggestion['text']

    markers_elem = clip.find('markers')
    if markers_elem is None:
        markers_elem = ET.SubElement(clip, 'markers')
    else:
        markers_elem.clear()
    marker = ET.SubElement(markers_elem, 'marker')
    ET.SubElement(marker, 'comment').text = note_text
    ET.SubElement(marker, 'name').text = 'Guide'
    ET.SubElement(marker, 'in').text = '0'
    ET.SubElement(marker, 'out').text = '0'
    ET.SubElement(marker, 'duration').text = str(clip_duration)

    comments_elem = clip.find('comments')
    if comments_elem is None:
        comments_elem = ET.SubElement(clip, 'comments')
    comments_elem.clear()
    comment_block = ET.SubElement(comments_elem, 'comment')
    ET.SubElement(comment_block, 'name').text = 'Guide'
    ET.SubElement(comment_block, 'value').text = note_text

    timeline_marker = ET.SubElement(sequence_elem, 'marker')
    ET.SubElement(timeline_marker, 'comment').text = note_text
    ET.SubElement(timeline_marker, 'name').text = 'Guide'
    ET.SubElement(timeline_marker, 'in').text = str(clip_start)
    ET.SubElement(timeline_marker, 'out').text = str(clip_start)
    ET.SubElement(timeline_marker, 'duration').text = str(clip_duration)

    marker_count += 1

output_path = fcpxml_path.with_name(fcpxml_path.stem + '_with_markers.xml')
tree.write(output_path, encoding='utf-8', xml_declaration=True)
print(f"Wrote {marker_count} markers to {output_path}")

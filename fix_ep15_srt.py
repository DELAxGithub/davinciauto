#!/usr/bin/env python3
"""Fix Ep15 SRT formatting to follow srt_prompt.md rules."""

from pathlib import Path
import re


def parse_srt(srt_path: Path) -> list[dict]:
    """Parse SRT file into entries."""
    with srt_path.open('r', encoding='utf-8') as f:
        content = f.read()

    entries = []
    raw_entries = content.strip().split('\n\n')

    for raw in raw_entries:
        lines = raw.split('\n')
        if len(lines) >= 3:
            seq_num = lines[0].strip()
            timecode = lines[1].strip()
            # Join all text lines and remove internal line breaks
            text = ' '.join(lines[2:]).strip()
            # Clean up multiple spaces
            text = re.sub(r'\s+', ' ', text)
            entries.append({
                'seq': seq_num,
                'timecode': timecode,
                'text': text
            })

    return entries


def apply_srt_rules(text: str) -> str:
    """Apply srt_prompt.md formatting rules.

    Rules:
    - Replace 。with half-width space
    - Replace 、with half-width space
    - Max 60 chars per line, max 2 lines
    - Break at punctuation and word boundaries
    """
    # Rule: Replace punctuation with half-width space
    text = text.replace('。', ' ')
    text = text.replace('、', ' ')
    text = text.replace('！', ' ')
    text = text.replace('？', ' ')

    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    text = text.strip()

    # Rule: Max 60 chars per line, max 2 lines
    # If text fits in 60 chars, return as-is
    if len(text) <= 60:
        return text

    # Split into words by spaces
    if ' ' not in text:
        # No spaces, force break at 60 chars
        if len(text) > 120:
            return text[:60] + '\n' + text[60:120]
        elif len(text) > 60:
            return text[:60] + '\n' + text[60:]
        return text

    # Find optimal break point
    words = text.split(' ')
    line1_parts = []
    line2_parts = []
    line1_len = 0

    for word in words:
        word_len = len(word)

        # Add to line1 if it fits
        if line1_len == 0:
            # First word always goes to line1
            line1_parts.append(word)
            line1_len = word_len
        elif line1_len + 1 + word_len <= 60:
            # Add space + word to line1
            line1_parts.append(word)
            line1_len += 1 + word_len
        else:
            # Goes to line2
            line2_parts.append(word)

    # Build result
    line1 = ' '.join(line1_parts)

    if not line2_parts:
        return line1

    line2 = ' '.join(line2_parts)

    # If line2 is too long, truncate
    if len(line2) > 60:
        line2 = line2[:57] + '...'

    return line1 + '\n' + line2


def format_srt_entry(entry: dict) -> str:
    """Format single SRT entry."""
    text = apply_srt_rules(entry['text'])
    return f"{entry['seq']}\n{entry['timecode']}\n{text}\n"


def main():
    """Fix Ep15 SRT formatting."""
    srt_path = Path('orion/projects/OrionEp15/output/OrionEp15_timecode.srt')

    if not srt_path.exists():
        print(f"❌ SRT not found: {srt_path}")
        return

    print(f"📖 Parsing: {srt_path}")
    entries = parse_srt(srt_path)
    print(f"✅ Parsed {len(entries)} entries")

    print("\n🔧 Applying srt_prompt.md rules:")
    print("   - Replacing punctuation with half-width spaces")
    print("   - Max 60 chars per line, max 2 lines")
    print("   - Breaking at word boundaries")

    # Apply formatting rules
    formatted_entries = []
    for entry in entries:
        formatted_entries.append(format_srt_entry(entry))

    # Write updated SRT
    output_content = '\n'.join(formatted_entries)
    srt_path.write_text(output_content, encoding='utf-8')

    print(f"\n✅ Fixed SRT: {srt_path}")
    print(f"📊 Total entries: {len(entries)}")


if __name__ == '__main__':
    main()

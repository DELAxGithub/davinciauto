#!/usr/bin/env python3
import csv
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print('Usage: python scripts/md_to_csv_verbatim.py <script.md> <out.csv>', file=sys.stderr)
        return 2
    md = pathlib.Path(sys.argv[1])
    out_csv = pathlib.Path(sys.argv[2])
    text = md.read_text(encoding='utf-8')

    lines = [ln.rstrip() for ln in text.splitlines()]
    rows = []
    num = 1
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        # skip empty or section headers like [00:..]
        if not ln or re.match(r"^\[\d{2}:\d{2}-\d{2}:\d{2}\]", ln):
            i += 1
            continue
        # Detect speaker direction e.g. （釈迦の声、...） then next non-empty line is quote
        m = re.match(r'^（([^）]+)）$', ln)
        if m and '声' in m.group(1):
            # extract character name before 'の声'
            char = m.group(1).split('の声', 1)[0]
            # advance to next non-empty
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                quote = lines[j].strip()
                rows.append([
                    f'OrionEp2-{num:03d}-DL.wav', 'OrionEp2', f'{num:03d}', 'DL', char, quote
                ])
                num += 1
                i = j + 1
                continue
        # Otherwise NA line
        rows.append([f'OrionEp2-{num:03d}-NA.wav', 'OrionEp2', f'{num:03d}', 'NA', 'NA', ln])
        num += 1
        i += 1

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['filename','project','number','role','character','text'])
        w.writerows(rows)
    print(f'WROTE: {out_csv}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


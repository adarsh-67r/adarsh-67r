"""Render README section labels as SVG files."""
import sys


def build(label, width=760, height=34):
    label_width = len(label) * 8.2 + 4
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{label} section"><text x="0" y="22" font-family="JetBrains Mono, monospace" font-size="14" fill="#8b949e">{label.lower()}</text><line x1="{label_width}" y1="18" x2="{width}" y2="18" stroke="#30363d"/></svg>'


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit('usage: python3 scripts/make_headings.py "label" output.svg')
    with open(sys.argv[2], "w", encoding="utf-8") as file:
        file.write(build(sys.argv[1]))

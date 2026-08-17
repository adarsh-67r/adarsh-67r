#!/usr/bin/env python3
"""Turn a photo into ascii.svg — a self-typing, monochrome ASCII portrait.

The portrait generator runs locally and is not part of the scheduled stats job.
The explicit u2net_human_seg session avoids rembg's newer, much larger default
model and is appropriate for a human profile photo.
"""
import argparse
import sys

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

RAMP = " .`:-=+*cs#%@"
COLS = 90
CLAHE_CLIP = 3.0
GAMMA = 1.0
CURVE = 1.7
CROP_BOTTOM = 0.0
ROW_RATIO = 0.48

FG_LIGHT = "#6e7681"
FG_DARK = "#c9d1d9"
CHAR_W = 7.74
FONT_SIZE = 12.9
LINE_H = 15
ROW_DELAY = 0.09
FAMILY = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

RMBG_SESSION = new_session("u2net_human_seg")


def prep(path, crop=None):
    """Cut out the background, equalize local contrast, then darken."""
    src = Image.open(path).convert("RGBA")
    if crop:
        src = src.crop(crop)

    cut = remove(src, session=RMBG_SESSION)
    alpha = np.array(cut.split()[-1])

    white = Image.new("RGBA", cut.size, (255, 255, 255, 255))
    gray = np.array(Image.alpha_composite(white, cut).convert("L"))
    gray = cv2.bilateralFilter(gray, 11, 50, 50)
    gray = cv2.createCLAHE(
        clipLimit=CLAHE_CLIP,
        tileGridSize=(8, 8),
    ).apply(gray)
    gray = (255.0 * (gray / 255.0) ** CURVE).astype("uint8")
    gray[alpha < 20] = 255
    return Image.fromarray(gray)


def to_lines(img, cols=COLS, gamma=GAMMA):
    w, h = img.size
    if CROP_BOTTOM:
        img = img.crop((0, 0, w, int(h * (1 - CROP_BOTTOM))))
        w, h = img.size

    rows = int(cols * (h / w) * ROW_RATIO)
    img = img.resize((cols, rows), Image.LANCZOS)
    px = list(img.getdata())
    n = len(RAMP)
    lines = []
    for row in range(rows):
        lines.append("".join(
            RAMP[min(
                n - 1,
                int((1 - px[row * cols + col] / 255.0) ** gamma * n),
            )]
            for col in range(cols)
        ).rstrip())

    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def build_svg(lines, cols=COLS):
    pad = 14
    width = int(cols * CHAR_W + pad * 2)
    height = len(lines) * LINE_H + pad * 2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="{FAMILY}">',
        f'<style>.a{{fill:{FG_LIGHT}}}'
        f'@media(prefers-color-scheme:dark){{.a{{fill:{FG_DARK}}}}}</style>',
    ]

    for index, line in enumerate(lines):
        y = pad + index * LINE_H
        begin = f"{index * ROW_DELAY:.2f}s"
        end = f"{(index + 1) * ROW_DELAY:.2f}s"
        width_px = max(len(line), 1) * CHAR_W
        safe = (
            line.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        parts.append(
            f'<clipPath id="c{index}"><rect x="{pad}" y="{y}" '
            f'height="{LINE_H}" width="0">'
            f'<animate attributeName="width" from="0" to="{width_px:.1f}" '
            f'begin="{begin}" dur="{ROW_DELAY}s" fill="freeze"/>'
            f'</rect></clipPath>'
        )
        parts.append(
            f'<g clip-path="url(#c{index})"><text xml:space="preserve" '
            f'x="{pad}" y="{y + 11.2:.1f}" class="a" '
            f'font-size="{FONT_SIZE}">{safe}</text></g>'
        )
        parts.append(
            f'<rect y="{y + 1}" width="6" height="12" class="a" '
            f'opacity="0"><animate attributeName="x" from="{pad}" '
            f'to="{pad + width_px:.1f}" begin="{begin}" '
            f'dur="{ROW_DELAY}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.8" begin="{begin}"/>'
            f'<set attributeName="opacity" to="0" begin="{end}"/></rect>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("photo")
    parser.add_argument("out", nargs="?", default="ascii.svg")
    parser.add_argument("--crop", help="left,top,right,bottom")
    parser.add_argument("--cols", type=int, default=COLS)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    crop = None
    if args.crop:
        values = [int(value) for value in args.crop.split(",")]
        if len(values) != 4:
            sys.exit("--crop needs four numbers: left,top,right,bottom")
        crop = tuple(values)

    lines = to_lines(prep(args.photo, crop), cols=args.cols)
    if args.preview:
        print("\n".join(lines))

    with open(args.out, "w", encoding="utf-8") as output:
        output.write(build_svg(lines, cols=args.cols))

    print(f"wrote {args.out} — {len(lines)} rows, {args.cols} columns")
    print("next: python3 scripts/embed_portrait_font.py")


if __name__ == "__main__":
    main()

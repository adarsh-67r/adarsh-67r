"""Generate the animated ASCII portrait locally from an image path."""
import sys
from io import BytesIO
import cv2
import numpy as np
from PIL import Image
from rembg import remove

RAMP = " .`:-=+*cs#%@"
COLS = 90
FONT_SIZE = 12.9
CHAR_W = 7.74
STAGGER = 0.09
FILL = "#c9d1d9"


def source(path):
    with open(path, "rb") as file:
        image = Image.open(BytesIO(remove(file.read()))).convert("RGBA")
    background = Image.new("RGBA", image.size, "white")
    background.paste(image, (0, 0), image)
    return background.convert("L")


def process(image):
    array = np.array(image)
    array = cv2.bilateralFilter(array, 9, 60, 60)
    array = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(array)
    return ((array.astype(np.float32) / 255) ** 1.7 * 255).astype(np.uint8)


def ascii_lines(array):
    height, width = array.shape
    rows = int(COLS * height / width * 0.48)
    resized = cv2.resize(array, (COLS, rows), interpolation=cv2.INTER_AREA)
    return [" " + "".join(RAMP[min(int(pixel / 255 * (len(RAMP) - 1)), len(RAMP) - 1)] for pixel in row) for row in resized]


def svg(lines):
    row_height = FONT_SIZE * 1.05
    width = int((COLS + 1) * CHAR_W) + 20
    height = int(len(lines) * row_height) + 20
    definitions = []
    content = []
    for index, line in enumerate(lines):
        clip = f"clip{index}"
        y = 15 + index * row_height
        definitions.append(f'<clipPath id="{clip}"><rect x="10" y="{y - FONT_SIZE}" width="0" height="{row_height}"><animate attributeName="width" from="0" to="{len(line) * CHAR_W}" begin="{index * STAGGER:.2f}s" dur="0.5s" fill="freeze"/></rect></clipPath>')
        content.append(f'<g clip-path="url(#{clip})"><text x="10" y="{y}" font-family="JetBrains Mono, monospace" font-size="{FONT_SIZE}px" xml:space="preserve" fill="{FILL}">{line.replace(" ", "&#160;")}</text></g>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><defs>{"".join(definitions)}</defs>{"".join(content)}</svg>'


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 scripts/make_portrait.py <github-avatar.jpg>")
    with open("ascii.svg", "w", encoding="utf-8") as file:
        file.write(svg(ascii_lines(process(source(sys.argv[1])))))

#!/usr/bin/env python3
"""Subset JetBrains Mono and inline it into generated SVG files.

Requires: pip install fonttools brotli
Expected files: scripts/fonts/JetBrainsMono-Regular.ttf and JetBrainsMono-SemiBold.ttf
"""
import base64
import os
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def subset(source, text, output):
    subprocess.run(["pyftsubset", source, f"--text={text}", "--flavor=woff2", "--layout-features=", "--no-hinting", f"--output-file={output}"], check=True)


def data_uri(path):
    with open(path, "rb") as file:
        return base64.b64encode(file.read()).decode("ascii")


def main():
    regular = os.path.join(FONT_DIR, "JetBrainsMono-Regular.ttf")
    semibold = os.path.join(FONT_DIR, "JetBrainsMono-SemiBold.ttf")
    if not os.path.exists(regular) or not os.path.exists(semibold):
        raise SystemExit("add JetBrainsMono-Regular.ttf and JetBrainsMono-SemiBold.ttf to scripts/fonts first")
    with tempfile.TemporaryDirectory() as temp:
        ramp = os.path.join(temp, "jbmono-ramp.woff2")
        text = os.path.join(temp, "jbmono-text.woff2")
        head = os.path.join(temp, "jbmono-head.woff2")
        subset(regular, " .`:-=+*cs#%@abcdefghijklmnopqrstuvwxyz0123456789·–—", ramp)
        subset(regular, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ·–—%", text)
        subset(semibold, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ·–—%", head)
        for name in ("ascii.svg", "stats.svg", "streak.svg", "langs.svg", "year.svg"):
            path = os.path.join(ROOT, name)
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as file:
                content = file.read()
            if name == "ascii.svg":
                css = f"@font-face{{font-family:ascii;font-style:normal;font-weight:400;src:url(data:font/woff2;base64,{data_uri(ramp)}) format('woff2')}}"
                content = content.replace("<style>", f"<style>{css}", 1).replace("ui-monospace,SFMono-Regular,Menlo,Consolas,monospace", "ascii,monospace")
            else:
                css = f"@font-face{{font-family:JBMono;font-style:normal;font-weight:400;src:url(data:font/woff2;base64,{data_uri(text)}) format('woff2')}}@font-face{{font-family:JBMono;font-style:normal;font-weight:600;src:url(data:font/woff2;base64,{data_uri(head)}) format('woff2')}}"
                content = content.replace("<style>", f"<style>{css}", 1)
            with open(path, "w", encoding="utf-8") as file:
                file.write(content)
            print(f"embedded font in {name}")


if __name__ == "__main__":
    main()

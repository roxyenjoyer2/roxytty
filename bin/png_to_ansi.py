#!/usr/bin/env python3
"""
png_to_ansi.py — Convert a pixel-art PNG (RGBA) into ANSI half-block
terminal art, using truecolor (24-bit) escape codes.

Each terminal cell holds two vertically-stacked source pixels:
  - the TOP pixel becomes the foreground color of a U+2580 '▀' glyph
  - the BOTTOM pixel becomes the background color of that cell

Transparent pixels (alpha == 0) are treated as "no color" — we let the
terminal's default background/foreground show through by skipping the
corresponding color escape for that half.

Usage:
    python3 png_to_ansi.py sprite.png                # print to terminal
    python3 png_to_ansi.py sprite.png -o frame.ans    # save raw ANSI to file
    python3 png_to_ansi.py sprite.png --python-repr   # emit as a Python
                                                        # string literal,
                                                        # handy for embedding
                                                        # frames directly in
                                                        # your CLI's source

Requires: Pillow (pip install pillow)
"""

import argparse
import sys
from PIL import Image

RESET = "\x1b[0m"
ALPHA_THRESHOLD = 128  # pixels with alpha below this are treated as transparent


def fg(r, g, b):
    return f"\x1b[38;2;{r};{g};{b}m"


def bg(r, g, b):
    return f"\x1b[48;2;{r};{g};{b}m"


def get_pixel(img, x, y, width, height):
    """Return (r, g, b, a) for a pixel, or fully transparent if out of bounds
    (needed when height is odd and we pad the last row)."""
    if x >= width or y >= height:
        return (0, 0, 0, 0)
    return img.getpixel((x, y))


def convert(img: Image.Image) -> str:
    img = img.convert("RGBA")
    width, height = img.size

    lines = []
    # Step through rows two at a time (top pixel + bottom pixel per cell)
    for cell_y in range(0, height, 2):
        row_chars = []
        prev_fg = None
        prev_bg = None
        for x in range(width):
            top = get_pixel(img, x, cell_y, width, height)
            bottom = get_pixel(img, x, cell_y + 1, width, height)

            top_opaque = top[3] >= ALPHA_THRESHOLD
            bottom_opaque = bottom[3] >= ALPHA_THRESHOLD

            if not top_opaque and not bottom_opaque:
                # Fully transparent cell — reset colors and emit a space
                if prev_fg is not None or prev_bg is not None:
                    row_chars.append(RESET)
                    prev_fg = prev_bg = None
                row_chars.append(" ")
                continue

            if top_opaque and bottom_opaque:
                cur_fg = top[:3]
                cur_bg = bottom[:3]
                glyph = "\u2580"  # ▀
            elif top_opaque and not bottom_opaque:
                # Only top half visible — draw upper block with no bg
                cur_fg = top[:3]
                cur_bg = None
                glyph = "\u2580"
            else:
                # Only bottom half visible — draw lower block instead,
                # so we only need to set foreground color
                cur_fg = bottom[:3]
                cur_bg = None
                glyph = "\u2584"  # ▄

            # Emit color escapes only when they change (keeps output smaller)
            needed_fg = cur_fg
            needed_bg = cur_bg

            if needed_bg != prev_bg:
                if needed_bg is None:
                    row_chars.append(RESET)
                    prev_fg = None  # reset also clears fg, force re-emit
                else:
                    row_chars.append(bg(*needed_bg))
                prev_bg = needed_bg

            if needed_fg != prev_fg:
                row_chars.append(fg(*needed_fg))
                prev_fg = needed_fg

            row_chars.append(glyph)

        row_chars.append(RESET)
        lines.append("".join(row_chars))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", help="Input PNG file")
    parser.add_argument("-o", "--output", help="Write ANSI output to this file instead of stdout")
    parser.add_argument("--python-repr", action="store_true",
                         help="Emit output wrapped as a Python string literal (for embedding as a frame)")
    args = parser.parse_args()

    try:
        img = Image.open(args.input)
    except Exception as e:
        print(f"Error opening image: {e}", file=sys.stderr)
        sys.exit(1)

    ansi = convert(img)

    if args.python_repr:
        out = "FRAME = " + repr(ansi) + "\n"
    else:
        out = ansi + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(out)


if __name__ == "__main__":
    main()

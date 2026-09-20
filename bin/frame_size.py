#!/usr/bin/env python3
"""
frame_size.py — Print "WIDTH HEIGHT" (in terminal cells) for a set of
.ans frame files, computed as the max across all frames in the directory
(frames should normally all share the same dimensions, but max is a
safe fallback if they don't).

Width = length of the longest visible-character row (ANSI escape codes
don't count, since they're zero-width).
Height = number of lines in the file.

Usage:
    python3 frame_size.py <frames_dir>
Prints: "<width> <height>"
"""

import glob
import os
import re
import sys

# Strips ANSI escape sequences to get the true visible character count.
ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def visible_width(line: str) -> int:
    return len(ANSI_ESCAPE.sub("", line))


def main():
    if len(sys.argv) != 2:
        print("Usage: frame_size.py <frames_dir>", file=sys.stderr)
        sys.exit(1)

    frames_dir = sys.argv[1]
    paths = sorted(glob.glob(os.path.join(frames_dir, "**", "*.ans"), recursive=True))
    if not paths:
        print("No .ans files found", file=sys.stderr)
        sys.exit(1)

    max_width = 0
    max_height = 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()
        max_height = max(max_height, len(lines))
        for line in lines:
            max_width = max(max_width, visible_width(line))

    print(f"{max_width} {max_height}")


if __name__ == "__main__":
    main()

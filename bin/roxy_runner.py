#!/usr/bin/env python3
"""
roxy_runner.py — Displays Roxy's sprite animations in the current terminal
pane and reacts to shell events (command started / finished).

Frame layout (each folder holds .ans files, played in filename order):
    frames/idle/      looped while nothing happens
    frames/cast_in/   transition into casting pose, played once when a command starts
    frames/cast/      looped while the command keeps running (after cast_in)
    frames/success/   played once after a command exits 0
    frames/fail/      played once after a command exits non-zero
Missing folders are simply skipped (cast_in alone holds its last frame until
the command finishes; cast alone loops right away). Legacy layout (.ans files directly in
frames/) is still used as the idle loop.

Per-frame duration is encoded in the filename: name-1100ms.ans

Events arrive as signals from roxy_hook.sh (via the PID file):
    SIGUSR1  command started   -> interrupt whatever is playing, start cast
    SIGUSR2  command finished  -> exit code read from roxy.rc, play result

Usage:
    python3 roxy_runner.py --frames-dir ../frames --fps 3
Ctrl+C to stop.
"""

import argparse
import glob
import os
import re
import select
import signal
import sys
import time

CLEAR_SCREEN = "\x1b[2J"
CURSOR_HOME = "\x1b[H"
HIDE_CURSOR = "\x1b[?25l"
SHOW_CURSOR = "\x1b[?25h"

RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PID_FILE = os.path.join(RUNTIME_DIR, "roxy.pid")
RC_FILE = os.path.join(RUNTIME_DIR, "roxy.rc")

STATES = ("idle", "cast_in", "cast", "success", "fail")
CASTING = ("cast_in", "cast")
DURATION_SUFFIX_RE = re.compile(r"-(\d+)ms$")


def parse_duration_ms(path: str):
    stem = os.path.splitext(os.path.basename(path))[0]
    match = DURATION_SUFFIX_RE.search(stem)
    return int(match.group(1)) / 1000.0 if match else None


def load_frames_from(directory: str, default_interval: float):
    frames = []  # list of (content, duration_seconds)
    for path in sorted(glob.glob(os.path.join(directory, "*.ans"))):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        duration = parse_duration_ms(path)
        frames.append((content, duration if duration is not None else default_interval))
    return frames


def load_animations(frames_dir: str, default_interval: float):
    anims = {s: load_frames_from(os.path.join(frames_dir, s), default_interval) for s in STATES}
    if not anims["idle"]:  # legacy flat layout
        anims["idle"] = load_frames_from(frames_dir, default_interval)
    if not anims["idle"]:
        print(f"No idle frames found in {frames_dir}", file=sys.stderr)
        sys.exit(1)
    if anims["cast_in"] and not anims["cast"]:
        anims["cast"] = [anims["cast_in"][-1]]  # hold the pose until the command ends
    return anims


def install_signals() -> int:
    """Route USR1/USR2 into a pipe so select() wakes up instantly.
    Returns the read end of the pipe."""
    r, w = os.pipe()
    os.set_blocking(r, False)
    os.set_blocking(w, False)
    signal.set_wakeup_fd(w)  # writes the signal number as one byte
    for sig in (signal.SIGUSR1, signal.SIGUSR2):
        signal.signal(sig, lambda *_: None)  # a handler must exist for the fd to fire
    for sig in (signal.SIGTERM, signal.SIGHUP):  # tmux kills panes with SIGHUP
        signal.signal(sig, lambda *_: sys.exit(0))  # so the PID file gets cleaned up
    return r


def wait(wake_fd: int, timeout: float):
    """Sleep up to `timeout`, but return early with any signal numbers received."""
    ready, _, _ = select.select([wake_fd], [], [], timeout)
    if not ready:
        return []
    try:
        return list(os.read(wake_fd, 64))
    except BlockingIOError:
        return []


def read_exit_code() -> int:
    try:
        with open(RC_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def run(frames_dir: str, default_interval: float):
    anims = load_animations(frames_dir, default_interval)
    counts = {s: len(f) for s, f in anims.items()}
    print(f"Loaded frames: {counts}", file=sys.stderr)
    time.sleep(0.5)

    wake_fd = install_signals()
    with open(PID_FILE, "w") as f:
        f.write(f"{os.getpid()}\n")

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    state = "idle"
    result = None  # outcome waiting for the current cast pass to finish

    try:
        while True:
            next_state = None
            for content, duration in anims[state]:
                sys.stdout.write(CLEAR_SCREEN + CURSOR_HOME + content)
                sys.stdout.flush()

                # Signals from a fast command can arrive together in any order,
                # so treat the batch as a set: "started" first, then "finished".
                events = wait(wake_fd, duration)
                if signal.SIGUSR1 in events:  # command started
                    result = None
                    if state not in CASTING:
                        start = "cast_in" if anims["cast_in"] else ("cast" if anims["cast"] else None)
                        next_state = start
                if signal.SIGUSR2 in events:  # command finished
                    outcome = "fail" if read_exit_code() else "success"
                    if state in CASTING or next_state in CASTING:
                        result = outcome  # let the current cast pass finish first
                    elif anims[outcome]:
                        next_state = outcome
                if next_state:
                    break  # interrupt immediately

            # end of a pass (or interrupted)
            if next_state:
                state = next_state
            elif state in CASTING:
                if result:
                    state = result if anims[result] else "idle"
                    result = None
                elif state == "cast_in":
                    state = "cast"  # intro done -> loop while command runs
                # else (state == "cast"): command still running, loop again
            elif state != "idle":
                state = "idle"  # success/fail played once
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        try:
            os.unlink(PID_FILE)
        except OSError:
            pass
        sys.stdout.write(SHOW_CURSOR + "\x1b[0m")
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frames-dir", default=os.path.join(os.path.dirname(__file__), "..", "frames"),
                        help="Frames directory (default: ../frames relative to this script)")
    parser.add_argument("--interval", type=float, default=None,
                        help="Default seconds/frame for files without -<N>ms suffix (default: 0.35)")
    parser.add_argument("--fps", type=float, default=None, help="Default frames per second (alternative to --interval)")
    args = parser.parse_args()

    if args.fps:
        default_interval = 1.0 / args.fps
    elif args.interval:
        default_interval = args.interval
    else:
        default_interval = 0.35

    run(os.path.abspath(args.frames_dir), default_interval)


if __name__ == "__main__":
    main()

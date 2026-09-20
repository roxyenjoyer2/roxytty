# roxytty

An animated pixel-art Roxy Migurdia living in the corner of your terminal.
She idles while you work, casts a spell while a command runs, and reacts
when it succeeds or fails.

Runs in a dedicated tmux pane, playing pre-rendered ANSI half-block frames
(24-bit truecolor, two stacked source pixels per terminal cell).

## Requirements

- Python 3
- tmux
- bash + [bash-preexec](https://github.com/rcaloras/bash-preexec) (for command reactions)
- A truecolor terminal
- [Pillow](https://pypi.org/project/pillow/) (only to convert new sprites)

## Usage

```bash
./bin/start_roxy_session.sh            # session name defaults to "main"
./bin/start_roxy_session.sh mysession  # custom session name
```

Use this instead of plain `tmux` / `tmux attach`. Roxy gets her own pane on
the right, sized automatically to the frame width.

### Command reactions (optional)

Add to the **end** of `~/.bashrc`, after `bash-preexec` is sourced:

```bash
source /path/to/roxytty/bin/roxy_hook.sh
```

Without it, Roxy just idles.

## Animation flow

```
Enter -> cast_in (once) -> cast (loops while command runs)
      -> command ends -> current pass finishes
      -> success / fail (once, by exit code) -> idle
```

- Very fast commands: intro, then result directly (no loop).
- Only `cast_in` present: its last frame is held while the command runs.
- Only `cast` present: it loops immediately.
- Missing folders are skipped. Flat `frames/*.ans` still works as idle.

## Frames

```
frames/
  idle/       loops when nothing is running
  cast_in/    plays once when a command starts
  cast/       loops while a command runs
  success/    plays once after exit code 0
  fail/       plays once after a non-zero exit code
```

Frames play in filename-sorted order. Per-frame duration is set by a
`-<N>ms` filename suffix (e.g. `cast2-400ms.ans`); files without one use the
default (`--fps` / `--interval` on `roxy_runner.py`, 0.35 s).

### Making your own

Draw a pixel-art PNG with a transparent background, then convert:

```bash
python3 bin/png_to_ansi.py sprite.png -o frames/idle/idle1-1100ms.ans
```

## How it works

`roxy_hook.sh` uses bash-preexec to signal the runner: `SIGUSR1` on command
start, `SIGUSR2` on finish (exit code passed via `roxy.rc`). The runner's PID
lives in `roxy.pid` (in `$XDG_RUNTIME_DIR` or `/tmp`). Signals interrupt the
current frame's sleep immediately, so reactions feel instant.

## Layout

```
bin/
  start_roxy_session.sh   tmux launcher
  roxy_runner.py          state machine, signal-driven
  roxy_hook.sh            bash-preexec hooks
  png_to_ansi.py          PNG -> ANSI converter
  frame_size.py           pane size detection
frames/                   .ans frames (see above)
```

## Known limitations

- One Roxy at a time (global PID file).
- Every bash shell triggers her while the runner is alive, not just the one in the tmux session.
- Commands aborted with Ctrl+C count as failures (exit 130).
- A stale PID file after `SIGKILL` could signal a recycled PID (the runner cleans up on SIGTERM/SIGHUP/Ctrl+C).

## License

- **Code**: [MIT](LICENSE).
- **Sprite frames** (`frames/`): fan art, edited from an anime screenshot.
  Roxy Migurdia and *Mushoku Tensei* are © their respective owners
  (Rifujin na Magonote / Shirotaka / Studio Bind and associated rights
  holders). The frames are **not** covered by the MIT license, are
  non-commercial, and will be removed on request.

## Credits

Code written with Claude (Anthropic).

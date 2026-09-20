#!/usr/bin/env bash
# start_roxy_session.sh
#
# Launches (or attaches to) a tmux session with a dedicated Roxy pane
# in the bottom-right corner, running the idle-loop sprite animation.
#
# Usage:
#   ./start_roxy_session.sh              # session name defaults to "main"
#   ./start_roxy_session.sh mysession    # custom session name
#
# Run this instead of plain `tmux` / `tmux attach` to get Roxy included.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROXY_DIR="$(dirname "$SCRIPT_DIR")"          # roxy-cli/ (parent of bin/)
FRAMES_DIR="$ROXY_DIR/frames"
RUNNER="$SCRIPT_DIR/roxy_runner.py"

SESSION_NAME="${1:-main}"

# Roxy pane size — auto-detected from the frames' actual dimensions
# (max width/height across all .ans files), so this stays correct as you
# add or replace sprites without editing this script.
FRAME_SIZE_OUTPUT="$(python3 "$SCRIPT_DIR/frame_size.py" "$FRAMES_DIR")"
ROXY_PANE_WIDTH="${FRAME_SIZE_OUTPUT%% *}"
ROXY_PANE_HEIGHT="${FRAME_SIZE_OUTPUT##* }"
echo "Roxy pane size: ${ROXY_PANE_WIDTH} cols x ${ROXY_PANE_HEIGHT} rows" >&2

if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Session '$SESSION_NAME' already exists — attaching."
    exec tmux attach -t "$SESSION_NAME"
fi

# Create a new detached session, explicitly sized to match the
# attaching terminal (tmux can't know this yet for a plain -d session,
# which is why the split below used to get sized against a stale
# default instead of your real terminal width).
tmux new-session -d -s "$SESSION_NAME" -x "$(tput cols)" -y "$(tput lines)"

# Apply seamless look: no status bar, invisible pane borders.
tmux set-option -t "$SESSION_NAME" status off
tmux set-option -t "$SESSION_NAME" pane-border-style "fg=black,bg=black"
tmux set-option -t "$SESSION_NAME" pane-active-border-style "fg=black,bg=black"

# Single split: carve Roxy's corner directly off the main pane, full
# height, exactly ROXY_PANE_WIDTH columns wide. Two panes total — your
# one prompt, and Roxy.
tmux split-window -h -l "$ROXY_PANE_WIDTH" -t "$SESSION_NAME:0.0" \
    "python3 '$RUNNER' --frames-dir '$FRAMES_DIR'"

# Return focus to your main working pane.
tmux select-pane -t "$SESSION_NAME:0.0"

exec tmux attach -t "$SESSION_NAME"

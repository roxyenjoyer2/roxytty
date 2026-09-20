# roxy_hook.sh — tells roxy_runner.py when a command starts/finishes.
#
# Add to the END of ~/.bashrc, in this order:
#   source ~/.bash-preexec.sh                      # https://github.com/rcaloras/bash-preexec
#   source /path/to/roxy-cli/bin/roxy_hook.sh

_roxy_dir="${XDG_RUNTIME_DIR:-/tmp}"
_roxy_pidfile="$_roxy_dir/roxy.pid"
_roxy_rcfile="$_roxy_dir/roxy.rc"
_roxy_ran=0

_roxy_signal() {
    local pid
    [[ -r $_roxy_pidfile ]] || return 0
    read -r pid < "$_roxy_pidfile"; [[ -n $pid ]] || return 0
    kill -"$1" "$pid" 2>/dev/null
    return 0
}

roxy_preexec() {            # before a command runs
    _roxy_ran=1
    _roxy_signal USR1
}

roxy_precmd() {             # before the next prompt
    local rc=$?
    (( _roxy_ran )) || return 0   # first prompt / empty Enter: nothing ran
    _roxy_ran=0
    printf '%s' "$rc" > "$_roxy_rcfile" 2>/dev/null
    _roxy_signal USR2
}

preexec_functions+=(roxy_preexec)
precmd_functions+=(roxy_precmd)

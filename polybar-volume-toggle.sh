#!/usr/bin/env bash
# polybar-volume-toggle.sh
# Abre/fecha a janela flutuante de controle de áudio (GTK3).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$(command -v python3)"

PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-volume.pid"

# Fecha se já estiver aberta
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid"
        rm -f "$PID_FILE"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Abre a janela GTK em background
NO_AT_BRIDGE=1 "$PYTHON" "$SCRIPT_DIR/janela_audio.py" &
echo "$!" > "$PID_FILE"

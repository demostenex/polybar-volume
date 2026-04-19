#!/usr/bin/env bash
# polybar-volume-toggle.sh
# Abre/fecha a janela yad de seleção de sink de áudio.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-volume.pid"

# Se a janela já está aberta, fecha
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid"
        rm -f "$PID_FILE"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# Lista de sinks via Python
SINKS=$("$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode list-sinks 2>/dev/null)

_abrir_janela() {
    if [ -z "$SINKS" ]; then
        yad --title="Áudio" --text="Nenhum sink encontrado." \
            --button="Fechar:1" --width=300 --timeout=5 \
            --fixed --mouse --skip-taskbar --on-top --sticky
        exit 1
    fi

    ESCOLHA=$(echo "$SINKS" | yad \
        --title="Saída de Áudio" \
        --list \
        --column="#" \
        --column="Dispositivo" \
        --column="Ativo" \
        --width=480 \
        --height=300 \
        --print-column=2 \
        --fixed \
        --mouse \
        --skip-taskbar \
        --on-top \
        --sticky \
        --button="Usar este:0" \
        --button="Fechar:1" \
        2>/dev/null) || STATUS=$?
    STATUS="${STATUS:-0}"

    # Botão "Usar este" retorna 0
    if [ "$STATUS" -eq 0 ] && [ -n "$ESCOLHA" ]; then
        # yad retorna a descrição com pipes: |Descrição|
        DESC=$(echo "$ESCOLHA" | tr -d '|\n')
        INDEX=$(echo "$SINKS" | awk -F'\t' -v desc="$DESC" '$2 == desc {print $1}')
        if [ -n "$INDEX" ]; then
            SINK_NAME=$(pactl list sinks short | awk -v idx="$INDEX" '$1 == idx {print $2}')
            if [ -n "$SINK_NAME" ]; then
                "$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode set-sink --sink "$SINK_NAME"
            fi
        fi
    fi
}

_abrir_janela &
JANELA_PID=$!
echo "$JANELA_PID" > "$PID_FILE"

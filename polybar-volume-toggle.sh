#!/usr/bin/env bash
# polybar-volume-toggle.sh
# Abre/fecha a janela de controle de áudio (yad notebook: Saídas + Entradas + Volume).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$SCRIPT_DIR/.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

PID_FILE="${XDG_RUNTIME_DIR:-/tmp}/polybar-volume.pid"

# ------------------------------------------------------------------
# Fecha janela se já estiver aberta
# ------------------------------------------------------------------
if [ -f "$PID_FILE" ]; then
    old_pid=$(cat "$PID_FILE")
    if kill -0 "$old_pid" 2>/dev/null; then
        kill "$old_pid"
        rm -f "$PID_FILE"
        exit 0
    fi
    rm -f "$PID_FILE"
fi

# ------------------------------------------------------------------
# Coleta dados
# ------------------------------------------------------------------
SINKS=$("$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode list-sinks 2>/dev/null)
SOURCES=$("$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode list-sources 2>/dev/null)
VOLUME=$("$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode module 2>/dev/null | sed 's/%{[^}]*}//g' | tr -d ' ')

_abrir_janela() {
    local KEY=$RANDOM

    # ---- Aba 1: Saídas ----
    local sink_rows=()
    if [ -n "$SINKS" ]; then
        while IFS=$'\t' read -r idx desc ativo; do
            sink_rows+=("$idx" "$desc" "$ativo")
        done <<< "$SINKS"
    fi

    # ---- Aba 2: Entradas ----
    local source_rows=()
    if [ -n "$SOURCES" ]; then
        while IFS=$'\t' read -r idx desc ativo; do
            source_rows+=("$idx" "$desc" "$ativo")
        done <<< "$SOURCES"
    fi

    # ---- Aba 3: Volume ----
    local vol_pct
    vol_pct=$(pactl get-sink-volume @DEFAULT_SINK@ 2>/dev/null | grep -oP '\d+(?=%)' | head -1)
    vol_pct="${vol_pct:-50}"

    # Inicia as abas em paralelo (yad notebook)
    (
        [ ${#sink_rows[@]} -gt 0 ] && \
            printf '%s\n' "${sink_rows[@]}" | \
            yad --plug="$KEY" --tabnum=1 \
                --list \
                --column="#:HD" \
                --column="Dispositivo de Saída" \
                --column="Ativo" \
                --print-column=1 \
                2>/dev/null
    ) &

    (
        [ ${#source_rows[@]} -gt 0 ] && \
            printf '%s\n' "${source_rows[@]}" | \
            yad --plug="$KEY" --tabnum=2 \
                --list \
                --column="#:HD" \
                --column="Dispositivo de Entrada" \
                --column="Ativo" \
                --print-column=1 \
                2>/dev/null
    ) &

    yad --plug="$KEY" --tabnum=3 \
        --form \
        --field="Volume (%):NUM" "$vol_pct!0..150!5" \
        2>/dev/null &

    # ---- Janela principal (notebook) ----
    local resultado
    resultado=$(yad --notebook \
        --key="$KEY" \
        --tab="🔊 Saídas" \
        --tab="🎤 Entradas" \
        --tab="🎚 Volume" \
        --title="Controle de Áudio" \
        --width=500 --height=320 \
        --fixed \
        --mouse \
        --skip-taskbar \
        --on-top \
        --sticky \
        --button="Usar este:0" \
        --button="Fechar:1" \
        2>/dev/null) || STATUS=$?
    STATUS="${STATUS:-0}"

    if [ "$STATUS" -ne 0 ]; then
        return
    fi

    # resultado formato: "tabnum|dado1|dado2|..."
    local tab_num
    tab_num=$(echo "$resultado" | cut -d'|' -f1)

    case "$tab_num" in
        1)  # Aba Saídas — usar sink selecionado
            local idx
            idx=$(echo "$resultado" | cut -d'|' -f2)
            if [ -n "$idx" ] && [ "$idx" != "" ]; then
                local sink_name
                sink_name=$(pactl list sinks short | awk -v i="$idx" '$1 == i {print $2}')
                [ -n "$sink_name" ] && \
                    "$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode set-sink --sink "$sink_name"
            fi
            ;;
        2)  # Aba Entradas — usar source selecionado
            local idx
            idx=$(echo "$resultado" | cut -d'|' -f2)
            if [ -n "$idx" ] && [ "$idx" != "" ]; then
                local source_name
                source_name=$(pactl list sources short | awk -v i="$idx" '$1 == i {print $2}')
                [ -n "$source_name" ] && \
                    "$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode set-source --source "$source_name"
            fi
            ;;
        3)  # Aba Volume — aplicar nível
            local novo_vol
            novo_vol=$(echo "$resultado" | cut -d'|' -f2 | cut -d',' -f1 | tr -d ' ')
            if [[ "$novo_vol" =~ ^[0-9]+$ ]]; then
                "$PYTHON" "$SCRIPT_DIR/volume_polybar.py" --mode volume-up --step 0
                pactl set-sink-volume @DEFAULT_SINK@ "${novo_vol}%"
            fi
            ;;
    esac
}

_abrir_janela &
JANELA_PID=$!
echo "$JANELA_PID" > "$PID_FILE"

#!/usr/bin/env python3
"""
volume_polybar.py
Entry point do módulo de volume para o Polybar.
"""
from __future__ import annotations

import argparse
import sys

from adaptador_audio import AdaptadorPactl

# ---------------------------------------------------------------------------
# Ícones e cores (Nerd Font / Material Design Icons)
# ---------------------------------------------------------------------------

ICONE_MUDO = "\U000f075f"        # 󰝟  cinza
ICONE_BT = "\U000f032b"          # 󰋋  verde
ICONE_VOL_BAIXO = "\U000f057f"   # 󰕿  azul  (0–33%)
ICONE_VOL_MEDIO = "\U000f0580"   # 󰖀  azul  (34–66%)
ICONE_VOL_ALTO = "\U000f057e"    # 󰕾  azul  (67–100%)
ICONE_HDMI = "\U000f04d3"        # 󰓃  roxo

COR_CINZA = "#888888"
COR_VERDE = "#00cc44"
COR_AZUL = "#5599ff"
COR_ROXO = "#aa55ff"


def _icone_e_cor(tipo: str, volume: int, mudo: bool) -> tuple[str, str]:
    if mudo:
        return ICONE_MUDO, COR_CINZA
    if tipo == "bluetooth":
        return ICONE_BT, COR_VERDE
    if tipo in ("hdmi", "loopback"):
        return ICONE_HDMI, COR_ROXO
    # analógico ou outro
    if volume <= 33:
        icone = ICONE_VOL_BAIXO
    elif volume <= 66:
        icone = ICONE_VOL_MEDIO
    else:
        icone = ICONE_VOL_ALTO
    return icone, COR_AZUL


# ---------------------------------------------------------------------------
# Modos
# ---------------------------------------------------------------------------

def modo_module(adaptador: AdaptadorPactl) -> None:
    """Saída de uma linha para o Polybar: ícone colorido + volume%."""
    try:
        tipo = adaptador.detectar_tipo(adaptador.get_default_sink())
        volume = adaptador.get_volume()
        mudo = adaptador.is_muted()
        icone, cor = _icone_e_cor(tipo, volume, mudo)
        # Polybar aceita %{F#cor} para colorir
        print(f"%{{F{cor}}}{icone}%{{F-}} {volume}% ")
    except Exception as exc:  # noqa: BLE001
        print(f"ERR {exc}", file=sys.stderr)
        print("\U000f075f ERR ")


def modo_list_sinks(adaptador: AdaptadorPactl) -> None:
    """Saída tab-separada para o yad: index \\t descrição \\t ativo."""
    try:
        default = adaptador.get_default_sink()
        sinks = adaptador.listar_sinks()
        for s in sinks:
            ativo = "✔" if s["name"] == default else " "
            print(f"{s['index']}\t{s['description']}\t{ativo}")
    except Exception as exc:  # noqa: BLE001
        print(f"ERR {exc}", file=sys.stderr)
        sys.exit(1)


def modo_toggle_mute(adaptador: AdaptadorPactl) -> None:
    adaptador.toggle_mute()


def modo_volume_up(adaptador: AdaptadorPactl, step: int = 5) -> None:
    adaptador.volume_up(step)


def modo_volume_down(adaptador: AdaptadorPactl, step: int = 5) -> None:
    adaptador.volume_down(step)


def modo_set_sink(adaptador: AdaptadorPactl, sink_name: str) -> None:
    adaptador.set_default_sink(sink_name)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

MODOS = ["module", "list-sinks", "toggle-mute", "volume-up", "volume-down", "set-sink"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Módulo de volume para Polybar")
    parser.add_argument(
        "--mode",
        choices=MODOS,
        default="module",
        help="Modo de operação",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=5,
        help="Passo de ajuste de volume (padrão: 5%%)",
    )
    parser.add_argument(
        "--sink",
        type=str,
        default="",
        help="Nome do sink (para --mode set-sink)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    adaptador = AdaptadorPactl()

    mapa = {
        "module": lambda: modo_module(adaptador),
        "list-sinks": lambda: modo_list_sinks(adaptador),
        "toggle-mute": lambda: modo_toggle_mute(adaptador),
        "volume-up": lambda: modo_volume_up(adaptador, args.step),
        "volume-down": lambda: modo_volume_down(adaptador, args.step),
        "set-sink": lambda: modo_set_sink(adaptador, args.sink),
    }

    mapa[args.mode]()


if __name__ == "__main__":
    main()

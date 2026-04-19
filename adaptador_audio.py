"""
adaptador_audio.py
Responsabilidade única: comunicação com PulseAudio/PipeWire via pactl.
"""
from __future__ import annotations

import re
import subprocess
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Protocolo — permite substituição por mock nos testes
# ---------------------------------------------------------------------------

@runtime_checkable
class AdaptadorAudioProtocol(Protocol):
    def listar_sinks(self) -> list[dict]: ...
    def get_default_sink(self) -> str: ...
    def set_default_sink(self, sink_name: str) -> None: ...
    def get_volume(self) -> int: ...
    def set_volume(self, pct: int) -> None: ...
    def volume_up(self, step: int = 5) -> None: ...
    def volume_down(self, step: int = 5) -> None: ...
    def toggle_mute(self) -> None: ...
    def is_muted(self) -> bool: ...
    def detectar_tipo(self, sink_name: str) -> str: ...


# ---------------------------------------------------------------------------
# Implementação real (pactl)
# ---------------------------------------------------------------------------

class AdaptadorPactl:
    """Implementação via pactl (PulseAudio / PipeWire-pulse)."""

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _run(self, *args: str) -> str:
        result = subprocess.run(
            ["pactl", *args],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()

    def _parse_volume_pct(self, volume_str: str) -> int:
        """Extrai percentual do campo Volume do pactl (ex: '50%')."""
        match = re.search(r"(\d+)%", volume_str)
        return int(match.group(1)) if match else 0

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def listar_sinks(self) -> list[dict]:
        """Retorna lista de sinks com index, name, description, volume_pct, muted, state, tipo."""
        raw = self._run("list", "sinks")
        sinks: list[dict] = []
        current: dict | None = None

        for line in raw.splitlines():
            # Novo bloco de sink
            m = re.match(r"^Sink #(\d+)", line)
            if m:
                if current:
                    sinks.append(current)
                current = {
                    "index": int(m.group(1)),
                    "name": "",
                    "description": "",
                    "volume_pct": 0,
                    "muted": False,
                    "state": "",
                    "tipo": "",
                }
                continue

            if current is None:
                continue

            line_s = line.strip()

            if line_s.startswith("Name:"):
                current["name"] = line_s.split(":", 1)[1].strip()
                current["tipo"] = self.detectar_tipo(current["name"])

            elif line_s.startswith("Description:"):
                current["description"] = line_s.split(":", 1)[1].strip()

            elif line_s.startswith("State:"):
                current["state"] = line_s.split(":", 1)[1].strip()

            elif line_s.startswith("Mute:"):
                current["muted"] = line_s.split(":", 1)[1].strip().lower() == "yes"

            elif line_s.startswith("Volume:") and "front-left" in line_s:
                current["volume_pct"] = self._parse_volume_pct(line_s)

        if current:
            sinks.append(current)

        return sinks

    def get_default_sink(self) -> str:
        return self._run("get-default-sink")

    def set_default_sink(self, sink_name: str) -> None:
        self._run("set-default-sink", sink_name)

    def get_volume(self) -> int:
        raw = self._run("get-sink-volume", "@DEFAULT_SINK@")
        return self._parse_volume_pct(raw)

    def set_volume(self, pct: int) -> None:
        pct = max(0, min(150, pct))
        self._run("set-sink-volume", "@DEFAULT_SINK@", f"{pct}%")

    def volume_up(self, step: int = 5) -> None:
        self._run("set-sink-volume", "@DEFAULT_SINK@", f"+{step}%")

    def volume_down(self, step: int = 5) -> None:
        self._run("set-sink-volume", "@DEFAULT_SINK@", f"-{step}%")

    def toggle_mute(self) -> None:
        self._run("set-sink-mute", "@DEFAULT_SINK@", "toggle")

    def is_muted(self) -> bool:
        raw = self._run("get-sink-mute", "@DEFAULT_SINK@")
        return raw.strip().lower().endswith("yes")

    def detectar_tipo(self, sink_name: str) -> str:
        name = sink_name.lower()
        if "bluez" in name:
            return "bluetooth"
        if "snd_aloop" in name or "loopback" in name:
            return "loopback"
        if "hdmi" in name:
            return "hdmi"
        if "analog" in name or "alsa_output" in name:
            return "analog"
        return "outro"

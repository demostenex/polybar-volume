"""
tests/test_adaptador.py
Testes unitários para adaptador_audio.py (mock de subprocess).
"""
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from adaptador_audio import AdaptadorPactl  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

PACTL_LIST_SINKS = """\
Sink #0
\tState: SUSPENDED
\tName: alsa_output.pci-0000_00_1b.0.analog-stereo
\tDescription: Built-in Audio Analog Stereo
\tMute: no
\t\tVolume: front-left: 32768 /  50% / -18.06 dB,   front-right: 32768 /  50% / -18.06 dB
Sink #1
\tState: RUNNING
\tName: bluez_output.55_FB_BA_A6_E7_D2.1
\tDescription: C01 Headset
\tMute: no
\t\tVolume: front-left: 65536 / 100% /   0.00 dB,   front-right: 65536 / 100% /   0.00 dB
"""


@pytest.fixture()
def adaptador():
    return AdaptadorPactl()


def mock_run(output: str):
    """Retorna um mock para subprocess.run com stdout preset."""
    m = MagicMock()
    m.stdout = output
    return m


# ---------------------------------------------------------------------------
# detectar_tipo
# ---------------------------------------------------------------------------

class TestDetectarTipo:
    def test_bluetooth(self, adaptador):
        assert adaptador.detectar_tipo("bluez_output.55_FB_BA_A6.1") == "bluetooth"

    def test_analogico(self, adaptador):
        assert adaptador.detectar_tipo("alsa_output.pci-0000_00_1b.0.analog-stereo") == "analog"

    def test_loopback(self, adaptador):
        assert adaptador.detectar_tipo("alsa_output.platform-snd_aloop.0.stereo") == "loopback"

    def test_hdmi(self, adaptador):
        assert adaptador.detectar_tipo("alsa_output.pci-0000_00_03.0.hdmi-stereo") == "hdmi"

    def test_outro(self, adaptador):
        assert adaptador.detectar_tipo("virtual_sink_xpto") == "outro"


# ---------------------------------------------------------------------------
# listar_sinks
# ---------------------------------------------------------------------------

class TestListarSinks:
    def test_dois_sinks(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SINKS)):
            sinks = adaptador.listar_sinks()
        assert len(sinks) == 2

    def test_sink_analogico(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SINKS)):
            sinks = adaptador.listar_sinks()
        s = sinks[0]
        assert s["index"] == 0
        assert s["name"] == "alsa_output.pci-0000_00_1b.0.analog-stereo"
        assert s["description"] == "Built-in Audio Analog Stereo"
        assert s["volume_pct"] == 50
        assert s["muted"] is False
        assert s["tipo"] == "analog"

    def test_sink_bluetooth(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SINKS)):
            sinks = adaptador.listar_sinks()
        s = sinks[1]
        assert s["tipo"] == "bluetooth"
        assert s["volume_pct"] == 100

    def test_sem_sinks(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")):
            sinks = adaptador.listar_sinks()
        assert sinks == []


# ---------------------------------------------------------------------------
# get_default_sink
# ---------------------------------------------------------------------------

class TestGetDefaultSink:
    def test_retorna_nome(self, adaptador):
        with patch("adaptador_audio.subprocess.run",
                   return_value=mock_run("bluez_output.55_FB_BA_A6_E7_D2.1\n")):
            assert adaptador.get_default_sink() == "bluez_output.55_FB_BA_A6_E7_D2.1"


# ---------------------------------------------------------------------------
# set_default_sink
# ---------------------------------------------------------------------------

class TestSetDefaultSink:
    def test_chama_pactl(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.set_default_sink("alsa_output.pci-0000_00_1b.0.analog-stereo")
        mock.assert_called_once()
        cmd = mock.call_args[0][0]
        assert cmd == ["pactl", "set-default-sink", "alsa_output.pci-0000_00_1b.0.analog-stereo"]


# ---------------------------------------------------------------------------
# get_volume
# ---------------------------------------------------------------------------

class TestGetVolume:
    def test_extrai_percentual(self, adaptador):
        raw = "Volume: front-left: 32768 /  50% / -18.06 dB,   front-right: 32768 /  50% / -18.06 dB"
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(raw)):
            assert adaptador.get_volume() == 50

    def test_volume_zero(self, adaptador):
        raw = "Volume: front-left: 0 /   0% / -inf dB"
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(raw)):
            assert adaptador.get_volume() == 0


# ---------------------------------------------------------------------------
# volume_up / volume_down
# ---------------------------------------------------------------------------

class TestVolumeUpDown:
    def test_volume_up_padrao(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.volume_up()
        cmd = mock.call_args[0][0]
        assert "+5%" in cmd

    def test_volume_down_custom(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.volume_down(10)
        cmd = mock.call_args[0][0]
        assert "-10%" in cmd


# ---------------------------------------------------------------------------
# toggle_mute / is_muted
# ---------------------------------------------------------------------------

class TestMudo:
    def test_toggle_chama_pactl(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.toggle_mute()
        cmd = mock.call_args[0][0]
        assert "toggle" in cmd

    def test_is_muted_yes(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("Mute: yes")):
            assert adaptador.is_muted() is True

    def test_is_muted_no(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("Mute: no")):
            assert adaptador.is_muted() is False


# ---------------------------------------------------------------------------
# set_volume — limites
# ---------------------------------------------------------------------------

class TestSetVolume:
    def test_limite_maximo(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.set_volume(200)
        cmd = mock.call_args[0][0]
        assert "150%" in cmd

    def test_limite_minimo(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.set_volume(-10)
        cmd = mock.call_args[0][0]
        assert "0%" in cmd


# ---------------------------------------------------------------------------
# listar_sources
# ---------------------------------------------------------------------------

PACTL_LIST_SOURCES = """\
Source #58
\tState: SUSPENDED
\tName: alsa_output.pci-0000_00_1b.0.analog-stereo.monitor
\tDescription: Monitor of Built-in Audio Analog Stereo
\tMute: no
Source #59
\tState: SUSPENDED
\tName: alsa_input.pci-0000_00_1b.0.analog-stereo
\tDescription: Built-in Audio Analog Stereo (microfone)
\tMute: no
Source #100
\tState: RUNNING
\tName: bluez_input.55:FB:BA:A6:E7:D2
\tDescription: C01 Microfone
\tMute: no
"""


class TestListarSources:
    def test_exclui_monitors(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SOURCES)):
            sources = adaptador.listar_sources()
        nomes = [s["name"] for s in sources]
        assert not any(".monitor" in n for n in nomes)

    def test_retorna_entradas_reais(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SOURCES)):
            sources = adaptador.listar_sources()
        assert len(sources) == 2

    def test_source_analogico(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SOURCES)):
            sources = adaptador.listar_sources()
        s = sources[0]
        assert s["index"] == 59
        assert "microfone" in s["description"].lower()
        assert s["tipo"] == "analog"

    def test_source_bluetooth(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run(PACTL_LIST_SOURCES)):
            sources = adaptador.listar_sources()
        s = sources[1]
        assert s["tipo"] == "bluetooth"


class TestDefaultSource:
    def test_get_default_source(self, adaptador):
        with patch("adaptador_audio.subprocess.run",
                   return_value=mock_run("alsa_input.pci-0000_00_1b.0.analog-stereo\n")):
            assert adaptador.get_default_source() == "alsa_input.pci-0000_00_1b.0.analog-stereo"

    def test_set_default_source_chama_pactl(self, adaptador):
        with patch("adaptador_audio.subprocess.run", return_value=mock_run("")) as mock:
            adaptador.set_default_source("bluez_input.55:FB:BA:A6:E7:D2")
        cmd = mock.call_args[0][0]
        assert cmd == ["pactl", "set-default-source", "bluez_input.55:FB:BA:A6:E7:D2"]


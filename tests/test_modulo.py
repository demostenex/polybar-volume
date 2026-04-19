"""
tests/test_modulo.py
Testes unitários para volume_polybar.py (ícones, modos, saída).
"""
import pathlib
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from volume_polybar import (  # noqa: E402
    _icone_e_cor,
    modo_list_sinks,
    modo_module,
    modo_toggle_mute,
    modo_volume_down,
    modo_volume_up,
    modo_set_sink,
    ICONE_MUDO,
    ICONE_BT,
    ICONE_VOL_BAIXO,
    ICONE_VOL_MEDIO,
    ICONE_VOL_ALTO,
    ICONE_HDMI,
    COR_CINZA,
    COR_VERDE,
    COR_AZUL,
    COR_ROXO,
)


# ---------------------------------------------------------------------------
# _icone_e_cor
# ---------------------------------------------------------------------------

class TestIconeECor:
    def test_mudo_sempre_cinza(self):
        for tipo in ("bluetooth", "analog", "hdmi", "loopback", "outro"):
            icone, cor = _icone_e_cor(tipo, 80, mudo=True)
            assert icone == ICONE_MUDO
            assert cor == COR_CINZA

    def test_bluetooth_verde(self):
        icone, cor = _icone_e_cor("bluetooth", 50, mudo=False)
        assert icone == ICONE_BT
        assert cor == COR_VERDE

    def test_hdmi_roxo(self):
        icone, cor = _icone_e_cor("hdmi", 50, mudo=False)
        assert icone == ICONE_HDMI
        assert cor == COR_ROXO

    def test_loopback_roxo(self):
        icone, cor = _icone_e_cor("loopback", 50, mudo=False)
        assert icone == ICONE_HDMI
        assert cor == COR_ROXO

    def test_analog_volume_baixo(self):
        icone, cor = _icone_e_cor("analog", 10, mudo=False)
        assert icone == ICONE_VOL_BAIXO
        assert cor == COR_AZUL

    def test_analog_volume_medio(self):
        icone, cor = _icone_e_cor("analog", 50, mudo=False)
        assert icone == ICONE_VOL_MEDIO
        assert cor == COR_AZUL

    def test_analog_volume_alto(self):
        icone, cor = _icone_e_cor("analog", 80, mudo=False)
        assert icone == ICONE_VOL_ALTO
        assert cor == COR_AZUL

    def test_limite_baixo_33(self):
        icone, _ = _icone_e_cor("analog", 33, mudo=False)
        assert icone == ICONE_VOL_BAIXO

    def test_limite_medio_34(self):
        icone, _ = _icone_e_cor("analog", 34, mudo=False)
        assert icone == ICONE_VOL_MEDIO

    def test_limite_alto_67(self):
        icone, _ = _icone_e_cor("analog", 67, mudo=False)
        assert icone == ICONE_VOL_ALTO


# ---------------------------------------------------------------------------
# modo_module
# ---------------------------------------------------------------------------

class TestModoModule:
    def _make_adaptador(self, tipo="analog", volume=50, mudo=False):
        a = MagicMock()
        a.get_default_sink.return_value = "alsa_output.pci.analog-stereo"
        a.detectar_tipo.return_value = tipo
        a.get_volume.return_value = volume
        a.is_muted.return_value = mudo
        return a

    def test_saida_contem_volume(self, capsys):
        modo_module(self._make_adaptador(volume=75))
        out = capsys.readouterr().out
        assert "75%" in out

    def test_saida_contem_cor_bluetooth(self, capsys):
        modo_module(self._make_adaptador(tipo="bluetooth", volume=50))
        out = capsys.readouterr().out
        assert COR_VERDE in out

    def test_saida_contem_cor_cinza_mudo(self, capsys):
        modo_module(self._make_adaptador(mudo=True))
        out = capsys.readouterr().out
        assert COR_CINZA in out

    def test_saida_tem_espaco_final(self, capsys):
        modo_module(self._make_adaptador())
        out = capsys.readouterr().out
        assert out.rstrip("\n").endswith(" ")

    def test_erro_nao_explode(self, capsys):
        a = MagicMock()
        a.get_default_sink.side_effect = Exception("pactl ausente")
        modo_module(a)
        out = capsys.readouterr().out
        assert ICONE_MUDO in out or "ERR" in out


# ---------------------------------------------------------------------------
# modo_list_sinks
# ---------------------------------------------------------------------------

class TestModoListSinks:
    def _make_adaptador(self, default="sink_bt"):
        a = MagicMock()
        a.get_default_sink.return_value = default
        a.listar_sinks.return_value = [
            {"index": 0, "name": "sink_analog", "description": "Analógico", "volume_pct": 50,
             "muted": False, "state": "SUSPENDED", "tipo": "analog"},
            {"index": 1, "name": "sink_bt", "description": "C01 Headset", "volume_pct": 100,
             "muted": False, "state": "RUNNING", "tipo": "bluetooth"},
        ]
        return a

    def test_saida_dois_sinks(self, capsys):
        modo_list_sinks(self._make_adaptador())
        out = capsys.readouterr().out
        assert len(out.strip().splitlines()) == 2

    def test_ativo_marcado(self, capsys):
        modo_list_sinks(self._make_adaptador(default="sink_bt"))
        out = capsys.readouterr().out
        linhas = out.strip().splitlines()
        assert "✔" in linhas[1]

    def test_inativo_sem_marca(self, capsys):
        modo_list_sinks(self._make_adaptador(default="sink_bt"))
        out = capsys.readouterr().out
        linhas = out.strip().splitlines()
        assert "✔" not in linhas[0]

    def test_separador_tab(self, capsys):
        modo_list_sinks(self._make_adaptador())
        out = capsys.readouterr().out
        for linha in out.strip().splitlines():
            assert "\t" in linha


# ---------------------------------------------------------------------------
# modo_toggle_mute / volume_up / volume_down / set_sink
# ---------------------------------------------------------------------------

class TestControles:
    def test_toggle_mute_chama_adaptador(self):
        a = MagicMock()
        modo_toggle_mute(a)
        a.toggle_mute.assert_called_once()

    def test_volume_up_chama_adaptador(self):
        a = MagicMock()
        modo_volume_up(a, step=10)
        a.volume_up.assert_called_once_with(10)

    def test_volume_down_chama_adaptador(self):
        a = MagicMock()
        modo_volume_down(a, step=3)
        a.volume_down.assert_called_once_with(3)

    def test_set_sink_chama_adaptador(self):
        a = MagicMock()
        modo_set_sink(a, "bluez_output.12.1")
        a.set_default_sink.assert_called_once_with("bluez_output.12.1")

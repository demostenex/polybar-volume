"""
tests/test_integracao.py
Testes de integração: executa volume_polybar.py via subprocess com pactl mockado.
"""
import pathlib
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

SCRIPT = str(pathlib.Path(__file__).resolve().parent.parent / "volume_polybar.py")
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Helper: roda o script como processo externo
# ---------------------------------------------------------------------------

def run_script(*args: str, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    import os
    env = {**os.environ, "PYTHONPATH": str(pathlib.Path(SCRIPT).parent)}
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [PYTHON, SCRIPT, *args],
        capture_output=True,
        text=True,
        env=env,
    )


# ---------------------------------------------------------------------------
# Modo module — testa saída com pactl real (só verifica formato, não valor)
# ---------------------------------------------------------------------------

class TestModoModuleIntegracao:
    def test_saida_nao_vazia(self):
        result = run_script("--mode", "module")
        # Pode falhar se pactl não estiver disponível; toleramos com skip
        if result.returncode != 0 and "pactl" in result.stderr:
            pytest.skip("pactl não disponível")
        assert result.stdout.strip() != ""

    def test_saida_contem_percentual(self):
        result = run_script("--mode", "module")
        if result.returncode != 0 and "pactl" in result.stderr:
            pytest.skip("pactl não disponível")
        assert "%" in result.stdout

    def test_saida_tem_marcacao_polybar(self):
        result = run_script("--mode", "module")
        if result.returncode != 0 and "pactl" in result.stderr:
            pytest.skip("pactl não disponível")
        # Polybar color tags: %{F#...} e %{F-}
        assert "%{F" in result.stdout


# ---------------------------------------------------------------------------
# Modo list-sinks
# ---------------------------------------------------------------------------

class TestModoListSinksIntegracao:
    def test_saida_tab_separada(self):
        result = run_script("--mode", "list-sinks")
        if result.returncode != 0:
            pytest.skip("pactl não disponível")
        for linha in result.stdout.strip().splitlines():
            assert "\t" in linha, f"Linha sem tab: {linha!r}"

    def test_pelo_menos_um_sink(self):
        result = run_script("--mode", "list-sinks")
        if result.returncode != 0:
            pytest.skip("pactl não disponível")
        assert len(result.stdout.strip().splitlines()) >= 1


# ---------------------------------------------------------------------------
# Argumentos inválidos
# ---------------------------------------------------------------------------

class TestArgumentosInvalidos:
    def test_modo_invalido(self):
        result = run_script("--mode", "modo-inexistente")
        assert result.returncode != 0

    def test_help_exitcode_zero(self):
        result = run_script("--help")
        assert result.returncode == 0
        assert "mode" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Modo set-sink com mock interno (sem chamar pactl real)
# ---------------------------------------------------------------------------

class TestModoSetSinkMockado:
    def test_set_sink_chama_pactl(self):
        """Verifica que --mode set-sink invoca pactl set-default-sink."""
        chamadas: list[list[str]] = []

        original_run = subprocess.run

        def mock_pactl(cmd, **kwargs):
            if cmd[0] == "pactl":
                chamadas.append(cmd)
                m = MagicMock()
                m.stdout = ""
                return m
            return original_run(cmd, **kwargs)

        with patch("adaptador_audio.subprocess.run", side_effect=mock_pactl):
            import volume_polybar
            import importlib
            import adaptador_audio
            importlib.reload(adaptador_audio)
            importlib.reload(volume_polybar)
            from volume_polybar import main
            main(["--mode", "set-sink", "--sink", "bluez_output.55.1"])

        set_calls = [c for c in chamadas if "set-default-sink" in c]
        assert len(set_calls) == 1
        assert set_calls[0][-1] == "bluez_output.55.1"

# volume-polybar

Módulo Polybar para controle de volume e seleção de sink de áudio (PulseAudio / PipeWire).

## Dependências

- `python3` (stdlib — sem pip)
- `pactl` (pacote `pulseaudio-utils` ou PipeWire-pulse)
- `yad` (para a janela de seleção de sinks)
- Nerd Font com Material Design Icons (ex.: JetBrainsMono Nerd Font)

## Instalação

```bash
cp volume_polybar.py   ~/.config/polybar/scripts/
cp adaptador_audio.py  ~/.config/polybar/scripts/
cp polybar-volume-toggle.sh ~/.config/polybar/scripts/
chmod +x ~/.config/polybar/scripts/polybar-volume-toggle.sh
chmod +x ~/.config/polybar/scripts/volume_polybar.py
```

Adicione o bloco de `polybar-module.ini` ao seu `~/.config/polybar/config.ini` e inclua
`volume` na lista de módulos da barra.

## Uso

| Ação no Polybar  | Resultado                    |
|------------------|------------------------------|
| Clique esquerdo  | Abre/fecha seletor de sinks  |
| Clique direito   | Toggle mudo                  |
| Scroll ↑         | Volume +5%                   |
| Scroll ↓         | Volume -5%                   |

## Ícones e cores

| Estado             | Ícone | Cor    |
|--------------------|-------|--------|
| Mudo               | 󰝟    | cinza  |
| Bluetooth ativo    | 󰋋    | verde  |
| Analógico baixo    | 󰕿    | azul   |
| Analógico médio    | 󰖀    | azul   |
| Analógico alto     | 󰕾    | azul   |
| HDMI / loopback    | 󰓃    | roxo   |

## Testes

```bash
cd volume-polybar
python -m pytest tests/ -v
```

## Estrutura

```
volume-polybar/
├── volume_polybar.py        ← entry point (--mode module|list-sinks|toggle-mute|volume-up|volume-down|set-sink)
├── adaptador_audio.py       ← backend pactl (SRP)
├── polybar-volume-toggle.sh ← janela yad de seleção de sinks
├── polybar-module.ini       ← config pronta para o Polybar
└── tests/
    ├── test_adaptador.py
    ├── test_modulo.py
    └── test_integracao.py
```

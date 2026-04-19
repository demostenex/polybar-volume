#!/usr/bin/env python3
"""
janela_audio.py
Janela flutuante de controle de áudio (PyGTK3 — nativa, sem yad).
Fecha ao perder foco ou pressionar Escape.
"""
from __future__ import annotations

import os
import pathlib
import sys

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from adaptador_audio import AdaptadorPactl  # noqa: E402

# ---------------------------------------------------------------------------
# Paleta dark (compatível com temas GTK escuros, mas com CSS override)
# ---------------------------------------------------------------------------
CSS = b"""
window {
    background-color: #1e1e2e;
}
.popup-box {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 0;
}
.section {
    background-color: #313244;
    border-radius: 6px;
    margin: 4px 8px;
    padding: 6px 8px;
}
.section-title {
    color: #6c7086;
    font-size: 9pt;
    margin-bottom: 2px;
}
label {
    color: #cdd6f4;
}
button {
    background-color: #45475a;
    color: #cdd6f4;
    border: none;
    border-radius: 4px;
    padding: 2px 8px;
    min-height: 0;
}
button:hover {
    background-color: #585b70;
}
button.vol-btn {
    font-size: 14pt;
    font-weight: bold;
    min-width: 30px;
    background-color: #313244;
}
button.mute-on {
    color: #f38ba8;
    background-color: #313244;
}
button.mute-off {
    color: #6c7086;
    background-color: #313244;
}
button.close-btn {
    background-color: transparent;
    color: #6c7086;
    font-size: 9pt;
    margin: 2px 8px 6px 8px;
}
scale trough {
    background-color: #45475a;
    min-height: 4px;
    border-radius: 2px;
}
scale highlight {
    background-color: #89b4fa;
    border-radius: 2px;
}
scale slider {
    background-color: #89b4fa;
    min-width: 12px;
    min-height: 12px;
    border-radius: 6px;
    border: none;
}
.device-row {
    background-color: transparent;
    border-radius: 4px;
    padding: 3px 6px;
}
.device-row:hover {
    background-color: #45475a;
}
.device-row.active-device label {
    color: #a6e3a1;
    font-weight: bold;
}
.device-row label {
    color: #cdd6f4;
    font-size: 9pt;
}
"""


class JanelaAudio(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(type=Gtk.WindowType.POPUP)
        self.adaptador = AdaptadorPactl()
        self._vol_debounce_id: int | None = None

        self._apply_css()
        self._build()
        self._refresh()
        self._posicionar()

        self.connect("key-press-event", self._on_key)
        self.connect("focus-out-event", self._on_focus_out)
        self.set_keep_above(True)
        self.set_decorated(False)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)

    # ------------------------------------------------------------------
    # CSS
    # ------------------------------------------------------------------

    def _apply_css(self) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.get_style_context().add_class("popup-box")
        self.add(outer)

        # Título
        title = Gtk.Label(label="  Controle de Áudio")
        title.set_xalign(0)
        title.set_margin_top(8)
        title.set_margin_start(8)
        title.get_style_context().add_class("section-title")
        outer.pack_start(title, False, False, 0)

        # Volume
        outer.pack_start(self._build_volume(), False, False, 0)

        # Saídas
        self._sinks_box = self._build_lista("🔊  Saídas")
        outer.pack_start(self._sinks_box, False, False, 0)

        # Entradas
        self._sources_box = self._build_lista("🎤  Entradas")
        outer.pack_start(self._sources_box, False, False, 0)

        # Fechar
        close = Gtk.Button(label="Fechar")
        close.get_style_context().add_class("close-btn")
        close.connect("clicked", lambda _: self.destroy())
        outer.pack_start(close, False, False, 0)

    def _build_volume(self) -> Gtk.Widget:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        section.get_style_context().add_class("section")

        lbl = Gtk.Label(label="🎚  Volume")
        lbl.set_xalign(0)
        lbl.get_style_context().add_class("section-title")
        section.pack_start(lbl, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        section.pack_start(row, False, False, 0)

        btn_down = Gtk.Button(label="−")
        btn_down.get_style_context().add_class("vol-btn")
        btn_down.connect("clicked", self._on_vol_down)
        row.pack_start(btn_down, False, False, 0)

        self._scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 150, 1)
        self._scale.set_draw_value(True)
        self._scale.set_value_pos(Gtk.PositionType.RIGHT)
        self._scale.set_size_request(220, -1)
        self._scale.connect("value-changed", self._on_scale_changed)
        row.pack_start(self._scale, True, True, 0)

        btn_up = Gtk.Button(label="+")
        btn_up.get_style_context().add_class("vol-btn")
        btn_up.connect("clicked", self._on_vol_up)
        row.pack_start(btn_up, False, False, 0)

        self._mute_btn = Gtk.Button(label="🔇  Mudo")
        self._mute_btn.get_style_context().add_class("mute-off")
        self._mute_btn.connect("clicked", self._on_toggle_mute)
        section.pack_start(self._mute_btn, False, False, 0)

        return section

    def _build_lista(self, titulo: str) -> Gtk.Widget:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        section.get_style_context().add_class("section")

        lbl = Gtk.Label(label=titulo)
        lbl.set_xalign(0)
        lbl.get_style_context().add_class("section-title")
        section.pack_start(lbl, False, False, 0)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.get_style_context().add_class("section")
        section.pack_start(listbox, True, True, 0)

        # Guarda referência ao listbox no container para _refresh
        section._listbox = listbox  # type: ignore[attr-defined]
        section._titulo = titulo     # type: ignore[attr-defined]

        return section

    # ------------------------------------------------------------------
    # Refresh (popula listas)
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        try:
            vol = self.adaptador.get_volume()
            self._scale.handler_block_by_func(self._on_scale_changed)
            self._scale.set_value(vol)
            self._scale.handler_unblock_by_func(self._on_scale_changed)
        except Exception:
            pass

        try:
            muted = self.adaptador.is_muted()
            ctx = self._mute_btn.get_style_context()
            if muted:
                ctx.remove_class("mute-off")
                ctx.add_class("mute-on")
                self._mute_btn.set_label("🔇  Mudo (ativo)")
            else:
                ctx.remove_class("mute-on")
                ctx.add_class("mute-off")
                self._mute_btn.set_label("🔇  Mudo")
        except Exception:
            pass

        try:
            default_sink = self.adaptador.get_default_sink()
            sinks = self.adaptador.listar_sinks()
            self._popular_lista(
                self._sinks_box._listbox,  # type: ignore[attr-defined]
                sinks,
                default_sink,
                self._on_sink_selected,
            )
        except Exception:
            pass

        try:
            default_source = self.adaptador.get_default_source()
            sources = self.adaptador.listar_sources()
            self._popular_lista(
                self._sources_box._listbox,  # type: ignore[attr-defined]
                sources,
                default_source,
                self._on_source_selected,
            )
        except Exception:
            pass

    def _popular_lista(
        self,
        listbox: Gtk.ListBox,
        dispositivos: list[dict],
        default_name: str,
        callback,
    ) -> None:
        # Remove filhos anteriores
        for child in listbox.get_children():
            listbox.remove(child)

        for dev in dispositivos:
            row = Gtk.ListBoxRow()
            row.get_style_context().add_class("device-row")
            row._device_name = dev["name"]  # type: ignore[attr-defined]

            ativo = dev["name"] == default_name
            if ativo:
                row.get_style_context().add_class("active-device")

            icone = "✔  " if ativo else "    "
            lbl = Gtk.Label(label=f"{icone}{dev['description']}")
            lbl.set_xalign(0)
            row.add(lbl)
            listbox.add(row)

        listbox.show_all()
        listbox.connect("row-activated", callback)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_scale_changed(self, scale: Gtk.Scale) -> None:
        """Debounce: aplica volume 300ms após última mudança."""
        if self._vol_debounce_id is not None:
            GLib.source_remove(self._vol_debounce_id)
        val = int(scale.get_value())
        self._vol_debounce_id = GLib.timeout_add(300, self._apply_volume, val)

    def _apply_volume(self, val: int) -> bool:
        try:
            self.adaptador.set_volume(val)
        except Exception:
            pass
        self._vol_debounce_id = None
        return False  # não repetir

    def _on_vol_up(self, _btn) -> None:
        try:
            self.adaptador.volume_up(5)
            GLib.timeout_add(100, self._refresh)
        except Exception:
            pass

    def _on_vol_down(self, _btn) -> None:
        try:
            self.adaptador.volume_down(5)
            GLib.timeout_add(100, self._refresh)
        except Exception:
            pass

    def _on_toggle_mute(self, _btn) -> None:
        try:
            self.adaptador.toggle_mute()
            GLib.timeout_add(100, self._refresh)
        except Exception:
            pass

    def _on_sink_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        try:
            name = row._device_name  # type: ignore[attr-defined]
            self.adaptador.set_default_sink(name)
            GLib.timeout_add(200, self._refresh)
        except Exception:
            pass

    def _on_source_selected(self, listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        try:
            name = row._device_name  # type: ignore[attr-defined]
            self.adaptador.set_default_source(name)
            GLib.timeout_add(200, self._refresh)
        except Exception:
            pass

    def _on_key(self, _win, event: Gdk.EventKey) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self.destroy()
            return True
        return False

    def _on_focus_out(self, _win, _event) -> bool:
        self.destroy()
        return False

    # ------------------------------------------------------------------
    # Posicionamento perto do cursor
    # ------------------------------------------------------------------

    def _posicionar(self) -> None:
        self.show_all()
        self.realize()

        display = Gdk.Display.get_default()
        seat = display.get_default_seat()
        pointer = seat.get_pointer()
        _screen, px, py = pointer.get_position()

        w, h = self.get_size()
        sw = display.get_default_screen().get_width()
        sh = display.get_default_screen().get_height()

        # Coloca acima do cursor (barra geralmente em cima ou embaixo)
        x = max(0, min(px - w // 2, sw - w - 4))
        y = py - h - 8
        if y < 0:
            y = py + 28  # se estiver muito em cima, coloca abaixo

        self.move(x, y)


def main() -> None:
    # Suprime warnings GTK não críticos
    import warnings
    warnings.filterwarnings("ignore")
    os.environ.setdefault("NO_AT_BRIDGE", "1")

    win = JanelaAudio()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()

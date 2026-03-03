import asyncio
import flet as ft
from theme import AppTheme


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 60}:{s % 60:02d}"


class SpotifyView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.sp = None
        self.is_playing = False
        self.panel: ft.Container | None = None

        # Track display
        self.album_art = ft.Image(
            src="",
            width=220,
            height=220,
            fit=ft.BoxFit.COVER,
            border_radius=12,
            visible=False,
        )
        self.album_placeholder = ft.Container(
            width=220,
            height=220,
            bgcolor=AppTheme.CARD,
            border_radius=12,
            content=ft.Icon(ft.Icons.MUSIC_NOTE, size=60, color=AppTheme.TEXT_DIM),
            alignment=ft.Alignment(0, 0),
        )
        self.track_name = ft.Text(
            "Nothing playing", size=18, weight=ft.FontWeight.BOLD,
            color=AppTheme.TEXT, text_align=ft.TextAlign.CENTER,
        )
        self.artist_name = ft.Text(
            "Open Spotify and play something", size=13,
            color=AppTheme.TEXT_DIM, text_align=ft.TextAlign.CENTER,
        )
        self.time_cur = ft.Text("0:00", size=11, color=AppTheme.TEXT_DIM)
        self.time_total = ft.Text("0:00", size=11, color=AppTheme.TEXT_DIM)
        self.progress_bar = ft.ProgressBar(
            value=0,
            bgcolor=AppTheme.BORDER,
            color=AppTheme.ACCENT,
            expand=True,
            height=4,
            border_radius=2,
        )
        self.play_btn = ft.IconButton(
            icon=ft.Icons.PLAY_CIRCLE_FILLED,
            icon_size=56,
            icon_color=AppTheme.TEXT,
            on_click=self._toggle_play,
            tooltip="Play / Pause",
        )
        self.volume_slider = ft.Slider(
            min=0, max=100, value=50,
            divisions=100,
            active_color=AppTheme.ACCENT,
            inactive_color=AppTheme.BORDER,
            thumb_color=AppTheme.TEXT,
            on_change_end=self._set_volume,
            expand=True,
        )
        self.status_text = ft.Text("", size=12, color=AppTheme.TEXT_DIM, italic=True)

    # ── Spotify helpers ───────────────────────────────────────────────────────

    def _get_client(self):
        if self.sp is None:
            try:
                from spotify_client import get_client
                self.sp = get_client()
            except Exception as e:
                self._set_status(f"Auth error: {e}")
        return self.sp

    def _set_status(self, msg: str):
        self.status_text.value = msg

    # ── actions ──────────────────────────────────────────────────────────────

    def _toggle_play(self, e):
        sp = self._get_client()
        if not sp:
            return
        try:
            if self.is_playing:
                sp.pause_playback()
            else:
                sp.start_playback()
            self.is_playing = not self.is_playing
            self._update_play_icon()
            self.page.update()
        except Exception as ex:
            self._set_status(str(ex))
            self.page.update()

    def _next_track(self, e):
        sp = self._get_client()
        if sp:
            try:
                sp.next_track()
            except Exception:
                pass

    def _prev_track(self, e):
        sp = self._get_client()
        if sp:
            try:
                sp.previous_track()
            except Exception:
                pass

    def _set_volume(self, e):
        sp = self._get_client()
        if sp:
            try:
                sp.volume(int(e.control.value))
            except Exception:
                pass

    def _update_play_icon(self):
        self.play_btn.icon = (
            ft.Icons.PAUSE_CIRCLE_FILLED if self.is_playing
            else ft.Icons.PLAY_CIRCLE_FILLED
        )

    # ── playback polling (called from main) ──────────────────────────────────

    def update_playback(self):
        """Synchronous — meant to be run in asyncio.to_thread."""
        sp = self._get_client()
        if not sp:
            return
        try:
            pb = sp.current_playback()
            if pb and pb.get("item"):
                track = pb["item"]
                self.track_name.value = track["name"]
                self.artist_name.value = ", ".join(a["name"] for a in track["artists"])
                duration = track["duration_ms"] or 1
                progress = pb.get("progress_ms", 0)
                self.progress_bar.value = progress / duration
                self.time_cur.value = _fmt_ms(progress)
                self.time_total.value = _fmt_ms(duration)
                self.is_playing = pb.get("is_playing", False)
                self._update_play_icon()
                images = track["album"]["images"]
                if images:
                    self.album_art.src = images[0]["url"]
                    self.album_art.visible = True
                    self.album_placeholder.visible = False
                else:
                    self.album_art.visible = False
                    self.album_placeholder.visible = True

                # sync volume slider
                device = pb.get("device")
                if device and device.get("volume_percent") is not None:
                    self.volume_slider.value = device["volume_percent"]
                self._set_status("")
            else:
                self._set_status("No active playback — play something in Spotify.")
        except Exception as ex:
            self._set_status(f"Error: {ex}")

    # ── public API ───────────────────────────────────────────────────────────

    def update_rgb(self, snake_pos: float):
        if self.panel:
            try:
                self.panel.border = ft.border.only(
                    top=ft.BorderSide(2, AppTheme.snake_color(0.0, snake_pos)),
                    right=ft.BorderSide(2, AppTheme.snake_color(0.25, snake_pos)),
                    bottom=ft.BorderSide(2, AppTheme.snake_color(0.5, snake_pos)),
                    left=ft.BorderSide(2, AppTheme.snake_color(0.75, snake_pos)),
                )
                self.panel.update()
            except Exception:
                pass

    def build(self) -> ft.Control:
        art_stack = ft.Stack(
            [self.album_placeholder, self.album_art],
            width=220, height=220,
        )

        progress_row = ft.Row(
            [self.time_cur, self.progress_bar, self.time_total],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
        )

        controls_row = ft.Row(
            [
                ft.IconButton(
                    icon=ft.Icons.SKIP_PREVIOUS_ROUNDED,
                    icon_size=38,
                    icon_color=AppTheme.TEXT,
                    on_click=self._prev_track,
                    tooltip="Previous",
                ),
                self.play_btn,
                ft.IconButton(
                    icon=ft.Icons.SKIP_NEXT_ROUNDED,
                    icon_size=38,
                    icon_color=AppTheme.TEXT,
                    on_click=self._next_track,
                    tooltip="Next",
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=16,
        )

        volume_row = ft.Row(
            [
                ft.Icon(ft.Icons.VOLUME_DOWN_ROUNDED, color=AppTheme.TEXT_DIM, size=18),
                self.volume_slider,
                ft.Icon(ft.Icons.VOLUME_UP_ROUNDED, color=AppTheme.TEXT_DIM, size=18),
            ],
            spacing=8,
        )

        inner = ft.Column(
            [
                ft.Text("Spotify", size=22, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                ft.Container(height=8),
                ft.Container(content=art_stack, alignment=ft.Alignment(0, 0)),
                ft.Container(height=16),
                self.track_name,
                self.artist_name,
                ft.Container(height=12),
                progress_row,
                ft.Container(height=4),
                controls_row,
                ft.Container(height=12),
                ft.Divider(color=AppTheme.BORDER, height=1),
                ft.Container(height=8),
                volume_row,
                self.status_text,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=4,
        )

        self.panel = ft.Container(
            content=inner,
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=24,
            border=ft.border.all(2, AppTheme.BORDER),
            expand=True,
        )
        return self.panel

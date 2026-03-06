import flet as ft
import json
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlparse
from theme import AppTheme

DATA_FILE = Path("data/links.json")


class LinksView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.links: list[dict] = self._load()
        self.panel: ft.Container | None = None
        self._change_callbacks: list = []

        self.list_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        self.mini_list_col = ft.Column(spacing=6, scroll=ft.ScrollMode.AUTO, expand=True)

        self.name_input = ft.TextField(
            hint_text="Display name",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            expand=True,
            text_size=14,
            on_submit=self._add_link,
        )
        self.url_input = ft.TextField(
            hint_text="https://...",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            expand=True,
            text_size=14,
            on_submit=self._add_link,
        )

        self._refresh()

    # ── observer ─────────────────────────────────────────────────────────────

    def register_change_callback(self, cb):
        self._change_callbacks.append(cb)

    def _notify_change(self):
        for cb in self._change_callbacks:
            try:
                cb()
            except Exception:
                pass

    # ── persistence ───────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text())
                for item in data:
                    if "favorite" not in item:
                        item["favorite"] = False
                return data
            except Exception:
                pass
        return []

    def _save(self):
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.links, indent=2))

    # ── actions ───────────────────────────────────────────────────────────────

    def _normalise_url(self, url: str) -> str:
        url = url.strip()
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    def _add_link(self, e=None):
        name = self.name_input.value.strip()
        url = self._normalise_url(self.url_input.value)
        if not name or not url:
            return
        self.links.append({"id": str(uuid.uuid4()), "name": name, "url": url, "favorite": False})
        self.name_input.value = ""
        self.url_input.value = ""
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _add_quick(self, raw: str):
        """Hub quick-add: accepts a URL and derives the display name from the domain."""
        url = self._normalise_url(raw)
        if not url:
            return
        try:
            name = urlparse(url).netloc.replace("www.", "") or raw
        except Exception:
            name = raw
        self.links.append({"id": str(uuid.uuid4()), "name": name, "url": url, "favorite": False})
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _delete(self, link_id: str):
        self.links = [l for l in self.links if l["id"] != link_id]
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _toggle_favorite(self, link_id: str):
        for l in self.links:
            if l["id"] == link_id:
                l["favorite"] = not l.get("favorite", False)
                break
        self._save()
        self._refresh()
        self.page.update()

    def _rename(self, link_id: str, new_name: str):
        new_name = new_name.strip()
        if not new_name:
            return
        for l in self.links:
            if l["id"] == link_id:
                l["name"] = new_name
                break
        self._save()

    def _open(self, url: str):
        webbrowser.open(url)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _make_item(self, link: dict, compact: bool = False) -> ft.Control:
        lid = link["id"]
        url = link["url"]
        fav = link.get("favorite", False)

        name_field = ft.TextField(
            value=link["name"],
            border_color="transparent",
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            bgcolor="transparent",
            cursor_color=AppTheme.ACCENT,
            text_size=12 if compact else 14,
            expand=True,
            content_padding=ft.padding.symmetric(horizontal=4, vertical=0),
            on_blur=lambda e, i=lid: self._rename(i, e.control.value),
            on_submit=lambda e, i=lid: self._rename(i, e.control.value),
        )

        star_btn = ft.IconButton(
            icon=ft.Icons.STAR_ROUNDED if fav else ft.Icons.STAR_OUTLINE_ROUNDED,
            icon_color="#FFD700" if fav else AppTheme.TEXT_DIM,
            icon_size=16 if compact else 18,
            on_click=lambda e, i=lid: self._toggle_favorite(i),
            tooltip="Remove from favorites" if fav else "Add to favorites",
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.with_opacity(0.1, "#FFD700"),
            ),
        )

        return ft.Container(
            content=ft.Row(
                [
                    star_btn,
                    name_field,
                    ft.IconButton(
                        icon=ft.Icons.OPEN_IN_NEW,
                        icon_color=AppTheme.ACCENT,
                        icon_size=16 if compact else 18,
                        on_click=lambda e, u=url: self._open(u),
                        tooltip=url,
                        style=ft.ButtonStyle(
                            overlay_color=ft.Colors.with_opacity(0.1, AppTheme.ACCENT),
                        ),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=AppTheme.TEXT_DIM,
                        icon_size=16 if compact else 18,
                        on_click=lambda e, i=lid: self._delete(i),
                        tooltip="Delete",
                        style=ft.ButtonStyle(
                            overlay_color=ft.Colors.with_opacity(0.1, ft.Colors.RED),
                        ),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            padding=ft.padding.symmetric(
                horizontal=8 if compact else 12,
                vertical=4 if compact else 8,
            ),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )

    def _refresh(self):
        sorted_links = sorted(self.links, key=lambda l: (0 if l.get("favorite") else 1))
        for list_col, compact in [(self.list_col, False), (self.mini_list_col, True)]:
            if self.links:
                list_col.controls = [self._make_item(l, compact) for l in sorted_links]
            else:
                list_col.controls = [
                    ft.Container(
                        content=ft.Text(
                            "No links yet — add one above!",
                            color=AppTheme.TEXT_DIM, size=12, italic=True,
                        ),
                        alignment=ft.Alignment(0, 0),
                        padding=20,
                    )
                ]
            try:
                list_col.update()
            except Exception:
                pass

    # ── public API ────────────────────────────────────────────────────────────

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
        for ctrl in [self.name_input, self.url_input]:
            ctrl.border_color = AppTheme.BORDER
            ctrl.focused_border_color = AppTheme.ACCENT
            ctrl.color = AppTheme.TEXT
            ctrl.hint_style = ft.TextStyle(color=AppTheme.TEXT_DIM)
            ctrl.bgcolor = AppTheme.CARD

        self._refresh()

        add_row = ft.Row(
            [
                self.name_input,
                self.url_input,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_color=AppTheme.ACCENT,
                    icon_size=28,
                    on_click=self._add_link,
                    tooltip="Add link",
                ),
            ],
            spacing=8,
        )

        self.panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Links", size=22, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                    add_row,
                    ft.Divider(color=AppTheme.BORDER, height=1),
                    ft.Container(content=self.list_col, expand=True),
                ],
                spacing=12,
                expand=True,
            ),
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=20,
            border=ft.border.all(2, AppTheme.BORDER),
            expand=True,
        )
        return self.panel

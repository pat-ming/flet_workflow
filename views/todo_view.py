import flet as ft
import json
import uuid
from pathlib import Path
from theme import AppTheme

DATA_FILE = Path("data/todos.json")


class TodoView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.todos: list[dict] = self._load()
        self.filter = "all"
        self.panel: ft.Container | None = None

        self.list_col = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self.input = ft.TextField(
            hint_text="Add a new task...",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            expand=True,
            text_size=14,
            on_submit=self._add_todo,
        )

    # ── persistence ─────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        if DATA_FILE.exists():
            try:
                return json.loads(DATA_FILE.read_text())
            except Exception:
                pass
        return []

    def _save(self):
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.todos, indent=2))

    # ── actions ──────────────────────────────────────────────────────────────

    def _add_todo(self, e):
        text = self.input.value.strip()
        if not text:
            return
        self.todos.append({"id": str(uuid.uuid4()), "text": text, "done": False})
        self.input.value = ""
        self._save()
        self._refresh()
        self.page.update()

    def _toggle(self, todo_id: str):
        for t in self.todos:
            if t["id"] == todo_id:
                t["done"] = not t["done"]
                break
        self._save()
        self._refresh()
        self.page.update()

    def _delete(self, todo_id: str):
        self.todos = [t for t in self.todos if t["id"] != todo_id]
        self._save()
        self._refresh()
        self.page.update()

    def _set_filter(self, f: str):
        self.filter = f
        self._refresh()
        self.page.update()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _visible(self) -> list[dict]:
        if self.filter == "active":
            return [t for t in self.todos if not t["done"]]
        if self.filter == "done":
            return [t for t in self.todos if t["done"]]
        return self.todos

    def _make_item(self, todo: dict) -> ft.Control:
        tid = todo["id"]
        done = todo["done"]

        text_ctrl = ft.Text(
            spans=[ft.TextSpan(
                text=todo["text"],
                style=ft.TextStyle(
                    size=14,
                    color=AppTheme.TEXT_DIM if done else AppTheme.TEXT,
                    decoration=ft.TextDecoration.LINE_THROUGH if done else ft.TextDecoration.NONE,
                ),
            )],
            expand=True,
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Checkbox(
                        value=done,
                        on_change=lambda e, i=tid: self._toggle(i),
                        fill_color={
                            ft.ControlState.SELECTED: AppTheme.ACCENT,
                            ft.ControlState.DEFAULT: AppTheme.BORDER,
                        },
                        check_color=AppTheme.TEXT,
                    ),
                    text_ctrl,
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=AppTheme.TEXT_DIM,
                        icon_size=18,
                        on_click=lambda e, i=tid: self._delete(i),
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
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )

    def _make_filter_btn(self, label: str, key: str) -> ft.Control:
        active = self.filter == key
        return ft.TextButton(
            content=ft.Text(
                label,
                color=AppTheme.ACCENT if active else AppTheme.TEXT_DIM,
                size=13,
                weight=ft.FontWeight.W_500,
            ),
            on_click=lambda e, k=key: self._set_filter(k),
            style=ft.ButtonStyle(
                overlay_color=ft.Colors.with_opacity(0.08, AppTheme.ACCENT),
            ),
        )

    def _refresh(self):
        items = self._visible()
        if items:
            self.list_col.controls = [self._make_item(t) for t in items]
        else:
            label = {
                "all": "No tasks yet — add one above!",
                "active": "All tasks complete!",
                "done": "Nothing completed yet.",
            }[self.filter]
            self.list_col.controls = [
                ft.Container(
                    content=ft.Text(label, color=AppTheme.TEXT_DIM, size=13, italic=True),
                    alignment=ft.Alignment(0, 0),
                    padding=40,
                )
            ]

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
        self._refresh()

        filter_row = ft.Row(
            [
                self._make_filter_btn("All", "all"),
                self._make_filter_btn("Active", "active"),
                self._make_filter_btn("Done", "done"),
            ],
            spacing=4,
        )

        add_row = ft.Row(
            [
                self.input,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_color=AppTheme.ACCENT,
                    icon_size=28,
                    on_click=self._add_todo,
                    tooltip="Add task",
                ),
            ],
            spacing=8,
        )

        self.panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Tasks", size=22, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                    add_row,
                    filter_row,
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

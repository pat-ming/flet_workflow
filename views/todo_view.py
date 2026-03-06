import flet as ft
import json
import uuid
import datetime
from pathlib import Path
from theme import AppTheme

DATA_FILE = Path("data/todos.json")


class TodoView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.todos: list[dict] = self._load()
        self.filter = "all"
        self.panel: ft.Container | None = None
        self.mini_panel: ft.Container | None = None
        self._change_callbacks: list = []

        self._selected_date: str | None = None

        # Persistent controls (shared across builds)
        self.list_col = ft.Column(
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
        self.mini_list_col = ft.Column(
            spacing=6,
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
        self._date_text = ft.Text("", size=11, color=AppTheme.ACCENT)
        self._date_display = ft.Row(
            [
                ft.Icon(ft.Icons.CALENDAR_TODAY, size=12, color=AppTheme.ACCENT),
                self._date_text,
                ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color=AppTheme.TEXT_DIM,
                    icon_size=14,
                    on_click=self._clear_date,
                    tooltip="Clear date",
                    style=ft.ButtonStyle(padding=ft.padding.all(2)),
                ),
            ],
            visible=False,
            spacing=2,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        self._date_picker = ft.DatePicker(
            on_change=self._on_date_picked,
            first_date=datetime.datetime(2024, 1, 1),
            last_date=datetime.datetime(2030, 12, 31),
        )
        page.overlay.append(self._date_picker)

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

    # ── date picker ──────────────────────────────────────────────────────────

    def _open_date_picker(self, e):
        self._date_picker.open = True
        self.page.update()

    def _on_date_picked(self, e):
        val = e.control.value
        if val:
            self._selected_date = val.strftime("%Y-%m-%d")
            self._date_text.value = val.strftime("%b %d")
            self._date_display.visible = True
        else:
            self._selected_date = None
            self._date_text.value = ""
            self._date_display.visible = False
        try:
            self._date_display.update()
        except Exception:
            pass

    def _clear_date(self, e):
        self._selected_date = None
        self._date_text.value = ""
        self._date_display.visible = False
        try:
            self._date_display.update()
        except Exception:
            pass

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        if DATA_FILE.exists():
            try:
                data = json.loads(DATA_FILE.read_text())
                for item in data:
                    if "date" not in item:
                        item["date"] = None
                return data
            except Exception:
                pass
        return []

    def _save(self):
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.todos, indent=2))

    # ── sort ─────────────────────────────────────────────────────────────────

    def _sort_todos(self, todos: list[dict]) -> list[dict]:
        def sort_key(t):
            d = t.get("date")
            return (1, "") if d is None else (0, d)
        return sorted(todos, key=sort_key)

    # ── actions ──────────────────────────────────────────────────────────────

    def _add_todo(self, e):
        text = self.input.value.strip()
        if not text:
            return
        self.todos.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "done": False,
            "date": self._selected_date,
        })
        self.input.value = ""
        self._selected_date = None
        self._date_text.value = ""
        self._date_display.visible = False
        try:
            self._date_display.update()
        except Exception:
            pass
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _toggle(self, todo_id: str):
        for t in self.todos:
            if t["id"] == todo_id:
                t["done"] = not t["done"]
                break
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _delete(self, todo_id: str):
        self.todos = [t for t in self.todos if t["id"] != todo_id]
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _add_quick(self, text: str):
        """Add a todo with no date — called from hub mini view."""
        if not text:
            return
        self.todos.append({
            "id": str(uuid.uuid4()),
            "text": text,
            "done": False,
            "date": None,
        })
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _set_filter(self, f: str):
        self.filter = f
        self._refresh()
        self.page.update()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _visible(self) -> list[dict]:
        if self.filter == "active":
            items = [t for t in self.todos if not t["done"]]
        elif self.filter == "done":
            items = [t for t in self.todos if t["done"]]
        else:
            items = list(self.todos)
        return self._sort_todos(items)

    def _make_item(self, todo: dict, compact: bool = False) -> ft.Control:
        tid = todo["id"]
        done = todo["done"]
        date_str = todo.get("date")

        text_ctrl = ft.Text(
            spans=[ft.TextSpan(
                text=todo["text"],
                style=ft.TextStyle(
                    size=12 if compact else 14,
                    color=AppTheme.TEXT_DIM if done else AppTheme.TEXT,
                    decoration=ft.TextDecoration.LINE_THROUGH if done else ft.TextDecoration.NONE,
                ),
            )],
            expand=True,
        )

        date_widget = None
        if date_str:
            try:
                dt = datetime.date.fromisoformat(date_str)
                today = datetime.date.today()
                date_display = dt.strftime("%b %d")
                if done:
                    date_color = AppTheme.TEXT_DIM
                elif dt < today:
                    date_color = "#ff5555"
                elif dt == today:
                    date_color = "#44dd88"
                else:
                    date_color = AppTheme.ACCENT
            except Exception:
                date_display = date_str
                date_color = AppTheme.ACCENT
            date_widget = ft.Text(
                date_display,
                size=10,
                color=date_color,
            )

        content_col = ft.Column(
            [text_ctrl] + ([date_widget] if date_widget else []),
            spacing=1,
            expand=True,
            tight=True,
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
                    content_col,
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=AppTheme.TEXT_DIM,
                        icon_size=16 if compact else 18,
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
            padding=ft.padding.symmetric(
                horizontal=6 if compact else 12,
                vertical=4 if compact else 6,
            ),
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
        for list_col, compact in [(self.list_col, False), (self.mini_list_col, True)]:
            if items:
                list_col.controls = [self._make_item(t, compact) for t in items]
            else:
                label = {
                    "all": "No tasks yet — add one above!",
                    "active": "All tasks complete!",
                    "done": "Nothing completed yet.",
                }[self.filter]
                list_col.controls = [
                    ft.Container(
                        content=ft.Text(label, color=AppTheme.TEXT_DIM, size=12, italic=True),
                        alignment=ft.Alignment(0, 0),
                        padding=20,
                    )
                ]
            try:
                list_col.update()
            except Exception:
                pass

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
        # Sync persistent control colors to current theme
        self.input.border_color = AppTheme.BORDER
        self.input.focused_border_color = AppTheme.ACCENT
        self.input.color = AppTheme.TEXT
        self.input.hint_style = ft.TextStyle(color=AppTheme.TEXT_DIM)
        self.input.bgcolor = AppTheme.CARD
        self._date_text.color = AppTheme.ACCENT
        self._date_display.controls[0].color = AppTheme.ACCENT  # calendar icon
        self._date_display.controls[2].icon_color = AppTheme.TEXT_DIM  # × button

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
                    icon=ft.Icons.CALENDAR_TODAY_OUTLINED,
                    icon_color=AppTheme.ACCENT,
                    icon_size=22,
                    on_click=self._open_date_picker,
                    tooltip="Set due date",
                ),
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_color=AppTheme.ACCENT,
                    icon_size=28,
                    on_click=self._add_todo,
                    tooltip="Add task",
                ),
            ],
            spacing=4,
        )

        self.panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Tasks", size=22, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                    add_row,
                    self._date_display,
                    filter_row,
                    ft.Divider(color=AppTheme.BORDER, height=1),
                    ft.Container(content=self.list_col, expand=True),
                ],
                spacing=10,
                expand=True,
            ),
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=20,
            border=ft.border.all(2, AppTheme.BORDER),
            expand=True,
        )
        return self.panel

    def build_mini(self) -> ft.Control:
        """Compact todo panel for embedding in HubView."""
        mini_input = ft.TextField(
            hint_text="Add task...",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=8,
            expand=True,
            text_size=12,
            dense=True,
        )

        def add_from_mini(e):
            text = mini_input.value.strip()
            if not text:
                return
            self.todos.append({
                "id": str(uuid.uuid4()),
                "text": text,
                "done": False,
                "date": None,
            })
            mini_input.value = ""
            self._save()
            self._refresh()
            self._notify_change()
            try:
                mini_input.update()
            except Exception:
                pass
            self.page.update()

        mini_input.on_submit = add_from_mini

        self.mini_panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text("Tasks", size=15, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                    ft.Row(
                        [
                            mini_input,
                            ft.IconButton(
                                icon=ft.Icons.ADD_ROUNDED,
                                icon_color=AppTheme.ACCENT,
                                icon_size=20,
                                on_click=add_from_mini,
                                tooltip="Add task",
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Divider(color=AppTheme.BORDER, height=1),
                    ft.Container(content=self.mini_list_col, expand=True),
                ],
                spacing=8,
                expand=True,
            ),
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=14,
            border=ft.border.all(2, AppTheme.BORDER),
            expand=True,
        )
        return self.mini_panel

import flet as ft
import json
import uuid
from pathlib import Path
from theme import AppTheme

DATA_FILE = Path("data/jobs.json")

STATUSES = ["Not Applied", "Ongoing", "Accepted", "Rejected"]


def _status_color(status: str) -> str:
    if status == "Accepted":
        return "#44dd88"
    if status == "Rejected":
        return "#ff5555"
    if status == "Ongoing":
        return AppTheme.ACCENT
    return AppTheme.TEXT_DIM


class JobView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.jobs: list[dict] = self._load()
        self.panel: ft.Container | None = None
        self._change_callbacks: list = []

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

        # Persistent add-form controls
        self.company_input = ft.TextField(
            hint_text="Company",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            expand=True,
            text_size=14,
            on_submit=self._add_job,
        )
        self.title_input = ft.TextField(
            hint_text="Role / Position",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT,
            hint_style=ft.TextStyle(color=AppTheme.TEXT_DIM),
            bgcolor=AppTheme.CARD,
            border_radius=10,
            expand=True,
            text_size=14,
            on_submit=self._add_job,
        )
        self._status_dd = ft.Dropdown(
            options=[ft.dropdown.Option(s) for s in STATUSES],
            value="Not Applied",
            border_color=AppTheme.BORDER,
            focused_border_color=AppTheme.ACCENT,
            bgcolor=AppTheme.CARD,
            color=AppTheme.TEXT_DIM,
            border_radius=10,
            content_padding=ft.padding.symmetric(horizontal=10, vertical=6),
            width=148,
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

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> list[dict]:
        if DATA_FILE.exists():
            try:
                return json.loads(DATA_FILE.read_text())
            except Exception:
                pass
        return []

    def _save(self):
        DATA_FILE.parent.mkdir(exist_ok=True)
        DATA_FILE.write_text(json.dumps(self.jobs, indent=2))

    # ── actions ──────────────────────────────────────────────────────────────

    def _add_job(self, e=None):
        company = self.company_input.value.strip()
        if not company:
            return
        self.jobs.append({
            "id": str(uuid.uuid4()),
            "company": company,
            "title": self.title_input.value.strip(),
            "status": self._status_dd.value or "Not Applied",
        })
        self.company_input.value = ""
        self.title_input.value = ""
        self._status_dd.value = "Not Applied"
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _add_quick(self, company: str):
        """Quick-add from hub mini view (company only, default status)."""
        if not company:
            return
        self.jobs.append({
            "id": str(uuid.uuid4()),
            "company": company,
            "title": "",
            "status": "Not Applied",
        })
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _delete(self, job_id: str):
        self.jobs = [j for j in self.jobs if j["id"] != job_id]
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    def _set_status(self, job_id: str, status: str):
        for j in self.jobs:
            if j["id"] == job_id:
                j["status"] = status
                break
        self._save()
        self._refresh()
        self._notify_change()
        self.page.update()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _make_item(self, job: dict, compact: bool = False) -> ft.Control:
        jid = job["id"]
        status = job.get("status", "Not Applied")
        color = _status_color(status)

        # Company + optional title
        if compact or not job.get("title"):
            name_widget = ft.Text(
                job["company"],
                size=12 if compact else 14,
                color=AppTheme.TEXT,
                weight=ft.FontWeight.W_500,
                no_wrap=True,
                max_lines=1,
                overflow=ft.TextOverflow.ELLIPSIS,
                expand=True,
            )
        else:
            name_widget = ft.Column(
                [
                    ft.Text(
                        job["company"],
                        size=14,
                        color=AppTheme.TEXT,
                        weight=ft.FontWeight.W_500,
                        no_wrap=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    ft.Text(
                        job["title"],
                        size=11,
                        color=AppTheme.TEXT_DIM,
                        no_wrap=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=1,
                tight=True,
                expand=True,
            )

        status_btn = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=8, height=8,
                            bgcolor=color,
                            border_radius=4,
                        ),
                        ft.Text(
                            status,
                            size=11 if compact else 12,
                            color=color,
                            no_wrap=True,
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_DROP_DOWN,
                            size=16,
                            color=color,
                        ),
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=AppTheme.CARD,
                border_radius=8,
                padding=ft.padding.symmetric(
                    horizontal=8 if compact else 10,
                    vertical=4,
                ),
            ),
            items=[
                ft.PopupMenuItem(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=8, height=8,
                                bgcolor=_status_color(s),
                                border_radius=4,
                            ),
                            ft.Text(s, size=12, color=_status_color(s)),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    on_click=lambda e, i=jid, sv=s: self._set_status(i, sv),
                )
                for s in STATUSES
            ],
            tooltip="Change status",
        )

        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(width=2),
                    name_widget,
                    status_btn,
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=AppTheme.TEXT_DIM,
                        icon_size=16 if compact else 18,
                        on_click=lambda e, i=jid: self._delete(i),
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
        for list_col, compact in [(self.list_col, False), (self.mini_list_col, True)]:
            if self.jobs:
                list_col.controls = [self._make_item(j, compact) for j in self.jobs]
            else:
                list_col.controls = [
                    ft.Container(
                        content=ft.Text(
                            "No jobs tracked yet.",
                            color=AppTheme.TEXT_DIM,
                            size=12,
                            italic=True,
                        ),
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
        # Sync persistent controls to current theme
        for ctrl in [self.company_input, self.title_input]:
            ctrl.border_color = AppTheme.BORDER
            ctrl.focused_border_color = AppTheme.ACCENT
            ctrl.color = AppTheme.TEXT
            ctrl.hint_style = ft.TextStyle(color=AppTheme.TEXT_DIM)
            ctrl.bgcolor = AppTheme.CARD
        self._status_dd.border_color = AppTheme.BORDER
        self._status_dd.focused_border_color = AppTheme.ACCENT
        self._status_dd.bgcolor = AppTheme.CARD
        self._status_dd.color = AppTheme.TEXT_DIM

        self._refresh()

        add_row = ft.Row(
            [
                self.company_input,
                self.title_input,
                self._status_dd,
                ft.IconButton(
                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                    icon_color=AppTheme.ACCENT,
                    icon_size=28,
                    on_click=self._add_job,
                    tooltip="Add job",
                ),
            ],
            spacing=8,
        )

        self.panel = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        "Jobs",
                        size=22,
                        weight=ft.FontWeight.BOLD,
                        color=AppTheme.TEXT,
                    ),
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

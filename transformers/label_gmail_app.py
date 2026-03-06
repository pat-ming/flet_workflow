import flet as ft
import json
import asyncio
import sys
from pathlib import Path

# Allow importing from same directory
sys.path.insert(0, str(Path(__file__).parent))
from download_gmails import main as download_gmails, gmail_dataset

LABELS_FILE = Path(__file__).parent / "labels.json"

# ── theme ─────────────────────────────────────────────────────────────────────
BG     = "#0F0F1A"
PANEL  = "#13131F"
CARD   = "#1A1A2E"
CARD2  = "#1E1E38"
BORDER = "#252540"
ACCENT = "#7B68EE"
GREEN  = "#50D890"
RED    = "#FF6B6B"
TEXT   = "#E8E8FF"
DIM    = "#6868A0"


# ── label persistence ─────────────────────────────────────────────────────────

def _load_labels() -> dict:
    if LABELS_FILE.exists():
        try:
            return {item["id"]: item for item in json.loads(LABELS_FILE.read_text())}
        except Exception:
            pass
    return {}


def _save_labels(labels: dict):
    LABELS_FILE.parent.mkdir(exist_ok=True)
    LABELS_FILE.write_text(json.dumps(list(labels.values()), indent=2))


# ── Flet app ──────────────────────────────────────────────────────────────────

async def main(page: ft.Page):
    page.title = "Email Labeler"
    page.bgcolor = BG
    page.padding = 0
    page.window.width = 980
    page.window.height = 740
    page.window.min_width = 700
    page.window.min_height = 560
    page.theme_mode = ft.ThemeMode.DARK

    # ── state ─────────────────────────────────────────────────────────────────
    state: dict = {
        "dataset": [],      # gmail_dataset items with assigned "id" keys
        "labels": {},
        "queue": [],        # dataset items not yet labeled
        "current": None,    # {id, sender, subject, date, body}
    }

    # ── reusable text nodes ───────────────────────────────────────────────────
    status_dot   = ft.Container(width=8, height=8, border_radius=4, bgcolor=DIM)
    status_text  = ft.Text("Connecting…", color=DIM, size=13)
    progress_bar = ft.ProgressBar(value=0, bgcolor=CARD2, color=ACCENT, height=3, border_radius=0)
    counter_text = ft.Text("", color=DIM, size=12)

    from_text    = ft.Text("", color=TEXT, size=13, selectable=True, no_wrap=False)
    date_text    = ft.Text("", color=DIM,  size=12, selectable=True)
    subject_text = ft.Text("", color=TEXT, size=17, weight=ft.FontWeight.BOLD,
                           selectable=True, no_wrap=False)
    body_text    = ft.Text("", color=TEXT, size=13, selectable=True, no_wrap=False)

    score_ref    = {"v": 5}
    score_num    = ft.Text("5", size=44, weight=ft.FontWeight.BOLD, color=ACCENT,
                           text_align=ft.TextAlign.CENTER)

    loading_msg  = ft.Text("", color=DIM, size=14, text_align=ft.TextAlign.CENTER)

    # ── slider ────────────────────────────────────────────────────────────────
    def _on_slider(e):
        score_ref["v"] = int(round(e.control.value))
        score_num.value = str(score_ref["v"])
        # tint color: green at 10, red at 0, accent in middle
        t = score_ref["v"] / 10
        if t >= 0.5:
            c = _lerp_color(ACCENT, GREEN, (t - 0.5) * 2)
        else:
            c = _lerp_color(RED, ACCENT, t * 2)
        score_num.color = c
        score_slider.active_color = c
        page.update()

    score_slider = ft.Slider(
        min=0, max=10, divisions=10, value=5,
        active_color=ACCENT,
        inactive_color=BORDER,
        thumb_color="#9B88EE",
        label="{value}",
        expand=True,
        on_change=_on_slider,
    )

    # ── helpers ───────────────────────────────────────────────────────────────
    def _lerp_color(c1: str, c2: str, t: float) -> str:
        """Linear interpolate between two hex colors."""
        r1, g1, b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
        r2, g2, b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
        r = int(r1 + (r2-r1)*t)
        g = int(g1 + (g2-g1)*t)
        b = int(b1 + (b2-b1)*t)
        return f"#{r:02X}{g:02X}{b:02X}"

    def _update_progress():
        total   = len(state["dataset"])
        labeled = len(state["labels"])
        remain  = len(state["queue"])
        progress_bar.value = labeled / total if total else 0
        counter_text.value = f"{labeled} labeled · {remain} remaining · {total} total"

    # ── content switcher ──────────────────────────────────────────────────────
    content_area = ft.Container(expand=True)

    def _show(panel):
        content_area.content = panel
        page.update()

    # ── loading panel ─────────────────────────────────────────────────────────
    loading_panel = ft.Container(
        content=ft.Column(
            [
                ft.ProgressRing(color=ACCENT, width=52, height=52, stroke_width=4),
                loading_msg,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=20,
            expand=True,
        ),
        expand=True,
    )

    # ── done panel ────────────────────────────────────────────────────────────
    done_panel = ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.CHECK_CIRCLE_ROUNDED, color=GREEN, size=72),
                ft.Text("All done!", color=TEXT, size=26, weight=ft.FontWeight.BOLD),
                ft.Text("Dataset saved to transformers/labels.json", color=DIM, size=14),
                ft.Text("", color=DIM, size=13),  # dynamic labeled count — updated on show
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=14,
            expand=True,
        ),
        expand=True,
    )

    # ── email panel (fields updated per email) ────────────────────────────────
    meta_card = ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [ft.Icon(ft.Icons.PERSON_OUTLINE_ROUNDED, color=DIM, size=15), from_text],
                    spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Row(
                    [ft.Icon(ft.Icons.CALENDAR_TODAY_OUTLINED, color=DIM, size=15), date_text],
                    spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Divider(color=BORDER, height=1),
                ft.Row(
                    [ft.Icon(ft.Icons.SUBJECT_ROUNDED, color=DIM, size=15), subject_text],
                    spacing=8, vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ],
            spacing=8,
        ),
        bgcolor=CARD2,
        border_radius=12,
        padding=16,
        border=ft.border.all(1, BORDER),
    )

    body_scroll = ft.Column(
        controls=[body_text],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )

    body_card = ft.Container(
        content=body_scroll,
        bgcolor=CARD2,
        border_radius=12,
        padding=16,
        border=ft.border.all(1, BORDER),
        expand=True,
    )

    legend_row = ft.Row(
        [
            ft.Text("0 = spam / irrelevant", color=RED, size=11, italic=True),
            ft.Container(expand=True),
            ft.Text("5 = neutral", color=DIM, size=11, italic=True),
            ft.Container(expand=True),
            ft.Text("10 = very important", color=GREEN, size=11, italic=True),
        ]
    )

    score_card = ft.Container(
        content=ft.Column(
            [
                ft.Text("Importance Score", color=DIM, size=11,
                        weight=ft.FontWeight.W_600),
                legend_row,
                ft.Row(
                    [ft.Text("0", color=DIM, size=13), score_slider,
                     ft.Text("10", color=DIM, size=13)],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10,
                ),
                score_num,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        bgcolor=CARD2,
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=24, vertical=14),
        border=ft.border.all(1, BORDER),
    )

    async def _label(e=None):
        em = state["current"]
        if not em:
            return
        state["labels"][em["id"]] = {**em, "label": score_ref["v"]}
        _save_labels(state["labels"])
        await _advance()

    async def _skip(e=None):
        await _advance()

    skip_btn = ft.OutlinedButton(
        "Skip",
        icon=ft.Icons.SKIP_NEXT_ROUNDED,
        style=ft.ButtonStyle(
            color=DIM,
            side=ft.BorderSide(1, BORDER),
            shape=ft.RoundedRectangleBorder(radius=10),
        ),
        on_click=_skip,
    )

    label_btn = ft.ElevatedButton(
        "Label & Next",
        icon=ft.Icons.CHECK_ROUNDED,
        style=ft.ButtonStyle(
            bgcolor=ACCENT,
            color="#FFFFFF",
            shape=ft.RoundedRectangleBorder(radius=10),
            elevation=0,
        ),
        on_click=_label,
    )

    email_panel = ft.Container(
        content=ft.Column(
            [
                meta_card,
                body_card,
                score_card,
                ft.Row([skip_btn, ft.Container(expand=True), label_btn]),
            ],
            spacing=12,
            expand=True,
        ),
        expand=True,
    )

    # ── load & advance ────────────────────────────────────────────────────────
    def _show_email(item: dict):
        state["current"] = item

        # reset score
        score_ref["v"] = 5
        score_slider.value = 5
        score_num.value = "5"
        score_num.color = ACCENT
        score_slider.active_color = ACCENT

        # populate fields
        from_text.value    = item["sender"]  or "(unknown sender)"
        date_text.value    = item["date"]    or ""
        subject_text.value = item["subject"] or "(no subject)"
        raw_body = (item["body"] or "").strip()
        body_text.value = raw_body if raw_body else "(empty body)"
        body_text.color = TEXT if raw_body else DIM

        _update_progress()
        _show(email_panel)

    async def _advance():
        if not state["queue"]:
            done_panel.content.controls[3].value = (
                f"{len(state['labels'])} emails labeled and saved."
            )
            _update_progress()
            _show(done_panel)
            return
        nxt = state["queue"].pop(0)
        _show_email(nxt)

    # ── startup ───────────────────────────────────────────────────────────────
    async def startup():
        try:
            loading_msg.value = "Downloading & cleaning emails…"
            _show(loading_panel)

            await asyncio.to_thread(download_gmails)

            # gmail_dataset is now populated — assign index-based ids
            dataset = [{"id": str(i), **email} for i, email in enumerate(gmail_dataset)]
            state["dataset"] = dataset

            status_dot.bgcolor = GREEN
            status_text.value = f"Loaded {len(dataset)} emails"
            status_text.color = GREEN
            page.update()

            state["labels"] = _load_labels()
            labeled_ids     = set(state["labels"].keys())
            state["queue"]  = [item for item in dataset if item["id"] not in labeled_ids]

            _update_progress()
            page.update()
            await _advance()

        except Exception as ex:
            loading_msg.value = f"Error: {ex}"
            status_dot.bgcolor = RED
            status_text.value  = "Error"
            status_text.color  = RED
            page.update()

    # ── layout ────────────────────────────────────────────────────────────────
    page.add(
        ft.Column(
            [
                # header bar
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.MARK_EMAIL_READ_ROUNDED, color=ACCENT, size=20),
                            ft.Text("Email Labeler", size=17, weight=ft.FontWeight.BOLD, color=TEXT),
                            ft.Text("DistilBERT dataset builder", color=DIM, size=12),
                            ft.Container(expand=True),
                            status_dot,
                            status_text,
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    bgcolor=PANEL,
                    padding=ft.padding.symmetric(horizontal=24, vertical=14),
                    border=ft.border.only(bottom=ft.BorderSide(1, BORDER)),
                ),
                progress_bar,
                ft.Container(
                    content=counter_text,
                    padding=ft.padding.only(right=24, top=4, bottom=2),
                    alignment=ft.Alignment(1, 0),
                ),
                ft.Container(
                    content=content_area,
                    expand=True,
                    padding=ft.padding.symmetric(horizontal=24, vertical=12),
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    _show(loading_panel)
    page.run_task(startup)


ft.run(main)

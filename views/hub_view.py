import asyncio
import math
import datetime
import time
import flet as ft
import flet.canvas as cv
from theme import AppTheme

MODES = ["Analog", "Digital", "Stopwatch", "Timer"]

# Fixed star positions (polar offsets from clock center) for night mode
_STARS = [
    (-42, -28), (52, -47), (-58, 12), (38, 44), (-18, -58), (62, 8), (-30, 52),
]


class HubView:
    def __init__(self, page: ft.Page, todo_view, job_view, links_view):
        self.page = page
        self.todo_view = todo_view
        self.job_view = job_view
        self.links_view = links_view
        self.panel: ft.Container | None = None
        self.switch_view_fn = None
        self._mode = "Analog"

        # ── Decorative background canvas ──────────────────────────────────────
        self._deco_canvas = cv.Canvas(shapes=[], width=600, height=600)
        self._anim_t = 0.0

        # ── Analog clock ──────────────────────────────────────────────────────
        self._clock_canvas = cv.Canvas(shapes=[], width=300, height=300)
        self._ana_time = ft.Text("", size=22, weight=ft.FontWeight.W_200,
                                 color=AppTheme.TEXT, font_family="monospace")
        self._ana_date = ft.Text("", size=14, color=AppTheme.TEXT_DIM)

        # ── Digital clock ─────────────────────────────────────────────────────
        self._dig_time = ft.Text("", size=56, weight=ft.FontWeight.W_200,
                                 color=AppTheme.TEXT, font_family="monospace")
        self._dig_date = ft.Text("", size=14, color=AppTheme.TEXT_DIM)

        # ── Stopwatch ─────────────────────────────────────────────────────────
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._sw_start_mono: float | None = None

        self._sw_display = ft.Text("00:00.0", size=52, weight=ft.FontWeight.W_200,
                                   color=AppTheme.TEXT, font_family="monospace")
        self._sw_btn = ft.ElevatedButton("Start", on_click=self._sw_toggle)
        self._sw_reset_btn = ft.TextButton("Reset", on_click=self._sw_reset)

        # ── Timer ─────────────────────────────────────────────────────────────
        self._timer_running = False
        self._timer_duration = 60.0
        self._timer_remaining = 60.0
        self._timer_start_mono: float | None = None

        self._timer_display = ft.Text("01:00.0", size=52, weight=ft.FontWeight.W_200,
                                      color=AppTheme.TEXT, font_family="monospace")
        self._timer_min = ft.TextField(
            value="1", width=60, text_align=ft.TextAlign.CENTER,
            border_radius=8, text_size=16,
            border_color=AppTheme.BORDER, focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT, bgcolor=AppTheme.CARD,
        )
        self._timer_sec = ft.TextField(
            value="00", width=60, text_align=ft.TextAlign.CENTER,
            border_radius=8, text_size=16,
            border_color=AppTheme.BORDER, focused_border_color=AppTheme.ACCENT,
            color=AppTheme.TEXT, bgcolor=AppTheme.CARD,
        )
        self._timer_btn = ft.ElevatedButton("Start", on_click=self._timer_toggle)
        self._timer_reset_btn = ft.TextButton("Reset", on_click=self._timer_reset)

        self._mode_label = ft.Text(self._mode, size=12, color=AppTheme.TEXT_DIM)

        self._analog_section: ft.Container | None = None
        self._digital_section: ft.Container | None = None
        self._sw_section: ft.Container | None = None
        self._timer_section: ft.Container | None = None

    # ── formatting ────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt(seconds: float) -> str:
        s = int(seconds)
        tenths = int((seconds - s) * 10)
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}.{tenths}"

    # ── decorative background ─────────────────────────────────────────────────

    def _draw_plants(self) -> list:
        shapes = []
        t = self._anim_t
        W, H = 600, 600
        layers = [
            (H - 10, 22, 55,  4.0, 10, 2.2, "#6ab87a", 0.18),
            (H,      16, 82,  6.5, 18, 1.7, "#4ea865", 0.26),
            (H + 8,  11, 115, 9.0, 26, 1.3, "#38924e", 0.36),
        ]
        for li, (y_base, count, bh, bw, amp, freq, color, alpha) in enumerate(layers):
            x_spacing = W / count
            for i in range(count):
                x = i * x_spacing + (li * 17.3 % x_spacing) + x_spacing * 0.2
                phase = i * 1.4 + li * 2.3
                sway = amp * math.sin(t * freq + phase)
                mid_x = x + sway * 0.4
                mid_y = y_base - bh * 0.5
                tip_x = x + sway
                tip_y = y_base - bh
                shapes.append(cv.Line(x1=x, y1=y_base, x2=mid_x, y2=mid_y,
                    paint=ft.Paint(color=ft.Colors.with_opacity(alpha, color),
                                   stroke_width=bw, stroke_cap=ft.StrokeCap.ROUND)))
                shapes.append(cv.Line(x1=mid_x, y1=mid_y, x2=tip_x, y2=tip_y,
                    paint=ft.Paint(color=ft.Colors.with_opacity(alpha * 0.65, color),
                                   stroke_width=bw * 0.45, stroke_cap=ft.StrokeCap.ROUND)))
        return shapes

    def _draw_clouds(self) -> list:
        shapes = []
        t = self._anim_t
        W = 600
        span = W + 300
        layers = [
            (90,  0.18, 0.40, 0.10,  1),
            (155, 0.32, 0.62, 0.12, -1),
            (210, 0.52, 0.80, 0.11,  1),
            (75,  0.12, 0.30, 0.08, -1),
        ]
        for li, (cy, speed, scale, alpha, direction) in enumerate(layers):
            spacing = 180 + li * 28
            num = int(span / spacing) + 2
            color = ft.Colors.with_opacity(alpha, "#607888")
            for i in range(num):
                x = ((i * spacing + direction * t * speed * 28) % span) - 150
                r = 34 * scale
                shapes.append(cv.Circle(x=x,          y=cy,          radius=r,
                    paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL)))
                shapes.append(cv.Circle(x=x + r*0.88, y=cy + r*0.18, radius=r*0.72,
                    paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL)))
                shapes.append(cv.Circle(x=x - r*0.78, y=cy + r*0.22, radius=r*0.60,
                    paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL)))
                shapes.append(cv.Circle(x=x + r*0.25, y=cy - r*0.22, radius=r*0.52,
                    paint=ft.Paint(color=color, style=ft.PaintingStyle.FILL)))
        return shapes

    def _update_deco(self):
        self._deco_canvas.shapes = (
            self._draw_clouds() if AppTheme.dark else self._draw_plants()
        )
        try:
            self._deco_canvas.update()
        except Exception:
            pass

    # ── clock drawing ─────────────────────────────────────────────────────────

    def _draw_clock(self, now: datetime.datetime):
        shapes = []
        cx, cy = 150, 150
        r = 128
        # Sun in light mode, Moon in dark mode
        show_sun = not AppTheme.dark

        # Clock face background
        shapes.append(cv.Circle(x=cx, y=cy, radius=r,
            paint=ft.Paint(color=AppTheme.CARD, style=ft.PaintingStyle.FILL)))

        # ── Sun or Moon ───────────────────────────────────────────────────────
        if show_sun:
            sr = 20
            sun_col = "#FFE8A0"   # lighter, softer yellow
            ray_col = "#FFD070"
            # Wide soft glow (semi-transparent)
            shapes.append(cv.Circle(x=cx, y=cy, radius=sr + 14,
                paint=ft.Paint(color=ft.Colors.with_opacity(0.08, sun_col),
                               style=ft.PaintingStyle.FILL)))
            # Inner glow
            shapes.append(cv.Circle(x=cx, y=cy, radius=sr + 6,
                paint=ft.Paint(color=ft.Colors.with_opacity(0.12, sun_col),
                               style=ft.PaintingStyle.FILL)))
            # Sun body (slightly transparent)
            shapes.append(cv.Circle(x=cx, y=cy, radius=sr,
                paint=ft.Paint(color=ft.Colors.with_opacity(0.70, sun_col),
                               style=ft.PaintingStyle.FILL)))
            # 8 rays
            for i in range(8):
                angle = math.radians(i * 45)
                shapes.append(cv.Line(
                    x1=cx + (sr + 4) * math.sin(angle),
                    y1=cy - (sr + 4) * math.cos(angle),
                    x2=cx + (sr + 14) * math.sin(angle),
                    y2=cy - (sr + 14) * math.cos(angle),
                    paint=ft.Paint(color=ft.Colors.with_opacity(0.55, ray_col),
                                   stroke_width=2.5, stroke_cap=ft.StrokeCap.ROUND)))
        else:
            mr = 18
            moon_col = "#E8DEC0"
            # Soft glow
            shapes.append(cv.Circle(x=cx, y=cy, radius=mr + 10,
                paint=ft.Paint(color=ft.Colors.with_opacity(0.08, moon_col),
                               style=ft.PaintingStyle.FILL)))
            shapes.append(cv.Circle(x=cx, y=cy, radius=mr + 4,
                paint=ft.Paint(color=ft.Colors.with_opacity(0.10, moon_col),
                               style=ft.PaintingStyle.FILL)))
            # Moon body (full circle)
            shapes.append(cv.Circle(x=cx, y=cy, radius=mr,
                paint=ft.Paint(color=moon_col, style=ft.PaintingStyle.FILL)))
            # Crescent cutout (same color as clock face)
            shapes.append(cv.Circle(x=cx + 9, y=cy - 6, radius=mr - 2,
                paint=ft.Paint(color=AppTheme.CARD, style=ft.PaintingStyle.FILL)))
            # Stars
            for dx, dy in _STARS:
                sx, sy = cx + dx, cy + dy
                if math.hypot(dx, dy) < r - 12:
                    shapes.append(cv.Circle(x=sx, y=sy, radius=1.4,
                        paint=ft.Paint(color="#C8C8B8", style=ft.PaintingStyle.FILL)))

        # Clock border
        shapes.append(cv.Circle(x=cx, y=cy, radius=r,
            paint=ft.Paint(color=AppTheme.BORDER, style=ft.PaintingStyle.STROKE, stroke_width=2)))

        # Tick marks
        for i in range(60):
            angle = math.radians(i * 6)
            if i % 5 == 0:
                tick_start, tick_width, tick_color = r - 18, 2.5, AppTheme.TEXT_DIM
            else:
                tick_start, tick_width, tick_color = r - 8, 1.0, AppTheme.BORDER
            shapes.append(cv.Line(
                x1=cx + tick_start * math.sin(angle),
                y1=cy - tick_start * math.cos(angle),
                x2=cx + (r - 4) * math.sin(angle),
                y2=cy - (r - 4) * math.cos(angle),
                paint=ft.Paint(color=tick_color, stroke_width=tick_width)))

        # Hour hand
        h_angle = math.radians((now.hour % 12 + now.minute / 60 + now.second / 3600) * 30)
        shapes.append(cv.Line(
            x1=cx - r * 0.12 * math.sin(h_angle), y1=cy + r * 0.12 * math.cos(h_angle),
            x2=cx + r * 0.50 * math.sin(h_angle), y2=cy - r * 0.50 * math.cos(h_angle),
            paint=ft.Paint(color=AppTheme.TEXT, stroke_width=7, stroke_cap=ft.StrokeCap.ROUND)))

        # Minute hand
        m_angle = math.radians((now.minute + now.second / 60) * 6)
        shapes.append(cv.Line(
            x1=cx - r * 0.12 * math.sin(m_angle), y1=cy + r * 0.12 * math.cos(m_angle),
            x2=cx + r * 0.72 * math.sin(m_angle), y2=cy - r * 0.72 * math.cos(m_angle),
            paint=ft.Paint(color=AppTheme.TEXT, stroke_width=4, stroke_cap=ft.StrokeCap.ROUND)))

        # Second hand
        s_angle = math.radians(now.second * 6)
        shapes.append(cv.Line(
            x1=cx - r * 0.18 * math.sin(s_angle), y1=cy + r * 0.18 * math.cos(s_angle),
            x2=cx + r * 0.86 * math.sin(s_angle), y2=cy - r * 0.86 * math.cos(s_angle),
            paint=ft.Paint(color=AppTheme.ACCENT, stroke_width=2, stroke_cap=ft.StrokeCap.ROUND)))

        # Center dots
        shapes.append(cv.Circle(x=cx, y=cy, radius=7,
            paint=ft.Paint(color=AppTheme.TEXT, style=ft.PaintingStyle.FILL)))
        shapes.append(cv.Circle(x=cx, y=cy, radius=4,
            paint=ft.Paint(color=AppTheme.ACCENT, style=ft.PaintingStyle.FILL)))

        self._clock_canvas.shapes = shapes

    # ── stopwatch ─────────────────────────────────────────────────────────────

    def _sw_toggle(self, e=None):
        mono = time.monotonic()
        if self._sw_running:
            self._sw_elapsed = mono - self._sw_start_mono
            self._sw_running = False
            self._sw_btn.text = "Start"
        else:
            self._sw_start_mono = mono - self._sw_elapsed
            self._sw_running = True
            self._sw_btn.text = "Stop"
        try:
            self._sw_btn.update()
        except Exception:
            pass

    def _sw_reset(self, e=None):
        self._sw_running = False
        self._sw_elapsed = 0.0
        self._sw_start_mono = None
        self._sw_display.value = "00:00.0"
        self._sw_btn.text = "Start"
        try:
            self._sw_display.update()
            self._sw_btn.update()
        except Exception:
            pass

    # ── timer ─────────────────────────────────────────────────────────────────

    def _timer_toggle(self, e=None):
        mono = time.monotonic()
        if self._timer_running:
            elapsed = mono - self._timer_start_mono
            self._timer_remaining = max(0.0, self._timer_duration - elapsed)
            self._timer_duration = self._timer_remaining
            self._timer_running = False
            self._timer_btn.text = "Start"
        else:
            if self._timer_remaining <= 0:
                try:
                    m = max(0, int(self._timer_min.value or 0))
                    s = max(0, int(self._timer_sec.value or 0))
                    total = m * 60 + s
                except ValueError:
                    total = 0
                if total <= 0:
                    return
                self._timer_duration = float(total)
                self._timer_remaining = self._timer_duration
            self._timer_start_mono = mono
            self._timer_running = True
            self._timer_btn.text = "Stop"
        try:
            self._timer_btn.update()
        except Exception:
            pass

    def _timer_reset(self, e=None):
        self._timer_running = False
        self._timer_start_mono = None
        try:
            m = max(0, int(self._timer_min.value or 0))
            s = max(0, int(self._timer_sec.value or 0))
            total = m * 60 + s
        except ValueError:
            total = 60
        self._timer_duration = float(total) if total > 0 else 60.0
        self._timer_remaining = self._timer_duration
        self._timer_display.value = self._fmt(self._timer_remaining)
        self._timer_btn.text = "Start"
        try:
            self._timer_display.update()
            self._timer_btn.update()
        except Exception:
            pass

    # ── mode switching ────────────────────────────────────────────────────────

    def _set_mode(self, mode: str):
        self._mode = mode
        self._mode_label.value = mode
        if self._analog_section is not None:
            self._analog_section.visible = (mode == "Analog")
            self._digital_section.visible = (mode == "Digital")
            self._sw_section.visible = (mode == "Stopwatch")
            self._timer_section.visible = (mode == "Timer")
            try:
                self._mode_label.update()
                self._analog_section.update()
                self._digital_section.update()
                self._sw_section.update()
                self._timer_section.update()
            except Exception:
                pass

    # ── main loop ─────────────────────────────────────────────────────────────

    async def clock_loop(self):
        tick = 0
        while True:
            mode = self._mode
            mono = time.monotonic()

            self._anim_t += 0.1
            self._update_deco()

            if mode in ("Analog", "Digital"):
                if tick % 10 == 0:
                    now = datetime.datetime.now()
                    if mode == "Analog":
                        self._draw_clock(now)
                        self._ana_time.value = now.strftime("%H:%M:%S")
                        self._ana_date.value = now.strftime("%A,  %B %d,  %Y")
                        try:
                            self._clock_canvas.update()
                            self._ana_time.update()
                            self._ana_date.update()
                        except Exception:
                            pass
                    else:
                        self._dig_time.value = now.strftime("%H:%M:%S")
                        self._dig_date.value = now.strftime("%A,  %B %d,  %Y")
                        try:
                            self._dig_time.update()
                            self._dig_date.update()
                        except Exception:
                            pass

            elif mode == "Stopwatch":
                elapsed = (
                    (mono - self._sw_start_mono)
                    if self._sw_running and self._sw_start_mono is not None
                    else self._sw_elapsed
                )
                self._sw_display.value = self._fmt(elapsed)
                try:
                    self._sw_display.update()
                except Exception:
                    pass

            elif mode == "Timer":
                if self._timer_running and self._timer_start_mono is not None:
                    remaining = max(0.0, self._timer_duration - (mono - self._timer_start_mono))
                    if remaining <= 0 and self._timer_running:
                        self._timer_running = False
                        self._timer_remaining = 0.0
                        self._timer_btn.text = "Start"
                        try:
                            self._timer_btn.update()
                        except Exception:
                            pass
                else:
                    remaining = self._timer_remaining
                self._timer_display.value = self._fmt(remaining)
                try:
                    self._timer_display.update()
                except Exception:
                    pass

            tick = (tick + 1) % 100
            await asyncio.sleep(0.1)

    # ── mini section builder ──────────────────────────────────────────────────

    def _make_mini_section(self, title: str, tab_index: int,
                           list_col: ft.Column, add_hint: str,
                           on_add_quick) -> ft.Column:
        mini_input = ft.TextField(
            hint_text=add_hint,
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

        def do_add(e):
            text = mini_input.value.strip()
            if not text:
                return
            mini_input.value = ""
            try:
                mini_input.update()
            except Exception:
                pass
            on_add_quick(text)

        mini_input.on_submit = do_add

        def nav_to_tab(e):
            if self.switch_view_fn:
                self.switch_view_fn(tab_index)

        header = ft.Container(
            content=ft.Row(
                [
                    ft.Text(title, size=13, weight=ft.FontWeight.BOLD, color=AppTheme.TEXT),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.OPEN_IN_NEW, size=13, color=AppTheme.TEXT_DIM),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            on_click=nav_to_tab,
            ink=True,
            border_radius=6,
            padding=ft.padding.symmetric(horizontal=4, vertical=2),
        )

        return ft.Column(
            [
                header,
                ft.Row(
                    [
                        mini_input,
                        ft.IconButton(
                            icon=ft.Icons.ADD_ROUNDED,
                            icon_color=AppTheme.ACCENT,
                            icon_size=18,
                            on_click=do_add,
                            tooltip=f"Add {title.lower()}",
                        ),
                    ],
                    spacing=4,
                ),
                ft.Container(content=list_col, expand=True),
            ],
            expand=True,
            spacing=6,
        )

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
        self._ana_time.color = AppTheme.TEXT
        self._ana_date.color = AppTheme.TEXT_DIM
        self._dig_time.color = AppTheme.TEXT
        self._dig_date.color = AppTheme.TEXT_DIM
        self._sw_display.color = AppTheme.TEXT
        self._timer_display.color = AppTheme.TEXT
        self._mode_label.color = AppTheme.TEXT_DIM
        for tf in (self._timer_min, self._timer_sec):
            tf.border_color = AppTheme.BORDER
            tf.focused_border_color = AppTheme.ACCENT
            tf.color = AppTheme.TEXT
            tf.bgcolor = AppTheme.CARD

        mode_btn = ft.PopupMenuButton(
            content=ft.Container(
                content=ft.Row(
                    [
                        self._mode_label,
                        ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=16, color=AppTheme.TEXT_DIM),
                    ],
                    spacing=2,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=AppTheme.CARD,
                border_radius=8,
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
            ),
            items=[
                ft.PopupMenuItem(
                    content=ft.Text(m, size=12, color=AppTheme.TEXT),
                    on_click=lambda e, m=m: self._set_mode(m),
                )
                for m in MODES
            ],
        )

        self._analog_section = ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=self._clock_canvas, alignment=ft.Alignment(0, 0)),
                    ft.Container(height=8),
                    ft.Container(content=self._ana_time, alignment=ft.Alignment(0, 0)),
                    ft.Container(height=4),
                    ft.Container(content=self._ana_date, alignment=ft.Alignment(0, 0)),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True, alignment=ft.Alignment(0, 0),
            visible=(self._mode == "Analog"),
        )

        self._digital_section = ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=self._dig_time, alignment=ft.Alignment(0, 0)),
                    ft.Container(height=8),
                    ft.Container(content=self._dig_date, alignment=ft.Alignment(0, 0)),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True, alignment=ft.Alignment(0, 0),
            visible=(self._mode == "Digital"),
        )

        self._sw_section = ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=self._sw_display, alignment=ft.Alignment(0, 0)),
                    ft.Container(height=24),
                    ft.Row(
                        [self._sw_btn, self._sw_reset_btn],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True, alignment=ft.Alignment(0, 0),
            visible=(self._mode == "Stopwatch"),
        )

        self._timer_section = ft.Container(
            content=ft.Column(
                [
                    ft.Row(
                        [
                            self._timer_min,
                            ft.Text(":", size=24, color=AppTheme.TEXT_DIM),
                            self._timer_sec,
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=4,
                    ),
                    ft.Container(height=12),
                    ft.Container(content=self._timer_display, alignment=ft.Alignment(0, 0)),
                    ft.Container(height=24),
                    ft.Row(
                        [self._timer_btn, self._timer_reset_btn],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=12,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            ),
            expand=True, alignment=ft.Alignment(0, 0),
            visible=(self._mode == "Timer"),
        )

        clock_col = ft.Column(
            [
                ft.Row([mode_btn]),
                self._analog_section,
                self._digital_section,
                self._sw_section,
                self._timer_section,
            ],
            expand=True,
            spacing=0,
        )

        clock_stack = ft.Stack(
            [
                ft.Container(content=self._deco_canvas, alignment=ft.Alignment(0, 1)),
                ft.Container(content=clock_col, expand=True),
            ],
            expand=True,
        )

        # ── Mini right-column sections ────────────────────────────────────────
        todo_section = self._make_mini_section(
            title="Tasks", tab_index=1,
            list_col=self.todo_view.mini_list_col,
            add_hint="Add task...",
            on_add_quick=self.todo_view._add_quick,
        )
        job_section = self._make_mini_section(
            title="Jobs", tab_index=2,
            list_col=self.job_view.mini_list_col,
            add_hint="Add company...",
            on_add_quick=self.job_view._add_quick,
        )
        links_section = self._make_mini_section(
            title="Links", tab_index=4,
            list_col=self.links_view.mini_list_col,
            add_hint="Paste URL...",
            on_add_quick=self.links_view._add_quick,
        )

        right_column = ft.Container(
            content=ft.Column(
                [
                    ft.Container(content=todo_section, expand=True),
                    ft.Divider(color=AppTheme.BORDER, height=1),
                    ft.Container(content=job_section, expand=True),
                    ft.Divider(color=AppTheme.BORDER, height=1),
                    ft.Container(content=links_section, expand=True),
                ],
                expand=True,
                spacing=8,
            ),
            width=280,
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=ft.padding.only(left=14, right=14, top=14, bottom=14),
            border=ft.border.all(2, AppTheme.BORDER),
        )

        self.panel = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=clock_stack,
                        expand=True,
                        padding=ft.padding.all(16),
                        clip_behavior=ft.ClipBehavior.HARD_EDGE,
                    ),
                    ft.VerticalDivider(color=AppTheme.BORDER, width=1),
                    right_column,
                ],
                expand=True,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            bgcolor=AppTheme.PANEL,
            border_radius=16,
            padding=0,
            border=ft.border.all(2, AppTheme.BORDER),
            expand=True,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        )
        return self.panel

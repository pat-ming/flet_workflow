import asyncio
import flet as ft
from theme import AppTheme
from views.todo_view import TodoView
from views.spotify_view import SpotifyView


async def main(page: ft.Page):
    page.title = "Workflow Hub"
    page.bgcolor = AppTheme.BG
    page.padding = 0
    page.window.width = 1100
    page.window.height = 720
    page.window.min_width = 900
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {}

    # ── views ─────────────────────────────────────────────────────────────────
    todo_view = TodoView(page)
    spotify_view = SpotifyView(page)

    todo_panel = todo_view.build()
    spotify_panel = spotify_view.build()

    view_list = [todo_view, spotify_view]
    active_index = {"value": 0}

    # ── content area ──────────────────────────────────────────────────────────
    content_area = ft.Container(
        content=todo_panel,
        expand=True,
    )

    # ── sidebar nav ───────────────────────────────────────────────────────────
    NAV_ITEMS = [
        (ft.Icons.TASK_ALT_ROUNDED, "Tasks"),
        (ft.Icons.MUSIC_NOTE_ROUNDED, "Spotify"),
    ]

    nav_buttons: list[ft.Container] = []

    def make_nav_btn(icon, label, index) -> ft.Container:
        indicator = ft.Container(
            width=3,
            height=36,
            bgcolor="transparent",
            border_radius=ft.border_radius.only(top_right=4, bottom_right=4),
        )
        inner = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icon, color=AppTheme.TEXT, size=22),
                    ft.Text(label, color=AppTheme.TEXT_DIM, size=9,
                            weight=ft.FontWeight.W_500),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                tight=True,
            ),
            width=64,
            height=60,
            alignment=ft.Alignment(0, 0),
            border_radius=10,
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )
        btn = ft.Container(
            content=ft.Row([indicator, inner], spacing=0),
            on_click=lambda e, i=index: switch_view(i),
            border_radius=10,
            ink=True,
        )
        return btn, indicator, inner

    for i, (ico, lbl) in enumerate(NAV_ITEMS):
        btn, ind, inn = make_nav_btn(ico, lbl, i)
        nav_buttons.append((btn, ind, inn))

    def _apply_active(index: int, rgb_color: str = AppTheme.ACCENT):
        for i, (_, ind, inn) in enumerate(nav_buttons):
            if i == index:
                ind.bgcolor = rgb_color
                inn.bgcolor = ft.Colors.with_opacity(0.12, AppTheme.ACCENT)
            else:
                ind.bgcolor = "transparent"
                inn.bgcolor = "transparent"

    _apply_active(0)

    sidebar_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "WH", size=20, weight=ft.FontWeight.BOLD,
                        color=AppTheme.ACCENT,
                    ),
                    padding=ft.padding.only(bottom=16, top=4),
                    alignment=ft.Alignment(0, 0),
                ),
                *[btn for btn, _, _ in nav_buttons],
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        width=80,
        bgcolor=AppTheme.PANEL,
        padding=ft.padding.symmetric(vertical=16),
        border=ft.border.only(right=ft.BorderSide(2, AppTheme.BORDER)),
    )

    # ── top RGB accent bar (gradient snake) ──────────────────────────────────
    top_bar = ft.Container(
        height=3,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, 0),
            end=ft.Alignment(1, 0),
            colors=[AppTheme.BG, AppTheme.BG],
            stops=[0.0, 1.0],
        ),
    )

    # ── switch view ───────────────────────────────────────────────────────────
    def switch_view(index: int):
        active_index["value"] = index
        panels = [todo_panel, spotify_panel]
        content_area.content = panels[index]
        _apply_active(index)
        page.update()

    # ── main layout ───────────────────────────────────────────────────────────
    page.add(
        ft.Column(
            [
                top_bar,
                ft.Row(
                    [
                        sidebar_container,
                        ft.Container(
                            content=content_area,
                            expand=True,
                            padding=16,
                        ),
                    ],
                    expand=True,
                    spacing=0,
                ),
            ],
            spacing=0,
            expand=True,
        )
    )

    # ── RGB snake animation loop ──────────────────────────────────────────────
    async def rgb_loop():
        snake_pos = 0.0
        while True:
            snake_pos = (snake_pos + 0.003) % 1.0

            # Top bar: gradient snake flowing left → right
            colors, stops = AppTheme.snake_top_gradient(snake_pos)
            top_bar.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=colors,
                stops=stops,
            )
            top_bar.update()

            # Sidebar right border: snake passes through the left-side position
            sidebar_container.border = ft.border.only(
                right=ft.BorderSide(2, AppTheme.snake_color(0.75, snake_pos))
            )
            sidebar_container.update()

            # Active nav indicator: show the snake head color
            head_color = AppTheme.hsv_to_hex(snake_pos * 360)
            _apply_active(active_index["value"], head_color)
            for _, ind, _ in nav_buttons:
                try:
                    ind.update()
                except Exception:
                    pass

            # Active view panel border (per-side snake colors)
            view_list[active_index["value"]].update_rgb(snake_pos)

            await asyncio.sleep(0.03)

    # ── Spotify polling loop ──────────────────────────────────────────────────
    async def spotify_poll():
        while True:
            if active_index["value"] == 1:
                try:
                    await asyncio.to_thread(spotify_view.update_playback)
                    page.update()
                except Exception:
                    pass
            await asyncio.sleep(3)

    page.run_task(rgb_loop)
    page.run_task(spotify_poll)


ft.run(main)

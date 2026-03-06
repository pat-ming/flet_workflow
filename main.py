import asyncio
import flet as ft
from theme import AppTheme
from views.todo_view import TodoView
from views.job_view import JobView
from views.spotify_view import SpotifyView
from views.links_view import LinksView
from views.hub_view import HubView


async def main(page: ft.Page):
    page.title = "Workflow Hub"
    page.bgcolor = AppTheme.BG
    page.padding = 0
    page.window.width = 1200
    page.window.height = 760
    page.window.min_width = 900
    page.window.min_height = 600
    page.theme_mode = ft.ThemeMode.DARK
    page.fonts = {}

    dark_mode = {"value": True}
    AppTheme.set_dark(True)

    # ── views (persistent instances) ─────────────────────────────────────────
    todo_view = TodoView(page)
    job_view = JobView(page)
    spotify_view = SpotifyView(page)
    links_view = LinksView(page)
    hub_view = HubView(page, todo_view, job_view, links_view)

    # Nav order: 0=Hub, 1=Tasks, 2=Jobs, 3=Spotify, 4=Links
    view_list = [hub_view, todo_view, job_view, spotify_view, links_view]
    active_index = {"value": 0}
    panels = {}

    def build_all_panels():
        # Build todo/jobs/links first so mini_list_cols are populated before hub uses them
        panels["todo"] = todo_view.build()
        panels["jobs"] = job_view.build()
        panels["links"] = links_view.build()
        panels["hub"] = hub_view.build()
        panels["spotify"] = spotify_view.build()

    def _panel_order():
        return [panels["hub"], panels["todo"], panels["jobs"], panels["spotify"], panels["links"]]

    # ── content area ─────────────────────────────────────────────────────────
    content_area = ft.Container(expand=True)

    # ── sidebar nav ──────────────────────────────────────────────────────────
    NAV_ITEMS = [
        (ft.Icons.HOME_ROUNDED, "Hub"),
        (ft.Icons.TASK_ALT_ROUNDED, "Tasks"),
        (ft.Icons.WORK_OUTLINE_ROUNDED, "Jobs"),
        (ft.Icons.MUSIC_NOTE_ROUNDED, "Spotify"),
        (ft.Icons.LINK_ROUNDED, "Links"),
    ]

    nav_buttons: list[tuple] = []

    def make_nav_btn(icon, label, index) -> tuple:
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
            on_click=lambda _, i=index: switch_view(i),
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

    # ── theme toggle ─────────────────────────────────────────────────────────
    wh_text = ft.Text("WH", size=20, weight=ft.FontWeight.BOLD, color=AppTheme.ACCENT)

    theme_btn = ft.IconButton(
        icon=ft.Icons.LIGHT_MODE,
        icon_color=AppTheme.TEXT_DIM,
        icon_size=20,
        tooltip="Switch to light mode",
    )

    def toggle_theme(_):
        dark_mode["value"] = not dark_mode["value"]
        AppTheme.set_dark(dark_mode["value"])

        build_all_panels()
        content_area.content = _panel_order()[active_index["value"]]

        page.bgcolor = AppTheme.BG
        page.theme_mode = ft.ThemeMode.DARK if dark_mode["value"] else ft.ThemeMode.LIGHT

        sidebar_container.bgcolor = AppTheme.PANEL
        sidebar_container.border = ft.border.only(
            right=ft.BorderSide(2, AppTheme.BORDER)
        )

        for nav_tuple in nav_buttons:
            col = nav_tuple[2].content
            col.controls[0].color = AppTheme.TEXT
            col.controls[1].color = AppTheme.TEXT_DIM

        _apply_active(active_index["value"])

        wh_text.color = AppTheme.ACCENT
        theme_btn.icon = ft.Icons.LIGHT_MODE if dark_mode["value"] else ft.Icons.DARK_MODE
        theme_btn.tooltip = (
            "Switch to light mode" if dark_mode["value"] else "Switch to dark mode"
        )
        theme_btn.icon_color = AppTheme.TEXT_DIM

        page.update()

    theme_btn.on_click = toggle_theme

    # ── sidebar container ────────────────────────────────────────────────────
    sidebar_container = ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=wh_text,
                    padding=ft.padding.only(bottom=16, top=4),
                    alignment=ft.Alignment(0, 0),
                ),
                *[btn for btn, _, _ in nav_buttons],
                ft.Container(expand=True),
                ft.Container(
                    content=theme_btn,
                    alignment=ft.Alignment(0, 0),
                    padding=ft.padding.only(bottom=8),
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=6,
        ),
        width=80,
        bgcolor=AppTheme.PANEL,
        padding=ft.padding.symmetric(vertical=16),
        border=ft.border.only(right=ft.BorderSide(2, AppTheme.BORDER)),
    )

    # ── top RGB accent bar ────────────────────────────────────────────────────
    top_bar = ft.Container(
        height=3,
        gradient=ft.LinearGradient(
            begin=ft.Alignment(-1, 0),
            end=ft.Alignment(1, 0),
            colors=[AppTheme.BG, AppTheme.BG],
            stops=[0.0, 1.0],
        ),
    )

    # ── switch view ──────────────────────────────────────────────────────────
    def switch_view(index: int):
        active_index["value"] = index
        content_area.content = _panel_order()[index]
        _apply_active(index)
        page.update()

    # Give hub_view a reference to switch_view so section headers can navigate
    hub_view.switch_view_fn = switch_view

    # ── initial build ────────────────────────────────────────────────────────
    build_all_panels()
    content_area.content = panels["hub"]
    _apply_active(0)

    # ── main layout ──────────────────────────────────────────────────────────
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

            colors, stops = AppTheme.snake_top_gradient(snake_pos)
            top_bar.gradient = ft.LinearGradient(
                begin=ft.Alignment(-1, 0),
                end=ft.Alignment(1, 0),
                colors=colors,
                stops=stops,
            )
            top_bar.update()

            sidebar_container.border = ft.border.only(
                right=ft.BorderSide(2, AppTheme.snake_color(0.75, snake_pos))
            )
            sidebar_container.update()

            head_color = AppTheme.hsv_to_hex(snake_pos * 360)
            _apply_active(active_index["value"], head_color)
            for _, ind, _ in nav_buttons:
                try:
                    ind.update()
                except Exception:
                    pass

            view_list[active_index["value"]].update_rgb(snake_pos)

            await asyncio.sleep(0.03)

    # ── Spotify polling loop ──────────────────────────────────────────────────
    async def spotify_poll():
        while True:
            if active_index["value"] == 3:  # Spotify is now index 3
                try:
                    await asyncio.to_thread(spotify_view.update_playback)
                    page.update()
                except Exception:
                    pass
            await asyncio.sleep(3)

    page.run_task(rgb_loop)
    page.run_task(spotify_poll)
    page.run_task(hub_view.clock_loop)


ft.run(main)

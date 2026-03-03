import flet as ft
import asyncio


async def main(page: ft.Page):
    page.title = "Counter"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    count = ft.Text(value="0", size=80, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)

    holding = {"active": False}

    def update_color():
        val = max(-100, min(100, int(count.value)))
        if val <= 0:
            t = (val + 100) / 100
            r, g, b = 255, int(255 * t), int(255 * t)
        else:
            t = val / 100
            r, g, b = int(255 * (1 - t)), 255, int(255 * (1 - t))
        count.color = f"#{r:02x}{g:02x}{b:02x}"

    def step(direction):
        count.value = str(int(count.value) + direction)
        update_color()
        page.update()

    async def hold_loop(direction):
        await asyncio.sleep(0.3)  # hold threshold before acceleration begins
        interval = 0.25
        while holding["active"]:
            step(direction)
            await asyncio.sleep(interval)
            interval = max(0.05, interval * 0.8)

    def on_press(direction):
        holding["active"] = True
        step(direction)
        page.run_task(hold_loop, direction)

    def on_release(_):
        holding["active"] = False

    def reset(e):
        count.value = "0"
        update_color()
        page.update()

    def make_hold_btn(label, direction):
        return ft.GestureDetector(
            content=ft.Container(
                content=ft.Text(label, size=20, weight=ft.FontWeight.BOLD),
                width=80,
                height=40,
                alignment=ft.Alignment(0, 0),
                bgcolor=ft.Colors.BLUE_GREY_800,
                border_radius=6,
            ),
            on_tap_down=lambda _: on_press(direction),
            on_tap_up=on_release,
        )

    page.add(
        count,
        ft.Row(
            [
                make_hold_btn("-", -1),
                ft.Button("Reset", on_click=reset, width=110),
                make_hold_btn("+", 1),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )


ft.run(main)

class AppTheme:
    # ── Dark palette ─────────────────────────────────────────────────────────
    _D_BG = "#0a0a14"
    _D_PANEL = "#10101e"
    _D_CARD = "#14142a"
    _D_TEXT = "#e2e2f0"
    _D_TEXT_DIM = "#6b6b8a"
    _D_BORDER = "#1e1e32"
    _D_ACCENT = "#6644ff"

    # ── Light palette ────────────────────────────────────────────────────────
    _L_BG = "#f4f4fb"
    _L_PANEL = "#ffffff"
    _L_CARD = "#eeeef8"
    _L_TEXT = "#1a1a2e"
    _L_TEXT_DIM = "#8888aa"
    _L_BORDER = "#d0d0e8"
    _L_ACCENT = "#6644ff"

    # ── Active colors (mutable, default dark) ────────────────────────────────
    BG = _D_BG
    PANEL = _D_PANEL
    CARD = _D_CARD
    TEXT = _D_TEXT
    TEXT_DIM = _D_TEXT_DIM
    BORDER = _D_BORDER
    ACCENT = _D_ACCENT
    dark = True

    @classmethod
    def set_dark(cls, dark: bool):
        cls.dark = dark
        if dark:
            cls.BG = cls._D_BG
            cls.PANEL = cls._D_PANEL
            cls.CARD = cls._D_CARD
            cls.TEXT = cls._D_TEXT
            cls.TEXT_DIM = cls._D_TEXT_DIM
            cls.BORDER = cls._D_BORDER
            cls.ACCENT = cls._D_ACCENT
        else:
            cls.BG = cls._L_BG
            cls.PANEL = cls._L_PANEL
            cls.CARD = cls._L_CARD
            cls.TEXT = cls._L_TEXT
            cls.TEXT_DIM = cls._L_TEXT_DIM
            cls.BORDER = cls._L_BORDER
            cls.ACCENT = cls._L_ACCENT

    # Rainbow ring: full 360° of hue spans the entire perimeter at all times.
    # As snake_pos advances 0→1, the whole ring rotates through one full cycle.

    @staticmethod
    def hsv_to_hex(h: float, s: float = 1.0, v: float = 0.9) -> str:
        """Convert HSV (h: 0-360, s/v: 0-1) to hex color string."""
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        return f"#{int((r+m)*255):02x}{int((g+m)*255):02x}{int((b+m)*255):02x}"

    @classmethod
    def snake_color(cls, side_pos: float, snake_pos: float) -> str:
        """
        Full-loop rainbow ring: every position on the perimeter is lit.
        The hue at each point = (side_pos + snake_pos) * 360, so the entire
        spectrum is always present and the ring rotates as snake_pos advances.
        """
        hue = (side_pos + snake_pos) * 360 % 360
        return cls.hsv_to_hex(hue, 1.0, 0.92)

    @classmethod
    def snake_top_gradient(cls, snake_pos: float, top_frac: float = 0.28) -> tuple:
        """
        LinearGradient colors/stops for the top bar.
        top_frac ≈ top_width / total_perimeter so the bar's hues are a
        continuous slice of the same rotating ring seen on the panel borders.
        """
        N = 20
        colors, stops = [], []
        for i in range(N):
            bar_x = i / (N - 1)
            perim_pos = bar_x * top_frac
            colors.append(cls.snake_color(perim_pos, snake_pos))
            stops.append(bar_x)
        return colors, stops

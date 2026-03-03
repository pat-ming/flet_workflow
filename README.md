# Workflow Hub

A dark-themed desktop productivity app built with [Flet](https://flet.dev) (Python). Combines a task manager and a Spotify controller in a single window, with an RGB snake animation running across the UI.

![Python](https://img.shields.io/badge/Python-3.12%2B-blue) ![Flet](https://img.shields.io/badge/Flet-0.81.0-purple) ![Platform](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey)

---

## Features

- **Task Manager** — Add, complete, and delete tasks. Filters for All / Active / Done. Persists to `data/todos.json`.
- **Spotify Controller** — Displays current track, album art, progress bar, and playback controls (play/pause, skip, previous, volume). Polls every 3 seconds.
- **RGB Snake Animation** — A continuously cycling rainbow gradient flows across the top bar, sidebar border, and active panel border.

---

## Project Structure

```
flet_workflow/
├── main.py              # App entry point, layout, nav, animation loops
├── theme.py             # Color palette and RGB animation helpers
├── config.py            # Spotify API credentials
├── spotify_client.py    # Spotipy auth + singleton client
├── views/
│   ├── todo_view.py     # Task manager view
│   └── spotify_view.py  # Spotify controller view
└── data/
    └── todos.json       # Persisted tasks (auto-created)
```

---

## Setup

### 1. Clone & create a virtual environment

```bash
git clone <repo-url>
cd flet_workflow
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install flet==0.81.0 spotipy
```

### 2. Configure Spotify credentials

Create an app at [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard), then fill in [config.py](config.py):

```python
SPOTIPY_CLIENT_ID     = "your_client_id"
SPOTIPY_CLIENT_SECRET = "your_client_secret"
SPOTIPY_REDIRECT_URI  = "http://127.0.0.1:8888/callback"
```

Add `http://127.0.0.1:8888/callback` to the **Redirect URIs** in your Spotify app settings.

### 3. Run

```bash
python main.py
```

On first launch, a browser tab will open for Spotify OAuth. After authorizing, the token is cached in `.spotify_cache`.

---

## Building a Standalone Executable

### macOS `.app`

```bash
pip install pyinstaller
flet pack main.py --name "WorkflowHub" --product-name "Workflow Hub" -y
# Output: dist/WorkflowHub.app
```

On first open, right-click → **Open** to bypass the macOS Gatekeeper warning.

### Windows `.exe` (via GitHub Actions)

Push to `main` (or trigger manually from the **Actions** tab). The workflow at [.github/workflows/build-windows.yml](.github/workflows/build-windows.yml) builds `WorkflowHub.exe` on a Windows runner and uploads it as a downloadable artifact.

---

## Spotify Scopes Used

| Scope | Purpose |
|---|---|
| `user-read-playback-state` | Read current track and playback status |
| `user-modify-playback-state` | Play, pause, skip, set volume |
| `user-read-currently-playing` | Read the currently playing item |

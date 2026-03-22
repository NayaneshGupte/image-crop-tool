# High-Level Design (HLD)

## Overview

The Hero Page Generator is a fully local, offline tool. It takes a reference website screenshot and a person's photo, analyses the screenshot's visual style using computer vision, and produces a self-contained HTML hero section that blends the photo into the extracted background.

**No LLM. No API. No cloud. No token cost.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User's Browser                        │
│                        ui.html (SPA)                         │
│   File Browser │ Assignment Slots │ Generate │ Preview       │
└────────────────────────────┬────────────────────────────────┘
                             │  HTTP (localhost)
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     app.py  (Flask server)                    │
│                                                              │
│  GET  /              → serves ui.html                        │
│  GET  /api/files     → lists Resource folder images          │
│  GET  /api/preview/  → serves image thumbnails               │
│  POST /api/generate  → runs the generation pipeline          │
│  GET  /output/       → serves generated HTML files           │
└────────────────────────────┬────────────────────────────────┘
                             │  imports
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    generator.py  (pipeline)                   │
│                                                              │
│  1. extract_gradient()      Pillow + NumPy                   │
│  2. extract_nav_color()     Pillow + NumPy                   │
│  3. extract_accent_color()  Pillow + NumPy                   │
│  4. remove_bg_rembg()       rembg (optional)                 │
│  5. build_background_css()  Pure Python                      │
│  6. generate_html()         Pure Python f-string template    │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
Reference Screenshot ──► extract_gradient()    ──► grad dict
                     ──► extract_nav_color()   ──► nav_color
                     ──► extract_accent_color()──► accent_color
                                                        │
Person Photo         ──► remove_bg_rembg()     ──► transparent PNG  ─┐
                              │ (if not installed)                    │
                              └──► raw photo + CSS mask ──────────────┤
                                                                       │
                                                                       ▼
                                                           generate_html()
                                                                │
                                                                ▼
                                                      output/index.html
                                                  (self-contained, no deps)
```

---

## Component Breakdown

### `app.py` — Web Server
- Starts a Flask HTTP server on localhost
- Serves the `ui.html` single-page application
- Exposes four API endpoints
- On startup, auto-opens the browser

### `generator.py` — CV Pipeline
Pure Python module with no Flask dependency. Can be imported and used independently.

| Function | Library | What it does |
|---|---|---|
| `extract_gradient` | Pillow, NumPy | Samples thin strips along left/right edges of the screenshot to determine if the background is vertical or diagonal gradient |
| `extract_nav_color` | Pillow, NumPy | Averages the top 9% of the screenshot to get nav bar colour |
| `extract_accent_color` | Pillow, NumPy | Finds the most saturated pixel across a downscaled image — reliably captures the CTA or heading accent colour |
| `remove_bg_rembg` | rembg, onnxruntime | Runs the U²-Net local AI model to produce a transparent-background PNG. Returns `None` if rembg is not installed |
| `build_background_css` | Pure Python | Compares left-edge and right-edge colours; emits a `135deg` diagonal gradient if they differ significantly, otherwise a vertical one |
| `generate_html` | Pure Python | Assembles a fully self-contained HTML file using an f-string template; embeds the photo as a base64 data URI |

### `ui.html` — Browser UI
Single-file SPA (HTML + CSS + vanilla JS). No build step, no framework.

- Fetches the file list from `/api/files` on load
- Renders thumbnails using `/api/preview/`
- Manages assignment state entirely in JS memory
- Calls `/api/generate` via `fetch()` and renders the result in an `<iframe>`

### `Resource folder/` — Input Images
Where the user stores reference screenshots and photos. The server scans this directory when the UI requests the file list.

### `output/` — Generated Pages
Every run writes two files: `index.html` (latest, always overwritten) and `index_<unix_timestamp>.html` (archive). This folder is gitignored.

---

## Photo Blending Strategy

The tool uses two strategies, selected automatically:

**Strategy 1 — rembg (preferred)**
The U²-Net neural network segments the person from the background and outputs a PNG with an alpha channel. The transparent PNG is then placed directly on the CSS gradient background — no blending needed.

**Strategy 2 — CSS mask (fallback)**
When rembg is unavailable, a `mask-image` radial gradient is applied to the photo element. The gradient is centred toward the upper-right (where the face typically is), fading the edges to transparent. A `::after` pseudo-element bleeds the background colour in from the left edge to smooth the text/photo boundary.

---

## Technology Stack

| Layer | Technology | Reason |
|---|---|---|
| Web server | Flask | Lightweight, zero-config local HTTP server |
| Image I/O | Pillow | Best Python imaging library |
| Colour math | NumPy | Fast array operations for pixel sampling |
| Background removal | rembg + onnxruntime | Local AI inference, no API key |
| HTML generation | Python f-strings | Zero templating overhead |
| UI | Vanilla JS | No build step, works offline |

---

## Design Decisions

**Why not use an LLM?**
LLM API calls cost tokens, require an internet connection, and add latency. All the visual analysis tasks here — colour sampling, gradient detection — are deterministic computer vision problems that don't benefit from a language model.

**Why a local server instead of a pure HTML file?**
A pure HTML/JS file cannot write files to disk or run Python. A minimal local server is the smallest possible bridge between the browser UI and the Python CV pipeline.

**Why embed the photo as base64?**
The output HTML file is intended to be fully self-contained — it works when opened directly in a browser without any web server, and can be shared as a single file.

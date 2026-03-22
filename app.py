#!/usr/bin/env python3
"""
app.py  —  Hero Page Generator
───────────────────────────────
Entry point. Starts a local Flask web server and opens the browser UI at
http://localhost:5001

The UI lets you:
  • Browse images from the Resource folder
  • Assign a reference screenshot and a person photo
  • Generate a blended hero HTML page  →  saved to output/

Usage
─────
  python3 app.py                  # default port 5001
  python3 app.py --port 8080
  python3 app.py --no-open        # skip auto-opening the browser

No LLM · No API · No cost
"""

import argparse
import base64
import mimetypes
import sys
import threading
import time
import webbrowser
from pathlib import Path

# ── Dependency check ───────────────────────────────────────────────────────────
try:
    from flask import Flask, jsonify, request, send_file, send_from_directory
except ImportError:
    sys.exit("❌  Flask not installed. Run: python3 -m pip install flask")

from generator import (
    extract_gradient,
    extract_nav_color,
    extract_accent_color,
    remove_bg_rembg,
    generate_html,
)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
RESOURCES_DIR  = BASE_DIR / "Resource folder"   # where user stores input images
OUTPUT_DIR        = BASE_DIR / "output"
OUTPUT_IMAGES_DIR = BASE_DIR / "output" / "images"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_IMAGES_DIR.mkdir(exist_ok=True)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

app = Flask(__name__, static_folder=str(BASE_DIR), static_url_path="")


# ══════════════════════════════════════════════════════════════════════════════
# Routes
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the browser UI."""
    return send_from_directory(BASE_DIR, "ui.html")


@app.route("/api/files")
def list_files():
    """
    Return a JSON list of all image files in the Resource folder.
    Each entry: { name, path, size }
    """
    search_dir = RESOURCES_DIR if RESOURCES_DIR.exists() else BASE_DIR
    files = []
    for f in sorted(search_dir.iterdir()):
        if f.suffix.lower() in IMAGE_EXTS:
            files.append({
                "name": f.name,
                "path": str(f.relative_to(BASE_DIR)),
                "size": f.stat().st_size,
            })
    return jsonify(files)


@app.route("/api/preview/<path:filepath>")
def preview(filepath):
    """Serve an image from the project tree for in-browser thumbnail preview."""
    safe = BASE_DIR / filepath
    if not safe.exists() or safe.suffix.lower() not in IMAGE_EXTS:
        return jsonify({"error": "not found"}), 404
    return send_file(safe)


@app.route("/api/generate", methods=["POST"])
def generate():
    """
    POST body (JSON):
      { "screenshot": "Resource folder/file.png", "photo": "Resource folder/file.jpg" }

    Response (JSON):
      { "html_file", "archive", "method", "colors" }
    """
    data           = request.get_json()
    screenshot_rel = data.get("screenshot", "")
    photo_rel      = data.get("photo", "")

    ref_path   = BASE_DIR / screenshot_rel
    photo_path = BASE_DIR / photo_rel

    if not ref_path.exists():
        return jsonify({"error": f"Screenshot not found: {screenshot_rel}"}), 400
    if not photo_path.exists():
        return jsonify({"error": f"Photo not found: {photo_rel}"}), 400

    # 1. Extract visual style from the reference screenshot
    grad         = extract_gradient(ref_path)
    nav_color    = extract_nav_color(ref_path)
    accent_color = extract_accent_color(ref_path)

    # 2. Process photo — try rembg background removal first, fallback to CSS mask
    ts        = int(time.time())
    stem      = photo_path.stem  # original filename without extension

    png_bytes = remove_bg_rembg(photo_path)
    if png_bytes:
        photo_b64    = base64.standard_b64encode(png_bytes).decode()
        photo_mime   = "image/png"
        bg_removed   = True
        method       = "rembg"
        # Save the rembg-processed transparent PNG
        img_filename = f"{stem}_nobg_{ts}.png"
        img_bytes    = png_bytes
    else:
        with open(photo_path, "rb") as f:
            raw_bytes = f.read()
        photo_b64    = base64.standard_b64encode(raw_bytes).decode()
        photo_mime, _ = mimetypes.guess_type(str(photo_path))
        photo_mime   = photo_mime or "image/jpeg"
        bg_removed   = False
        method       = "css-mask"
        # Save a copy of the original photo used in this run
        img_filename = f"{stem}_{ts}{photo_path.suffix}"
        img_bytes    = raw_bytes

    # Save image to output/images/
    img_out_path = OUTPUT_IMAGES_DIR / img_filename
    img_out_path.write_bytes(img_bytes)

    # 3. Generate the HTML page
    html = generate_html(grad, nav_color, accent_color, photo_b64, photo_mime, bg_removed)

    # 4. Save — always overwrite output/index.html + keep a timestamped archive
    out_file = OUTPUT_DIR / "index.html"
    arc_file = OUTPUT_DIR / f"index_{ts}.html"
    out_file.write_text(html, encoding="utf-8")
    arc_file.write_text(html, encoding="utf-8")

    return jsonify({
        "html_file":  "output/index.html",
        "archive":    f"output/index_{ts}.html",
        "image_file": f"output/images/{img_filename}",
        "method":     method,
        "colors": {
            "gradient_top":   grad["top"],
            "gradient_mid":   grad["mid"],
            "gradient_right": grad["right"],
            "nav":            nav_color,
            "accent":         accent_color,
        },
    })


@app.route("/output/<path:filename>")
def serve_output(filename):
    """Serve a generated file from the output directory."""
    return send_from_directory(OUTPUT_DIR, filename)


# ══════════════════════════════════════════════════════════════════════════════
# Startup
# ══════════════════════════════════════════════════════════════════════════════

def _open_browser(port: int) -> None:
    time.sleep(1.0)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hero Page Generator — local web UI")
    parser.add_argument("--port",    type=int, default=5001, help="Port to listen on (default: 5001)")
    parser.add_argument("--no-open", action="store_true",    help="Do not open browser automatically")
    args = parser.parse_args()

    print(f"\n🚀  Hero Page Generator")
    print(f"   URL      : http://localhost:{args.port}")
    print(f"   Resources: {RESOURCES_DIR}")
    print(f"   Output   : {OUTPUT_DIR}")
    print(f"\n   Press Ctrl+C to stop.\n")

    if not args.no_open:
        threading.Thread(target=_open_browser, args=(args.port,), daemon=True).start()

    app.run(port=args.port, debug=False)

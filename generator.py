"""
generator.py
────────────
Core image-analysis and HTML-generation pipeline.
Imported by app.py — no Flask dependency here.

Pipeline
────────
  1. extract_gradient()    – samples the reference screenshot for background colours
  2. extract_nav_color()   – reads the nav bar colour from the top strip
  3. extract_accent_color()– finds the most saturated (CTA/accent) colour
  4. remove_bg_rembg()     – optional local-AI background removal (rembg)
  5. build_background_css()– converts sampled colours into a CSS gradient string
  6. generate_html()       – assembles the final self-contained HTML page
"""

import base64
import mimetypes
from pathlib import Path

import numpy as np
from PIL import Image


# ── Colour helpers ─────────────────────────────────────────────────────────────

def rgb_to_hex(rgb) -> str:
    return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))


def is_light(hex_color: str) -> bool:
    """Return True if the colour is light enough to need dark text on top."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) > 160


def _hex_distance(a: str, b: str) -> int:
    """Sum of absolute channel differences between two hex colours."""
    a, b = a.lstrip("#"), b.lstrip("#")
    return sum(abs(int(a[i:i+2], 16) - int(b[i:i+2], 16)) for i in (0, 2, 4))


# ── Step 1 – Background gradient extraction ────────────────────────────────────

def extract_gradient(ref_path: Path) -> dict:
    """
    Sample thin vertical strips along the left and right edges of the
    reference screenshot (skipping nav bar and photo area) to detect
    whether the background is a vertical or diagonal gradient.

    Returns a dict with keys: top, mid, bottom, right  (all hex strings).
    """
    img = Image.open(ref_path).convert("RGB")
    w, h = img.size

    # Left edge — sample 6 points from 12 % to 85 % height
    left_samples = []
    for y_pct in [0.12, 0.25, 0.40, 0.55, 0.70, 0.85]:
        y = int(h * y_pct)
        patch = img.crop((5, y, int(w * 0.12), y + 4))
        left_samples.append(np.array(patch).reshape(-1, 3).mean(axis=0))

    # Right edge — 3 mid points (avoids photo region on left)
    right_samples = []
    for y_pct in [0.30, 0.50, 0.70]:
        y = int(h * y_pct)
        patch = img.crop((int(w * 0.88), y, w - 5, y + 4))
        right_samples.append(np.array(patch).reshape(-1, 3).mean(axis=0))

    return {
        "top":    rgb_to_hex(left_samples[0]),
        "mid":    rgb_to_hex(left_samples[len(left_samples) // 2]),
        "bottom": rgb_to_hex(left_samples[-1]),
        "right":  rgb_to_hex(np.mean(right_samples, axis=0).astype(int)),
    }


# ── Step 2 – Nav bar colour ────────────────────────────────────────────────────

def extract_nav_color(ref_path: Path) -> str:
    """
    Average the top 9 % of the screenshot to determine the nav bar colour.
    """
    img = Image.open(ref_path).convert("RGB")
    w, h = img.size
    strip = img.crop((0, 0, w, int(h * 0.09)))
    arr = np.array(strip).reshape(-1, 3).mean(axis=0)
    return rgb_to_hex(arr)


# ── Step 3 – Accent colour ─────────────────────────────────────────────────────

def extract_accent_color(ref_path: Path) -> str:
    """
    Find the most saturated pixel in a downscaled version of the screenshot.
    This reliably picks up the CTA button or heading accent colour.
    """
    img = Image.open(ref_path).convert("RGB").resize((200, 150))
    arr = np.array(img, dtype=float)
    pmax = arr.max(axis=2)
    pmin = arr.min(axis=2)
    saturation = np.where(pmax > 0, (pmax - pmin) / pmax, 0)
    idx = np.unravel_index(saturation.argmax(), saturation.shape)
    return rgb_to_hex(arr[idx[0], idx[1]].astype(int))


# ── Step 4 – Background removal (optional) ─────────────────────────────────────

def remove_bg_rembg(photo_path: Path) -> bytes | None:
    """
    Use rembg (local U²-Net model, no API) to remove the photo background.
    Returns PNG bytes on success, or None if rembg is not installed.

    Install: pip install rembg onnxruntime
    """
    try:
        from rembg import remove
    except ImportError:
        return None

    with open(photo_path, "rb") as f:
        return remove(f.read())


# ── Step 5 – CSS gradient builder ──────────────────────────────────────────────

def build_background_css(grad: dict) -> str:
    """
    Convert the sampled gradient dict into a CSS background declaration.
    Uses a diagonal gradient if the left and right edges differ noticeably,
    otherwise a vertical gradient.
    """
    if _hex_distance(grad["top"], grad["right"]) > 30:
        return (
            f"background: linear-gradient(135deg, "
            f"{grad['top']} 0%, {grad['mid']} 50%, {grad['right']} 100%);"
        )
    return (
        f"background: linear-gradient(180deg, "
        f"{grad['top']} 0%, {grad['mid']} 60%, {grad['bottom']} 100%);"
    )


# ── Step 6 – HTML generation ───────────────────────────────────────────────────

def generate_html(
    grad:        dict,
    nav_color:   str,
    accent_color: str,
    photo_b64:   str,
    photo_mime:  str,
    bg_removed:  bool,
) -> str:
    """
    Assemble a fully self-contained HTML hero page.

    Photo blending strategy
    ──────────────────────
    • bg_removed=True  → photo has a transparent PNG background; render as-is.
    • bg_removed=False → original photo; apply a CSS radial mask-image to fade
                         the edges into the page background, plus a left-edge
                         gradient overlay to smooth the text/photo boundary.
    """
    bg_css         = build_background_css(grad)
    nav_text_color = "#1a1a3e" if is_light(nav_color) else "#ffffff"
    heading_color  = "#1a1a3e" if is_light(grad["top"]) else "#ffffff"
    photo_uri      = f"data:{photo_mime};base64,{photo_b64}"

    if bg_removed:
        photo_blend_css  = """
        .photo-wrap img {
          width: 100%; height: auto; display: block;
          object-fit: contain; max-height: 85vh;
        }"""
        photo_overlay_css = ""
    else:
        photo_blend_css = """
        .photo-wrap img {
          width: 100%; height: auto; display: block; object-fit: cover;
          -webkit-mask-image: radial-gradient(
            ellipse 88% 92% at 68% 38%,
            black 30%, rgba(0,0,0,0.95) 48%, rgba(0,0,0,0.6) 62%, transparent 80%
          );
          mask-image: radial-gradient(
            ellipse 88% 92% at 68% 38%,
            black 30%, rgba(0,0,0,0.95) 48%, rgba(0,0,0,0.6) 62%, transparent 80%
          );
        }"""
        photo_overlay_css = f"""
        .photo-wrap::after {{
          content: ''; position: absolute; inset: 0; pointer-events: none;
          background: linear-gradient(to right, {grad["top"]} 0%, transparent 30%);
        }}"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
  <title>Vision Beyond Autism</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link href="https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,400;0,600;0,700;1,700&display=swap" rel="stylesheet"/>
  <style>
    *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%}}
    body{{font-family:'Poppins',sans-serif;overflow-x:hidden}}
    nav{{
      position:sticky;top:0;z-index:200;background-color:{nav_color};
      padding:0 6%;height:62px;display:flex;align-items:center;
      justify-content:space-between;border-bottom:1px solid rgba(0,0,0,0.06);
    }}
    .nav-brand{{font-weight:700;font-size:1.05rem;color:{nav_text_color};text-decoration:none;letter-spacing:-0.02em}}
    .nav-links{{display:flex;align-items:center;gap:2rem}}
    .nav-links a{{color:{nav_text_color};text-decoration:none;font-size:.875rem;opacity:.75;transition:opacity .18s}}
    .nav-links a:hover{{opacity:1}}
    .nav-links a.active{{font-weight:600;opacity:1;border-bottom:2px solid {accent_color};padding-bottom:2px}}
    .nav-cta{{background:{accent_color}!important;color:#fff!important;opacity:1!important;padding:.45rem 1.25rem;border-radius:999px;font-weight:600;font-size:.85rem!important}}
    .nav-cta:hover{{filter:brightness(1.12);transform:translateY(-1px)}}
    .hero{{
      min-height:calc(100vh - 62px);{bg_css}
      display:flex;align-items:center;overflow:hidden;position:relative;
    }}
    .hero::before{{
      content:'';position:absolute;width:520px;height:520px;border-radius:50%;
      background:radial-gradient(circle,rgba(255,255,255,0.18) 0%,transparent 70%);
      top:50%;left:28%;transform:translate(-50%,-50%);pointer-events:none;
    }}
    .hero-inner{{width:100%;display:grid;grid-template-columns:52% 48%;align-items:center;position:relative;z-index:1}}
    .hero-text{{padding:5rem 5% 5rem 7%}}
    .hero-text h1{{font-size:clamp(2rem,3.8vw,3rem);font-weight:700;line-height:1.18;color:{heading_color};margin-bottom:1.25rem;letter-spacing:-0.02em}}
    .hero-text h1 .accent{{color:{accent_color};font-style:italic}}
    .hero-text p{{font-size:clamp(.9rem,1.3vw,1.05rem);line-height:1.65;color:{heading_color};opacity:.72;max-width:420px;margin-bottom:2.2rem}}
    .btn{{display:inline-block;padding:.7rem 2rem;background:{accent_color};color:#fff;border-radius:999px;text-decoration:none;font-weight:600;font-size:.92rem;box-shadow:0 4px 18px rgba(0,0,0,.15);transition:filter .18s,transform .12s,box-shadow .18s}}
    .btn:hover{{filter:brightness(1.1);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.2)}}
    .hero-photo{{display:flex;align-items:flex-end;justify-content:center;height:calc(100vh - 62px)}}
    .photo-wrap{{position:relative;width:100%;max-width:580px;height:100%;display:flex;align-items:flex-end}}
    {photo_blend_css}
    {photo_overlay_css}
    @media(max-width:820px){{
      .hero-inner{{grid-template-columns:1fr}}
      .hero-photo{{height:55vw;max-height:420px}}
      .hero-text{{padding:3rem 6% 1rem;text-align:center}}
      .hero-text p{{max-width:100%}}
    }}
    @media(max-width:500px){{.nav-links a:not(.nav-cta):not(.active){{display:none}}}}
  </style>
</head>
<body>
  <nav>
    <a class="nav-brand" href="#">Vision Beyond Autism</a>
    <div class="nav-links">
      <a href="#">Home</a>
      <a href="#" class="active">About</a>
      <a href="#">Philosophy</a>
      <a href="#">The Journey</a>
      <a href="#">Stories</a>
      <a href="#" class="nav-cta">Let's Talk</a>
    </div>
  </nav>
  <section class="hero">
    <div class="hero-inner">
      <div class="hero-text">
        <h1>Meet Aakanksha<br>Chitnis-Gupte:<span class="accent"><br>The Heart Behind<br>Our Vision</span></h1>
        <p>A mother, advocate, and pioneer in relationship-based approaches for autism.</p>
        <a href="#" class="btn">Let's Talk</a>
      </div>
      <div class="hero-photo">
        <div class="photo-wrap">
          <img src="{photo_uri}" alt="Aakanksha Chitnis-Gupte"/>
        </div>
      </div>
    </div>
  </section>
</body>
</html>"""

# How to Run

## Quick Start

Open **Terminal**, navigate to the project folder, and run:

```bash
cd path/to/image-crop-tool
python3 app.py
```

Your browser opens automatically at `http://localhost:5001`.

---

## Using the UI

### Step 1 — Select your reference screenshot

The left sidebar lists all images found in the `Resource folder/`. Click the screenshot that shows the design you want to match (e.g. `website_screenshot_expected.png`).

An assign bar appears at the top of the right panel — click **Set as Screenshot**.

### Step 2 — Select your photo

Click the person's photo from the sidebar (e.g. `image_101.png`), then click **Set as Photo**.

Both slots will show a live preview of the assigned images.

### Step 3 — Generate

Click **✨ Generate Page**.

The tool will:
1. Extract the background gradient and accent colour from the screenshot
2. Remove the photo background (if rembg is installed) or apply a CSS mask fade
3. Build a self-contained HTML file
4. Save it to `output/index.html`
5. Show an inline preview with **Open in new tab** and **Download** buttons

---

## Output files

Every run produces two files in the `output/` folder:

| File | Description |
|---|---|
| `output/index.html` | Latest result — always overwritten |
| `output/index_<timestamp>.html` | Timestamped archive — never overwritten |

---

## Command-line options

```bash
python3 app.py --port 8080       # use a different port
python3 app.py --no-open         # don't auto-open the browser
```

---

## Blending methods

The tool picks the best available method automatically:

| Method | Quality | Requirement |
|---|---|---|
| **rembg** | Best — clean transparent cutout | `pip install rembg onnxruntime` |
| **CSS mask** | Good — radial gradient fade | No extra install needed |

To install rembg after the initial setup:
```bash
python3 -m pip install rembg onnxruntime
```

---

## Stopping the server

Press `Ctrl + C` in the Terminal window where `app.py` is running.

---

## If the server is already running

If you see this error when starting:

```
OSError: [Errno 48] Address already in use
```

It means port 5001 is still occupied from a previous session. Fix it with one of the options below.

### Option 1 — Find and kill the process on port 5001

```bash
lsof -ti :5001 | xargs kill -9
```

Then relaunch normally:

```bash
python3 app.py
```

### Option 2 — Use a different port

```bash
python3 app.py --port 5002
```

### Option 3 — Kill all Python servers at once

Use this if you have multiple stale sessions:

```bash
pkill -f "python3 app.py"
```

Then relaunch:

```bash
python3 app.py
```

> **Tip:** Always stop the server with `Ctrl + C` rather than closing the Terminal window — this ensures the port is released cleanly.

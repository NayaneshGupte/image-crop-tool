# Installation Guide — macOS

Follow these steps once before you run the tool for the first time.

---

## Prerequisites

### 1. Check Python version

Open **Terminal** (press `Cmd + Space`, type `Terminal`, press Enter) and run:

```bash
python3 --version
```

You need **Python 3.10 or higher**. If it's missing, download it from [python.org](https://www.python.org/downloads/).

---

### 2. Check for Homebrew

```bash
brew --version
```

If you see `command not found`, install Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

After it finishes, close Terminal and reopen it.

---

## Step 1 — Install core Python packages

These are required for the tool to run:

```bash
python3 -m pip install pillow opencv-python numpy colorthief flask
```

Wait for all packages to finish downloading. You should see `Successfully installed` at the end.

---

## Step 2 — Install rembg (recommended, optional)

`rembg` removes the photo background using a local AI model. This gives the best blending result. Without it, the tool still works using a CSS mask fallback.

```bash
python3 -m pip install rembg onnxruntime
```

> **Note:** The first time you run the tool after installing rembg, it will download the U²-Net AI model (~170 MB). This is a one-time download stored in your home folder.

---

## Step 3 — Verify the installation

Run this to confirm all packages are accessible:

```bash
python3 -c "import PIL, cv2, numpy, colorthief, flask; print('✅ All core packages OK')"
```

You should see:
```
✅ All core packages OK
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip: command not found` | Use `python3 -m pip install ...` instead |
| `brew: command not found` | Re-run the Homebrew install command above |
| `opencv-python` fails on Python 3.14+ | Try `python3 -m pip install opencv-python-headless` |
| `rembg` install fails | Skip it — the CSS mask fallback works fine |
| Permission denied during pip install | Add `--user` to the end: `python3 -m pip install ... --user` |

---

Once installation is complete, see [HOW_TO_RUN.md](HOW_TO_RUN.md) to start the tool.

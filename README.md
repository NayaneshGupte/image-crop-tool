# Hero Page Generator

A fully local tool that analyses a website screenshot and blends a person's photo into a matching hero section — no LLM, no API, no cost.

## How it works

1. Drop your reference screenshot and person photo into the `Resource folder/`
2. Run `python3 app.py` — a browser UI opens at `http://localhost:5001`
3. Pick your screenshot and photo from the file browser
4. Click **Generate** — a self-contained HTML file is saved to `output/`

The tool uses computer vision to extract the background gradient, nav colour, and accent colour directly from the screenshot. The person's photo background is removed using a local AI model (rembg) if installed, or blended using a CSS mask gradient as a fallback.

## Project structure

```
image-crop-tool/
├── app.py              # Entry point — starts the Flask server
├── generator.py        # CV pipeline (colour extraction + HTML generation)
├── ui.html             # Browser UI (single-page app)
├── requirements.txt    # Python dependencies
├── Resource folder/    # Put your input images here
├── output/             # Generated HTML files (gitignored)
└── docs/
    ├── INSTALL.md      # Step-by-step Mac installation guide
    ├── HOW_TO_RUN.md   # How to use the tool
    └── HLD.md          # High-level design and architecture
```

## Quick start

```bash
# Install dependencies (once)
python3 -m pip install -r requirements.txt

# Run
python3 app.py
```

See [docs/INSTALL.md](docs/INSTALL.md) for the full installation guide and [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md) for usage instructions.

## Optional: better background removal

```bash
python3 -m pip install rembg onnxruntime
```

Downloads a local AI model (~170 MB, one-time) that removes the photo background cleanly. Without it, a CSS radial mask gradient is used as a fallback.

## Tech stack

- **Flask** — local web server
- **Pillow + NumPy** — image analysis and colour sampling
- **rembg** *(optional)* — local AI background removal
- **Vanilla JS** — browser UI, no build step

## License

MIT

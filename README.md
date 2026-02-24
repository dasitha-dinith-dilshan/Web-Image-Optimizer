# 🖼 Web Image Optimizer

Convert any image to web-optimized formats with a clean, dark-themed desktop interface.  
Built with Python + Tkinter — no browser required.

---

## Features

| Feature | Details |
|---|---|
| **Add files** | Click the drop zone, use "Add Images", or "Add Folder" (recursive scan) |
| **Drag & Drop** | Drag files or folders directly onto the drop zone |
| **Output formats** | WebP · AVIF · PNG · JPEG · BMP · TIFF |
| **Quality slider** | Adjusts per-format with sensible defaults when switching |
| **Rename options** | Keep original name + optional prefix; auto-increments to avoid overwrite |
| **Output folder** | Browse to choose, or leave blank to save beside the original |
| **Thumbnail grid** | Shows all queued images with per-item ✕ remove button |
| **Preview pane** | ◀ / ▶ navigation between images, shows filename, dimensions, and file size |
| **Dark theme** | Clean dark UI throughout |
| **Progress bar** | Live progress during batch conversion |
| **Smart conversion** | Auto-converts RGBA → RGB for formats that don't support transparency (JPEG, BMP) |

---

## Install Dependencies

```bash
pip install Pillow pillow-avif-plugin tkinterdnd2
```

> `tkinterdnd2` enables **drag & drop** — if you skip it, everything else still works normally.

---

## If That Doesn't Work

### 🪟 Windows

Try running your terminal as Administrator and use the `python -m` prefix to ensure you're hitting the right version of Python:

```bash
python -m pip install --upgrade pip
python -m pip install Pillow pillow-avif-plugin tkinterdnd2
```

---

### 🍎 macOS

You likely need `homebrew` to install the underlying AVIF support:

```bash
brew install libavif
pip install Pillow pillow-avif-plugin tkinterdnd2
```

---

### 🐧 Linux (Ubuntu / Debian)

You almost certainly need the development headers:

```bash
sudo apt-get update
sudo apt-get install python3-tk libavif-dev
pip install Pillow pillow-avif-plugin tkinterdnd2
```

---

## Run the App

```bash
python image_converter.py
```

---

## Supported Input Formats

The app automatically detects and accepts the following image types — all other file formats are silently skipped:

`.jpg` · `.jpeg` · `.png` · `.gif` · `.bmp` · `.tiff` · `.tif` · `.webp` · `.ico` · `.ppm` · `.pgm` · `.pbm` · `.tga` · `.heic` · `.heif`

---

## Output Format Guide

| Format | Best For | Transparency | Notes |
|---|---|---|---|
| **WebP** | General web use | ✅ Yes | Best balance of quality and file size |
| **AVIF** | Next-gen web images | ✅ Yes | Smallest file size, requires `pillow-avif-plugin` |
| **PNG** | Logos, icons, screenshots | ✅ Yes | Lossless, larger file size |
| **JPEG** | Photos | ❌ No | Widely compatible, no transparency |
| **BMP** | Legacy/Windows | ❌ No | Uncompressed, large file size |
| **TIFF** | Print / archival | ✅ Yes | LZW compressed |

---

## How to Use

1. **Add images** — drag and drop files or folders onto the drop zone, or use the Add buttons.
2. **Choose output format** — select from the radio buttons (WebP recommended for most cases).
3. **Adjust quality** — use the slider (affects lossy formats: WebP, AVIF, JPEG).
4. **Set rename options** — optionally add a prefix; keep or discard original filenames.
5. **Choose output folder** — browse to a folder or leave blank to save files in-place.
6. **Preview & manage** — use ◀ / ▶ to browse previews, click ✕ on thumbnails to remove.
7. **Convert** — click ⚡ Convert All and watch the progress bar.

---

## Rename Options

- **Keep original filename** — output file gets the same name with a new extension (e.g. `photo.jpg` → `photo.webp`)
- **Prefix** — prepend a custom string (e.g. prefix `web_` → `web_photo.webp`)
- **Overwrite** — if unchecked, a counter suffix is appended automatically to avoid overwriting existing files (e.g. `photo_1.webp`, `photo_2.webp`)

---

## Requirements

- Python 3.8+
- Pillow
- pillow-avif-plugin *(for AVIF output)*
- tkinterdnd2 *(optional, for drag & drop)*

---

## License

MIT — free to use, modify, and distribute.

"""
Web Image Optimizer
Convert any image to web-optimized formats: WebP, AVIF, PNG, JPEG, etc.
Features: Drag & drop, folder select, preview slider, rename options, output folder
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
import sys
import shutil
from pathlib import Path

# ── dependency check ──────────────────────────────────────────────────────────
MISSING = []
try:
    from PIL import Image, ImageTk
except ImportError:
    MISSING.append("Pillow")

try:
    import pillow_avif  # noqa: F401  — registers AVIF codec
except ImportError:
    pass  # AVIF might work via Pillow ≥ 10.1 native support

try:
    import tkinterdnd2 as tkdnd
    DND_AVAILABLE = True
except ImportError:
    tkdnd = None
    DND_AVAILABLE = False

if MISSING:
    print(f"Missing packages: {', '.join(MISSING)}\nRun:  pip install {' '.join(MISSING)}")
    sys.exit(1)


# ── constants ──────────────────────────────────────────────────────────────────
SUPPORTED_IN = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif",
                ".webp", ".ico", ".ppm", ".pgm", ".pbm", ".tga", ".heic", ".heif"}

OUTPUT_FORMATS = ["WebP", "AVIF", "PNG", "JPEG", "BMP", "TIFF"]

QUALITY_MAP = {"WebP": 85, "AVIF": 80, "PNG": 0, "JPEG": 90, "BMP": 0, "TIFF": 0}

THEME = {
    "bg":       "#1a1a2e",
    "surface":  "#16213e",
    "card":     "#0f3460",
    "accent":   "#e94560",
    "accent2":  "#533483",
    "text":     "#eaeaea",
    "subtext":  "#a0a0b0",
    "success":  "#4caf50",
    "warning":  "#ff9800",
    "border":   "#2a2a4a",
}


# ══════════════════════════════════════════════════════════════════════════════
class ImageConverterApp:

    def __init__(self, root):
        self.root = root
        self.root.title("🖼  Web Image Optimizer")
        self.root.geometry("1100x780")
        self.root.minsize(900, 650)
        self.root.configure(bg=THEME["bg"])

        # state
        self.files: list[Path] = []          # absolute paths
        self.previews: list[ImageTk.PhotoImage] = []   # keep references
        self.thumb_cache: dict[str, ImageTk.PhotoImage] = {}
        self.output_dir = tk.StringVar(value="")
        self.format_var = tk.StringVar(value="WebP")
        self.quality_var = tk.IntVar(value=85)
        self.prefix_var = tk.StringVar(value="")
        self.keep_name_var = tk.BooleanVar(value=True)
        self.overwrite_var = tk.BooleanVar(value=False)
        self.current_preview_idx = 0

        self._build_ui()
        self._apply_styles()

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── top bar ──
        top = tk.Frame(self.root, bg=THEME["bg"], pady=10)
        top.pack(fill="x", padx=20)
        tk.Label(top, text="🖼  Web Image Optimizer", font=("Segoe UI", 18, "bold"),
                 bg=THEME["bg"], fg=THEME["accent"]).pack(side="left")
        tk.Label(top, text="Convert images to web-optimized formats",
                 font=("Segoe UI", 10), bg=THEME["bg"], fg=THEME["subtext"]).pack(side="left", padx=12)

        # ── main pane (left controls + right preview) ──
        main = tk.Frame(self.root, bg=THEME["bg"])
        main.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        left = tk.Frame(main, bg=THEME["bg"], width=400)
        left.pack(side="left", fill="y", padx=(0, 10))
        left.pack_propagate(False)

        right = tk.Frame(main, bg=THEME["surface"], bd=0, relief="flat")
        right.pack(side="left", fill="both", expand=True)

        self._build_left(left)
        self._build_right(right)

        # ── status bar ──
        self.status_var = tk.StringVar(value="Ready — drop files or click Add Images")
        status = tk.Frame(self.root, bg=THEME["card"], pady=6)
        status.pack(fill="x", side="bottom")
        tk.Label(status, textvariable=self.status_var, font=("Segoe UI", 9),
                 bg=THEME["card"], fg=THEME["subtext"]).pack(side="left", padx=14)
        self.progress = ttk.Progressbar(status, length=200, mode="determinate")
        self.progress.pack(side="right", padx=14)

    def _build_left(self, parent):
        # ── Drop zone ──
        drop_frame = self._card(parent, pady=0)
        drop_frame.pack(fill="x", pady=(0, 8))
        self.drop_label = tk.Label(
            drop_frame,
            text="⬇  Drop images / folders here\nor click buttons below",
            font=("Segoe UI", 11), bg=THEME["card"], fg=THEME["subtext"],
            pady=20, cursor="hand2"
        )
        self.drop_label.pack(fill="x")

        if DND_AVAILABLE:
            self.drop_label.drop_target_register(tkdnd.DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        self.drop_label.bind("<Button-1>", lambda e: self._pick_files())

        # ── add buttons ──
        btn_row = tk.Frame(parent, bg=THEME["bg"])
        btn_row.pack(fill="x", pady=(0, 8))
        self._btn(btn_row, "📁 Add Images", self._pick_files).pack(side="left", fill="x", expand=True, padx=(0, 4))
        self._btn(btn_row, "📂 Add Folder", self._pick_folder).pack(side="left", fill="x", expand=True)

        # ── Output format ──
        fc = self._card(parent)
        fc.pack(fill="x", pady=(0, 8))
        self._label(fc, "Output Format").pack(anchor="w")
        fmt_row = tk.Frame(fc, bg=THEME["card"])
        fmt_row.pack(fill="x", pady=(6, 0))
        for fmt in OUTPUT_FORMATS:
            rb = tk.Radiobutton(fmt_row, text=fmt, variable=self.format_var,
                                value=fmt, command=self._on_format_change,
                                bg=THEME["card"], fg=THEME["text"],
                                selectcolor=THEME["accent2"],
                                activebackground=THEME["card"],
                                font=("Segoe UI", 9))
            rb.pack(side="left", padx=4)

        # quality
        self._label(fc, "Quality (lossy formats)").pack(anchor="w", pady=(8, 0))
        q_row = tk.Frame(fc, bg=THEME["card"])
        q_row.pack(fill="x")
        self.quality_slider = tk.Scale(q_row, from_=1, to=100, orient="horizontal",
                                       variable=self.quality_var,
                                       bg=THEME["card"], fg=THEME["text"],
                                       troughcolor=THEME["border"],
                                       highlightthickness=0,
                                       font=("Segoe UI", 8))
        self.quality_slider.pack(side="left", fill="x", expand=True)
        tk.Label(q_row, textvariable=self.quality_var, width=3,
                 bg=THEME["card"], fg=THEME["accent"], font=("Segoe UI", 10, "bold")).pack(side="left")

        # ── Rename options ──
        rc = self._card(parent)
        rc.pack(fill="x", pady=(0, 8))
        self._label(rc, "Rename Options").pack(anchor="w")
        tk.Checkbutton(rc, text="Keep original filename",
                       variable=self.keep_name_var,
                       bg=THEME["card"], fg=THEME["text"],
                       selectcolor=THEME["accent2"],
                       activebackground=THEME["card"],
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 0))
        prow = tk.Frame(rc, bg=THEME["card"])
        prow.pack(fill="x", pady=(4, 0))
        self._label(prow, "Prefix (optional):").pack(side="left")
        tk.Entry(prow, textvariable=self.prefix_var, width=16,
                 bg=THEME["surface"], fg=THEME["text"], insertbackground=THEME["text"],
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", padx=(6, 0))

        tk.Checkbutton(rc, text="Overwrite if file exists",
                       variable=self.overwrite_var,
                       bg=THEME["card"], fg=THEME["text"],
                       selectcolor=THEME["accent2"],
                       activebackground=THEME["card"],
                       font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))

        # ── Output folder ──
        oc = self._card(parent)
        oc.pack(fill="x", pady=(0, 8))
        self._label(oc, "Output Folder").pack(anchor="w")
        orow = tk.Frame(oc, bg=THEME["card"])
        orow.pack(fill="x", pady=(6, 0))
        tk.Entry(orow, textvariable=self.output_dir,
                 bg=THEME["surface"], fg=THEME["text"], insertbackground=THEME["text"],
                 relief="flat", font=("Segoe UI", 9)).pack(side="left", fill="x", expand=True)
        self._btn(orow, "Browse", self._pick_output, small=True).pack(side="left", padx=(4, 0))
        tk.Label(oc, text="Leave blank → save beside original",
                 bg=THEME["card"], fg=THEME["subtext"], font=("Segoe UI", 8)).pack(anchor="w")

        # ── Convert button ──
        self._btn(parent, "⚡  Convert All", self._start_convert,
                  accent=True).pack(fill="x", pady=(4, 0), ipady=8)

    def _build_right(self, parent):
        # header
        hdr = tk.Frame(parent, bg=THEME["surface"])
        hdr.pack(fill="x", padx=12, pady=(10, 4))
        self.queue_label = tk.Label(hdr, text="Queue (0 files)",
                                    font=("Segoe UI", 11, "bold"),
                                    bg=THEME["surface"], fg=THEME["text"])
        self.queue_label.pack(side="left")
        self._btn(hdr, "🗑 Clear All", self._clear_all, small=True).pack(side="right")

        # canvas + scrollbar for thumbnails
        canvas_frame = tk.Frame(parent, bg=THEME["surface"])
        canvas_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        self.thumb_canvas = tk.Canvas(canvas_frame, bg=THEME["surface"],
                                      highlightthickness=0)
        vsb = ttk.Scrollbar(canvas_frame, orient="vertical",
                             command=self.thumb_canvas.yview)
        self.thumb_canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.thumb_canvas.pack(side="left", fill="both", expand=True)

        self.thumb_inner = tk.Frame(self.thumb_canvas, bg=THEME["surface"])
        self.thumb_canvas.create_window((0, 0), window=self.thumb_inner, anchor="nw")
        self.thumb_inner.bind("<Configure>", lambda e: self.thumb_canvas.configure(
            scrollregion=self.thumb_canvas.bbox("all")))

        self.thumb_canvas.bind("<MouseWheel>",
                               lambda e: self.thumb_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # ── Preview pane at bottom ──
        prev_frame = tk.Frame(parent, bg=THEME["card"], pady=8)
        prev_frame.pack(fill="x", padx=12, pady=(0, 10))
        self._label(prev_frame, "Preview").pack(anchor="w", padx=8)

        nav = tk.Frame(prev_frame, bg=THEME["card"])
        nav.pack(fill="x", padx=8, pady=(4, 0))
        self._btn(nav, "◀ Prev", self._prev_preview, small=True).pack(side="left")
        self._btn(nav, "Next ▶", self._next_preview, small=True).pack(side="left", padx=(4, 0))
        self.preview_info = tk.Label(nav, text="No image selected",
                                     bg=THEME["card"], fg=THEME["subtext"],
                                     font=("Segoe UI", 8))
        self.preview_info.pack(side="left", padx=10)
        self._btn(nav, "✕ Remove", self._remove_current, small=True).pack(side="right")

        self.preview_label = tk.Label(prev_frame, bg=THEME["card"])
        self.preview_label.pack(pady=6)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _card(self, parent, pady=8):
        f = tk.Frame(parent, bg=THEME["card"], padx=10, pady=pady,
                     bd=1, relief="flat")
        return f

    def _label(self, parent, text):
        return tk.Label(parent, text=text, font=("Segoe UI", 9, "bold"),
                        bg=parent.cget("bg"), fg=THEME["text"])

    def _btn(self, parent, text, cmd, accent=False, small=False):
        bg = THEME["accent"] if accent else THEME["accent2"]
        font = ("Segoe UI", 9) if small else ("Segoe UI", 10, "bold")
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=THEME["text"], relief="flat",
                      activebackground=THEME["accent"], activeforeground="white",
                      font=font, cursor="hand2", padx=8, pady=4)
        b.bind("<Enter>", lambda e: b.config(bg=THEME["accent"]))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Horizontal.TProgressbar",
                         troughcolor=THEME["border"],
                         background=THEME["accent"])
        style.configure("Vertical.TScrollbar",
                         background=THEME["card"],
                         troughcolor=THEME["surface"],
                         arrowcolor=THEME["text"])

    # ── file management ────────────────────────────────────────────────────────
    def _pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image files",
                        " ".join(f"*{e}" for e in SUPPORTED_IN)),
                       ("All files", "*.*")])
        self._add_paths([Path(p) for p in paths])

    def _pick_folder(self):
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            imgs = [p for p in Path(folder).rglob("*")
                    if p.suffix.lower() in SUPPORTED_IN]
            self._add_paths(imgs)

    def _pick_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir.set(folder)

    def _on_drop(self, event):
        # tkinterdnd2 returns a string like: {/path/with spaces} /simple/path
        raw = event.data
        paths = []
        # parse braces
        import re
        for m in re.finditer(r'\{([^}]+)\}', raw):
            paths.append(Path(m.group(1)))
            raw = raw.replace(m.group(0), "")
        for p in raw.split():
            if p:
                paths.append(Path(p))
        expanded = []
        for p in paths:
            if p.is_dir():
                expanded += [f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED_IN]
            elif p.suffix.lower() in SUPPORTED_IN:
                expanded.append(p)
        self._add_paths(expanded)

    def _add_paths(self, paths: list[Path]):
        existing = {str(f) for f in self.files}
        new = [p for p in paths if str(p) not in existing]
        self.files.extend(new)
        self._refresh_thumbnails()
        self._set_status(f"{len(self.files)} image(s) in queue")

    def _clear_all(self):
        self.files.clear()
        self.thumb_cache.clear()
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.preview_label.config(image="", text="")
        self.preview_info.config(text="No image selected")
        self.queue_label.config(text="Queue (0 files)")
        self._set_status("Queue cleared")

    def _remove_current(self):
        if not self.files:
            return
        idx = max(0, min(self.current_preview_idx, len(self.files) - 1))
        removed = self.files.pop(idx)
        self.thumb_cache.pop(str(removed), None)
        self.current_preview_idx = max(0, idx - 1)
        self._refresh_thumbnails()
        self._show_preview(self.current_preview_idx)
        self._set_status(f"Removed {removed.name}")

    # ── thumbnail grid ─────────────────────────────────────────────────────────
    def _refresh_thumbnails(self):
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        self.queue_label.config(text=f"Queue ({len(self.files)} files)")
        cols = 4
        for i, fp in enumerate(self.files):
            self._make_thumb_card(i, fp, cols)
        if self.files:
            self._show_preview(self.current_preview_idx)

    def _make_thumb_card(self, idx, fp: Path, cols):
        row, col = divmod(idx, cols)
        card = tk.Frame(self.thumb_inner, bg=THEME["card"],
                        padx=4, pady=4, cursor="hand2")
        card.grid(row=row, column=col, padx=4, pady=4, sticky="nw")

        # thumbnail image
        img_lbl = tk.Label(card, bg=THEME["card"])
        img_lbl.pack()
        threading.Thread(target=self._load_thumb,
                         args=(fp, img_lbl, idx), daemon=True).start()

        # filename label
        name = fp.name if len(fp.name) <= 16 else fp.name[:13] + "…"
        tk.Label(card, text=name, bg=THEME["card"], fg=THEME["subtext"],
                 font=("Segoe UI", 7), wraplength=90).pack()

        # remove button
        tk.Button(card, text="✕", bg=THEME["accent"], fg="white",
                  relief="flat", font=("Segoe UI", 7), cursor="hand2",
                  command=lambda i=idx: self._remove_by_idx(i)).pack()

        card.bind("<Button-1>", lambda e, i=idx: self._show_preview(i))
        img_lbl.bind("<Button-1>", lambda e, i=idx: self._show_preview(i))

    def _load_thumb(self, fp: Path, label, idx):
        key = str(fp)
        if key not in self.thumb_cache:
            try:
                im = Image.open(fp)
                im.thumbnail((90, 90))
                ph = ImageTk.PhotoImage(im)
                self.thumb_cache[key] = ph
            except Exception:
                return
        else:
            ph = self.thumb_cache[key]
        self.root.after(0, lambda: label.config(image=ph))

    def _remove_by_idx(self, idx):
        if 0 <= idx < len(self.files):
            self.thumb_cache.pop(str(self.files[idx]), None)
            self.files.pop(idx)
            self.current_preview_idx = max(0, idx - 1)
            self._refresh_thumbnails()

    # ── preview ────────────────────────────────────────────────────────────────
    def _show_preview(self, idx):
        if not self.files:
            return
        idx = max(0, min(idx, len(self.files) - 1))
        self.current_preview_idx = idx
        fp = self.files[idx]
        try:
            im = Image.open(fp)
            im.thumbnail((320, 200))
            ph = ImageTk.PhotoImage(im)
            self._preview_ph = ph  # keep ref
            self.preview_label.config(image=ph, text="")
            size_kb = fp.stat().st_size // 1024
            self.preview_info.config(
                text=f"{fp.name}  |  {im.size[0]}×{im.size[1]}  |  {size_kb} KB  [{idx+1}/{len(self.files)}]"
            )
        except Exception as e:
            self.preview_label.config(text=f"Cannot preview\n{e}", image="")

    def _prev_preview(self):
        self._show_preview(self.current_preview_idx - 1)

    def _next_preview(self):
        self._show_preview(self.current_preview_idx + 1)

    def _on_format_change(self):
        q = QUALITY_MAP.get(self.format_var.get(), 85)
        self.quality_var.set(q)

    # ── conversion ─────────────────────────────────────────────────────────────
    def _start_convert(self):
        if not self.files:
            messagebox.showwarning("No Images", "Please add images first.")
            return
        threading.Thread(target=self._convert_worker, daemon=True).start()

    def _convert_worker(self):
        fmt = self.format_var.get()
        quality = self.quality_var.get()
        prefix = self.prefix_var.get().strip()
        keep_name = self.keep_name_var.get()
        overwrite = self.overwrite_var.get()
        out_root = self.output_dir.get().strip()
        ext = "." + fmt.lower()

        total = len(self.files)
        done = 0
        errors = []

        self.root.after(0, lambda: self.progress.config(maximum=total, value=0))

        for fp in list(self.files):
            try:
                # determine output path
                if out_root:
                    out_dir = Path(out_root)
                else:
                    out_dir = fp.parent

                out_dir.mkdir(parents=True, exist_ok=True)

                stem = fp.stem if keep_name else f"img_{done+1:04d}"
                out_name = (prefix + stem) + ext
                out_path = out_dir / out_name

                if out_path.exists() and not overwrite:
                    base = out_path.stem
                    counter = 1
                    while out_path.exists():
                        out_path = out_dir / f"{base}_{counter}{ext}"
                        counter += 1

                img = Image.open(fp)

                # convert mode for formats that don't support alpha
                if fmt in ("JPEG", "BMP") and img.mode in ("RGBA", "P", "LA"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                    img = bg
                elif img.mode == "P":
                    img = img.convert("RGBA")

                save_kwargs = {}
                if fmt == "WebP":
                    save_kwargs = {"quality": quality, "method": 6, "optimize": True}
                elif fmt == "AVIF":
                    save_kwargs = {"quality": quality}
                elif fmt == "JPEG":
                    save_kwargs = {"quality": quality, "optimize": True, "progressive": True}
                elif fmt == "PNG":
                    save_kwargs = {"optimize": True}
                elif fmt == "TIFF":
                    save_kwargs = {"compression": "tiff_lzw"}

                img.save(out_path, format=fmt if fmt != "TIFF" else "TIFF", **save_kwargs)
                done += 1

            except Exception as e:
                errors.append(f"{fp.name}: {e}")

            self.root.after(0, lambda v=done: self.progress.config(value=v))
            self.root.after(0, lambda v=done: self._set_status(
                f"Converting… {v}/{total}"))

        # done
        msg = f"✅ Converted {done}/{total} images to {fmt}"
        if errors:
            msg += f"\n⚠ {len(errors)} error(s):\n" + "\n".join(errors[:5])
        self.root.after(0, lambda: self._set_status(f"Done! {done}/{total} converted"))
        self.root.after(0, lambda: messagebox.showinfo("Conversion Complete", msg))

    def _set_status(self, text):
        self.status_var.set(text)


# ── entry point ───────────────────────────────────────────────────────────────
def main():
    if DND_AVAILABLE:
        root = tkdnd.Tk()
    else:
        root = tk.Tk()

    app = ImageConverterApp(root)

    # center window
    root.update_idletasks()
    w, h = root.winfo_width(), root.winfo_height()
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"+{x}+{y}")

    root.mainloop()


if __name__ == "__main__":
    main()

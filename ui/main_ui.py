"""Interfaz principal: selección/drag&drop de uno o varios SVG, opciones y conversión."""
from __future__ import annotations

import threading
import tkinter as tk
from functools import partial
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox

import customtkinter as ctk
from PIL import Image
from tkinterdnd2 import DND_FILES, TkinterDnD

from core.converter import (
    ConversionError,
    ConversionOptions,
    DEFAULT_SIZES,
    SUPPORTED_FORMATS,
    convert_svg,
    load_drawing,
    render_rgba,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

PREVIEW_PX = 220
FILE_LIST_HEIGHT = 90


class App(ctk.CTk, TkinterDnD.DnDWrapper):
    """CTk + soporte drag&drop (mixin estándar de tkinterdnd2)."""

    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)

        self.title("SVG Converter")
        self.geometry("880x680")
        self.minsize(760, 600)

        self.svg_paths: list[Path] = []
        self.output_dir: Path | None = None
        self.bg_color = "#FFFFFF"
        self.format_vars: dict[str, tk.BooleanVar] = {}
        self.size_vars: dict[int, tk.BooleanVar] = {}
        self._preview_img_ref: ctk.CTkImage | None = None

        self._build_layout()

    # ---------- layout ----------
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_drop_zone()
        self._build_options_panel()
        self._build_log_panel()

    def _build_drop_zone(self):
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.grid(row=0, column=0, rowspan=2, padx=16, pady=16, sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="Archivos SVG", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 4), sticky="w"
        )

        self.drop_label = ctk.CTkLabel(
            frame,
            text="Arrastra uno o varios .svg aquí\no haz clic para seleccionar",
            width=PREVIEW_PX,
            height=PREVIEW_PX,
            fg_color=("gray85", "gray20"),
            corner_radius=12,
            justify="center",
        )
        self.drop_label.grid(row=1, column=0, padx=12, pady=8)
        self.drop_label.bind("<Button-1>", lambda _e: self.browse_files())

        self.drop_label.drop_target_register(DND_FILES)
        self.drop_label.dnd_bind("<<Drop>>", self._on_drop)

        self.file_count_label = ctk.CTkLabel(frame, text="Ningún archivo seleccionado", wraplength=PREVIEW_PX)
        self.file_count_label.grid(row=2, column=0, padx=12, pady=(0, 4))

        self.file_list_frame = ctk.CTkScrollableFrame(frame, height=FILE_LIST_HEIGHT, fg_color=("gray90", "gray17"))
        self.file_list_frame.grid(row=3, column=0, padx=12, pady=(0, 8), sticky="ew")
        self.file_list_frame.grid_columnconfigure(0, weight=1)

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(btn_row, text="Agregar archivos...", command=self.browse_files).grid(
            row=0, column=0, padx=(0, 4), sticky="ew"
        )
        ctk.CTkButton(btn_row, text="Limpiar", fg_color="gray40", hover_color="gray30", command=self.clear_files).grid(
            row=0, column=1, padx=(4, 0), sticky="ew"
        )

        ctk.CTkLabel(frame, text="Carpeta de salida", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=5, column=0, padx=12, pady=(8, 2), sticky="w"
        )
        self.output_dir_label = ctk.CTkLabel(
            frame, text="(carpeta del SVG)/convertidos", wraplength=PREVIEW_PX, justify="left"
        )
        self.output_dir_label.grid(row=6, column=0, padx=12, pady=(0, 4), sticky="w")
        out_btn = ctk.CTkButton(frame, text="Cambiar carpeta...", command=self.browse_output_dir)
        out_btn.grid(row=7, column=0, padx=12, pady=(0, 12), sticky="ew")

    def _build_options_panel(self):
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(frame, text="Formatos de salida", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky="w"
        )
        for i, fmt in enumerate(SUPPORTED_FORMATS):
            var = tk.BooleanVar(value=True)
            self.format_vars[fmt] = var
            ctk.CTkCheckBox(frame, text=fmt, variable=var).grid(
                row=1 + i // 2, column=i % 2, padx=12, pady=4, sticky="w"
            )

        row = 3
        ctk.CTkLabel(frame, text="Tamaños (px, lado mayor)", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(16, 4), sticky="w"
        )
        row += 1
        for i, size in enumerate(DEFAULT_SIZES):
            var = tk.BooleanVar(value=True)
            self.size_vars[size] = var
            ctk.CTkCheckBox(frame, text=f"{size}px", variable=var).grid(
                row=row + i // 2, column=i % 2, padx=12, pady=4, sticky="w"
            )
        row += (len(DEFAULT_SIZES) + 1) // 2

        ctk.CTkLabel(frame, text="Fondo", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=row, column=0, columnspan=2, padx=12, pady=(16, 4), sticky="w"
        )
        row += 1
        self.transparent_var = tk.BooleanVar(value=True)
        ctk.CTkCheckBox(frame, text="Fondo transparente", variable=self.transparent_var).grid(
            row=row, column=0, columnspan=2, padx=12, pady=4, sticky="w"
        )
        row += 1

        color_row = ctk.CTkFrame(frame, fg_color="transparent")
        color_row.grid(row=row, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")
        ctk.CTkLabel(color_row, text="Color (si desactivas transparencia, y para JPG):").pack(
            side="left", padx=(0, 8)
        )
        self.color_swatch = ctk.CTkButton(
            color_row, text="", width=32, height=24, fg_color=self.bg_color, command=self.pick_color
        )
        self.color_swatch.pack(side="left")
        row += 1

        self.convert_btn = ctk.CTkButton(
            frame, text="Convertir", height=40, font=ctk.CTkFont(size=15, weight="bold"), command=self.start_conversion
        )
        self.convert_btn.grid(row=row, column=0, columnspan=2, padx=12, pady=(16, 12), sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=row + 1, column=0, columnspan=2, padx=12, pady=(0, 12), sticky="ew")

    def _build_log_panel(self):
        frame = ctk.CTkFrame(self, corner_radius=12)
        frame.grid(row=1, column=1, padx=(0, 16), pady=(0, 16), sticky="nsew")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Resultado", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, padx=12, pady=(12, 4), sticky="w"
        )
        self.log_box = ctk.CTkTextbox(frame, state="disabled", wrap="word")
        self.log_box.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="nsew")

        self.open_folder_btn = ctk.CTkButton(
            frame, text="Abrir carpeta de salida", command=self.open_output_folder, state="disabled"
        )
        self.open_folder_btn.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="ew")

    # ---------- helpers ----------
    def pick_color(self):
        _, hex_color = colorchooser.askcolor(color=self.bg_color, title="Elegir color de fondo")
        if hex_color:
            self.bg_color = hex_color
            self.color_swatch.configure(fg_color=hex_color)

    def log(self, message: str):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ---------- file selection ----------
    def _on_drop(self, event):
        paths = [Path(p) for p in self.tk.splitlist(event.data)]
        self._add_svgs(paths)

    def browse_files(self):
        paths = filedialog.askopenfilenames(title="Seleccionar SVG", filetypes=[("SVG", "*.svg")])
        if paths:
            self._add_svgs([Path(p) for p in paths])

    def browse_output_dir(self):
        path = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if path:
            self.output_dir = Path(path)
            self.output_dir_label.configure(text=str(self.output_dir))

    def clear_files(self):
        self.svg_paths = []
        self._refresh_file_list()
        self.drop_label.configure(image=None, text="Arrastra uno o varios .svg aquí\no haz clic para seleccionar")
        self._preview_img_ref = None
        self.file_count_label.configure(text="Ningún archivo seleccionado")
        if self.output_dir is None:
            self.output_dir_label.configure(text="(carpeta del SVG)/convertidos")

    def _add_svgs(self, paths: list[Path]):
        invalid = [p for p in paths if p.suffix.lower() != ".svg"]
        valid = [p for p in paths if p.suffix.lower() == ".svg"]
        if invalid:
            messagebox.showwarning(
                "Archivos ignorados",
                "Estos archivos no son .svg y fueron ignorados:\n" + "\n".join(p.name for p in invalid),
            )
        existing = {p.resolve() for p in self.svg_paths}
        added_first = None
        for p in valid:
            if p.resolve() in existing:
                continue
            self.svg_paths.append(p)
            existing.add(p.resolve())
            if added_first is None:
                added_first = p

        if not self.svg_paths:
            return

        self._refresh_file_list()

        if self.output_dir is None:
            self.output_dir_label.configure(text=str(self.svg_paths[0].parent / "convertidos"))

        # la preview muestra siempre el primer archivo de la lista
        try:
            drawing = load_drawing(self.svg_paths[0])
            preview = render_rgba(drawing, PREVIEW_PX)
        except ConversionError as exc:
            messagebox.showerror("Error al leer el SVG", f"{self.svg_paths[0].name}: {exc}")
            return

        checker = Image.new("RGBA", preview.size, (255, 255, 255, 255))
        checker.alpha_composite(preview)
        ctk_img = ctk.CTkImage(light_image=checker, dark_image=checker, size=preview.size)
        self._preview_img_ref = ctk_img
        self.drop_label.configure(image=ctk_img, text="")

    def _remove_svg(self, path: Path):
        self.svg_paths = [p for p in self.svg_paths if p != path]
        self._refresh_file_list()
        if not self.svg_paths:
            self.clear_files()
        elif self.output_dir is None:
            self.output_dir_label.configure(text=str(self.svg_paths[0].parent / "convertidos"))

    def _refresh_file_list(self):
        for child in self.file_list_frame.winfo_children():
            child.destroy()
        for path in self.svg_paths:
            row = ctk.CTkFrame(self.file_list_frame, fg_color="transparent")
            row.grid_columnconfigure(0, weight=1)
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=path.name, anchor="w").grid(row=0, column=0, sticky="ew")
            ctk.CTkButton(
                row, text="✕", width=22, height=22, fg_color="transparent", hover_color="gray30",
                command=partial(self._remove_svg, path),
            ).grid(row=0, column=1)

        n = len(self.svg_paths)
        if n == 0:
            self.file_count_label.configure(text="Ningún archivo seleccionado")
        elif n == 1:
            self.file_count_label.configure(text="1 archivo seleccionado")
        else:
            self.file_count_label.configure(text=f"{n} archivos seleccionados")

    # ---------- conversion ----------
    def start_conversion(self):
        if not self.svg_paths:
            messagebox.showwarning("Faltan SVG", "Selecciona o arrastra al menos un archivo .svg primero.")
            return

        formats = tuple(f for f, v in self.format_vars.items() if v.get())
        sizes = tuple(s for s, v in self.size_vars.items() if v.get())
        if not formats:
            messagebox.showwarning("Sin formatos", "Selecciona al menos un formato de salida.")
            return
        if not sizes:
            messagebox.showwarning("Sin tamaños", "Selecciona al menos un tamaño.")
            return

        output_dir = self.output_dir or (self.svg_paths[0].parent / "convertidos")
        svg_paths = list(self.svg_paths)
        transparent = self.transparent_var.get()
        bg_color = self.bg_color

        self.clear_log()
        self.convert_btn.configure(state="disabled", text="Convirtiendo...")
        self.open_folder_btn.configure(state="disabled")
        self.progress_bar.set(0)
        self._last_output_dir = output_dir

        steps_per_file = len(sizes) * len([f for f in formats if f != "ICO"]) + (1 if "ICO" in formats else 0)
        progress_state = {"done": 0, "total": max(steps_per_file * len(svg_paths), 1)}

        def progress_cb(msg: str):
            progress_state["done"] += 1
            self.after(0, self._on_progress, msg, progress_state["done"], progress_state["total"])

        def worker():
            total_outputs: list[Path] = []
            total_errors: list[str] = []
            for svg_path in svg_paths:
                self.after(0, self.log, f"\n— {svg_path.name} —")
                options = ConversionOptions(
                    formats=formats,
                    sizes=sizes,
                    transparent=transparent,
                    bg_color=bg_color,
                    output_dir=output_dir,
                    base_name=svg_path.stem,
                )
                try:
                    result = convert_svg(svg_path, options, progress_callback=progress_cb)
                    total_outputs.extend(result.outputs)
                    total_errors.extend(f"{svg_path.name}: {e}" for e in result.errors)
                except ConversionError as exc:
                    total_errors.append(f"{svg_path.name}: {exc}")
            self.after(0, self._on_conversion_done, total_outputs, total_errors)

        threading.Thread(target=worker, daemon=True).start()

    def _on_progress(self, msg: str, done: int, total: int):
        self.log(msg)
        self.progress_bar.set(min(done / total, 1.0))

    def _on_conversion_done(self, outputs: list[Path], errors: list[str]):
        self.convert_btn.configure(state="normal", text="Convertir")
        self.progress_bar.set(1.0)
        if errors:
            for err in errors:
                self.log(f"ERROR: {err}")
        self.log(f"\nListo: {len(outputs)} archivo(s) generado(s) en {self._last_output_dir}")
        if outputs:
            self.open_folder_btn.configure(state="normal")

    def open_output_folder(self):
        import os

        if self._last_output_dir and self._last_output_dir.exists():
            os.startfile(str(self._last_output_dir))  # noqa: S606 (acción local, sin datos externos)


def run():
    app = App()
    app.mainloop()

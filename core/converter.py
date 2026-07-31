"""Conversion engine: SVG -> PNG/ICO/JPG/WEBP en uno o varios tamaños.

Usa svglib+reportlab (backend rlPyCairo) para rasterizar el SVG a un PIL.Image
RGBA de alta calidad, y Pillow para el resto de formatos y el resize por tamaño.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from PIL import Image
from reportlab.graphics import renderPM
from reportlab.lib.colors import Color, toColor
from svglib.svglib import svg2rlg

SUPPORTED_FORMATS = ("PNG", "ICO", "JPG", "WEBP")
DEFAULT_SIZES = (16, 32, 64, 128, 256, 512, 1024)
ICO_MAX_SIZE = 256
HEX_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_GRADIENT_REF_RE = re.compile(r"url\(#([^)]+)\)")


class ConversionError(Exception):
    """Error al cargar o rasterizar un SVG."""


@dataclass
class ConversionOptions:
    formats: tuple[str, ...]
    sizes: tuple[int, ...]
    transparent: bool = True
    bg_color: str = "#FFFFFF"
    output_dir: Optional[Path] = None
    base_name: Optional[str] = None


@dataclass
class ConversionResult:
    outputs: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    m = HEX_RE.match(hex_color.strip())
    if not m:
        raise ConversionError(f"Color inválido: {hex_color!r} (usa formato #RRGGBB)")
    h = m.group(1)
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _parse_style_decls(style: str) -> dict[str, str]:
    decls = {}
    for part in style.split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            decls[k.strip()] = v.strip()
    return decls


def _stop_color(stop_el) -> Optional[Color]:
    style = _parse_style_decls(stop_el.get("style", ""))
    color_str = style.get("stop-color") or stop_el.get("stop-color") or "#000000"
    opacity_str = style.get("stop-opacity") or stop_el.get("stop-opacity") or "1"
    try:
        color = toColor(color_str.strip())
        opacity = float(opacity_str)
    except Exception:
        return None
    return Color(color.red, color.green, color.blue, opacity)


def _average_color_hex(stops: list) -> str:
    colors = [c for c in (_stop_color(s) for s in stops) if c is not None]
    if not colors:
        return "#808080"
    r = sum(c.red for c in colors) / len(colors)
    g = sum(c.green for c in colors) / len(colors)
    b = sum(c.blue for c in colors) / len(colors)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def flatten_gradients(svg_bytes: bytes) -> bytes:
    """svglib/reportlab no soporta gradientes al rasterizar vía renderPM (solo al
    exportar PDF): un fill/stroke con url(#gradiente) hace crashear el backend
    rlPyCairo. Como workaround, se reemplaza cada gradiente por el color sólido
    promedio de sus stops antes de pasarle el SVG a svglib."""
    try:
        root = ET.fromstring(svg_bytes)
    except ET.ParseError:
        return svg_bytes

    gradient_colors: dict[str, str] = {}
    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag in ("linearGradient", "radialGradient"):
            grad_id = el.get("id")
            if not grad_id:
                continue
            stops = [c for c in el if c.tag.split("}")[-1] == "stop"]
            gradient_colors[grad_id] = _average_color_hex(stops)

    if not gradient_colors:
        return svg_bytes

    def _replace(match: re.Match) -> str:
        return gradient_colors.get(match.group(1), match.group(0))

    changed = False
    for el in root.iter():
        for attr in ("fill", "stroke", "style"):
            val = el.get(attr)
            if val and "url(#" in val:
                new_val = _GRADIENT_REF_RE.sub(_replace, val)
                if new_val != val:
                    el.set(attr, new_val)
                    changed = True

    if not changed:
        return svg_bytes
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def load_drawing(svg_path: Path):
    svg_path = Path(svg_path)
    try:
        original_bytes = svg_path.read_bytes()
        flattened_bytes = flatten_gradients(original_bytes)
    except Exception as exc:
        raise ConversionError(f"No se pudo leer el SVG: {exc}") from exc

    tmp_path = None
    source = svg_path
    if flattened_bytes != original_bytes:
        try:
            tmp_path = svg_path.with_name(f".{svg_path.stem}.flattened.svg")
            tmp_path.write_bytes(flattened_bytes)
        except OSError:
            import tempfile

            fd, tmp_name = tempfile.mkstemp(suffix=".svg")
            with open(fd, "wb") as f:
                f.write(flattened_bytes)
            tmp_path = Path(tmp_name)
        source = tmp_path

    try:
        drawing = svg2rlg(str(source))
    except Exception as exc:  # svglib lanza excepciones variadas según el parser XML
        raise ConversionError(f"No se pudo leer el SVG: {exc}") from exc
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)

    if drawing is None or not drawing.width or not drawing.height:
        raise ConversionError("El SVG no tiene dimensiones válidas (width/height/viewBox).")
    return drawing


def render_rgba(drawing, target_px: int) -> Image.Image:
    """Rasteriza el drawing a un PIL.Image RGBA cuyo lado mayor mide target_px."""
    scale = target_px / max(drawing.width, drawing.height)
    dpi = 72.0 * scale
    transparent_bg = Color(0, 0, 0, alpha=0)
    img = renderPM.drawToPIL(drawing, dpi=dpi, bg=transparent_bg, backendFmt="RGBA")
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def flatten(img_rgba: Image.Image, rgb_color: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGB", img_rgba.size, rgb_color)
    base.paste(img_rgba, mask=img_rgba.split()[3])
    return base


def pad_to_square(img_rgba: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - img_rgba.width) // 2
    y = (size - img_rgba.height) // 2
    canvas.paste(img_rgba, (x, y), img_rgba)
    return canvas


def _save_raster(
    img_rgba: Image.Image,
    fmt: str,
    path: Path,
    transparent: bool,
    bg_rgb: tuple[int, int, int],
) -> None:
    if fmt == "PNG":
        img_rgba.save(path, format="PNG")
    elif fmt == "WEBP":
        out = img_rgba if transparent else flatten(img_rgba, bg_rgb)
        out.save(path, format="WEBP", lossless=True)
    elif fmt == "JPG":
        # JPG no soporta alfa: si transparent=True se rellena en blanco.
        out = flatten(img_rgba, bg_rgb if not transparent else (255, 255, 255))
        out.save(path, format="JPEG", quality=95)
    else:
        raise ConversionError(f"Formato no soportado: {fmt}")


def convert_svg(
    svg_path: Path,
    options: ConversionOptions,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> ConversionResult:
    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise ConversionError(f"No existe el archivo: {svg_path}")

    formats = tuple(f.upper() for f in options.formats) or ("PNG",)
    for f in formats:
        if f not in SUPPORTED_FORMATS:
            raise ConversionError(f"Formato no soportado: {f}")

    sizes = tuple(sorted(set(int(s) for s in options.sizes))) or DEFAULT_SIZES
    output_dir = Path(options.output_dir) if options.output_dir else svg_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = options.base_name or svg_path.stem
    bg_rgb = hex_to_rgb(options.bg_color)

    result = ConversionResult()
    drawing = load_drawing(svg_path)

    raster_formats = [f for f in formats if f in ("PNG", "JPG", "WEBP")]
    for size in sizes:
        try:
            img = render_rgba(drawing, size)
        except Exception as exc:
            result.errors.append(f"Tamaño {size}px: {exc}")
            continue
        for fmt in raster_formats:
            ext = "jpg" if fmt == "JPG" else fmt.lower()
            out_path = output_dir / f"{base_name}_{size}px.{ext}"
            try:
                _save_raster(img, fmt, out_path, options.transparent, bg_rgb)
                result.outputs.append(out_path)
                if progress_callback:
                    progress_callback(f"{out_path.name} generado")
            except Exception as exc:
                result.errors.append(f"{out_path.name}: {exc}")

    if "ICO" in formats:
        ico_sizes = tuple(s for s in sizes if s <= ICO_MAX_SIZE) or (min(sizes, default=256),)
        base_size = max(ico_sizes)
        try:
            base_img = render_rgba(drawing, base_size)
            base_img = pad_to_square(base_img, base_size)
            if not options.transparent:
                base_img = flatten(base_img, bg_rgb)
                base_img = base_img.convert("RGBA")
            ico_path = output_dir / f"{base_name}.ico"
            base_img.save(ico_path, format="ICO", sizes=[(s, s) for s in ico_sizes])
            result.outputs.append(ico_path)
            if progress_callback:
                progress_callback(f"{ico_path.name} generado ({len(ico_sizes)} tamaños)")
        except Exception as exc:
            result.errors.append(f"ICO: {exc}")

    return result

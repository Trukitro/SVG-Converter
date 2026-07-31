# AGENTS.md

## Proyecto
SVG Converter es una app de escritorio Python para convertir archivos `.svg` a
`PNG`, `ICO`, `JPG` y `WEBP` en uno o varios tamaños a la vez, pensada para
generar sets de íconos y logos en alta calidad. Usa:
- `customtkinter` + `tkinterdnd2` para la UI (drag&drop + selección manual)
- `svglib` + `reportlab` (backend `rlPyCairo`) para rasterizar el SVG
- `Pillow` para el resto de formatos, el resize por tamaño y el empaquetado `.ico`

## Estructura
- `svg_converter_app.py`: launcher principal
- `core/converter.py`: lógica de conversión (sin dependencias de UI)
- `ui/main_ui.py`: interfaz principal (CTk + drag&drop)

## Reglas para Codex
- Mantener arquitectura modular: lógica de conversión en `core/`, UI en `ui/`.
- `core/converter.py` no debe importar nada de `tkinter`/`customtkinter` — debe
  poder probarse con un script plano (`python -c "from core.converter import ..."`).
- No mover lógica de rasterizado al archivo `svg_converter_app.py`.
- Las conversiones son CPU-bound: deben correr en un `threading.Thread` y actualizar
  la UI únicamente vía `self.after(0, ...)`, nunca desde el thread de fondo.
- Validar cambios con:
  `python -m py_compile svg_converter_app.py core/converter.py ui/main_ui.py`
- Este es el repo público (SVG Converter). No incluir SVGs, logos ni assets de
  ningún cliente o entorno de trabajo real — solo ejemplos genéricos.

## Estilo
- Código claro, simple y compatible con Windows.
- Mensajes de UI en español.
- Evitar dependencias nuevas salvo que sean necesarias.

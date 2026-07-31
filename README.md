# SVG Converter

**SVG Converter** es una herramienta de escritorio para convertir archivos `.svg`
a `PNG`, `ICO`, `JPG` y `WEBP`, en uno o varios tamaños a la vez (16 a 1024px),
pensada para generar íconos y logos en la mejor calidad posible a partir de un
único vector fuente.

Repo: https://github.com/Trukitro/SVG-Converter

## 🚀 Arquitectura del Proyecto
- **`core/converter.py`**: motor de conversión (svglib + reportlab/rlPyCairo + Pillow),
  sin dependencias de UI.
- **`ui/main_ui.py`**: interfaz principal con `CustomTkinter`, drag&drop de archivos
  vía `tkinterdnd2`.
- **`svg_converter_app.py`**: punto de entrada (launcher).

## 🛠️ Características
- Selección de **uno o varios archivos** por diálogo o **drag & drop** directo (arrastra varios `.svg` a la vez).
- Exportación simultánea a **PNG, ICO, JPG y WEBP**.
- **Multi-tamaño en una sola pasada**: 16/32/64/128/256/512/1024px (o solo los que elijas).
- **Fondo transparente por defecto**, con opción de fijar un color sólido
  (selector de color) — se usa automáticamente como respaldo para JPG, que no
  soporta transparencia.
- `.ico` con múltiples resoluciones embebidas en un solo archivo.
- Conversión en segundo plano (no congela la UI) con barra de progreso y log.

## 📦 Instalación
1. Clonar el repositorio.
2. Instalar dependencias: `pip install -r requirements.txt`.
3. Ejecutar: `python svg_converter_app.py`.

## 📥 Descarga
También puedes descargar el instalador `.exe` (Windows) desde la sección
[Releases](https://github.com/Trukitro/SVG-Converter/releases) del repo —
generado con PyInstaller + Inno Setup, no requiere tener Python instalado.

## 🏗️ Compilar el ejecutable (dev)
```
pip install pyinstaller
pyinstaller SVG-Converter.spec
```
El `.exe` queda en `dist/SVG-Converter/`. Para generar el instalador de Windows,
compila `installer/setup.iss` con Inno Setup (`ISCC installer/setup.iss`).

## ⚠️ Limitaciones conocidas
- **Gradientes** (`linearGradient`/`radialGradient`): el backend de rasterizado
  (svglib + reportlab + rlPyCairo) no los soporta al exportar a PNG/ICO/JPG/WEBP
  (solo al exportar a PDF). Para no fallar, un `fill`/`stroke` con gradiente se
  reemplaza automáticamente por el color sólido promedio de sus stops antes de
  convertir — se pierde el degradado, pero la conversión no crashea.
- **Filtros** (`feGaussianBlur`, sombras, etc.): se ignoran silenciosamente; la
  forma se dibuja sin el efecto.

## 📚 Documentación
Ver [`docs/`](docs/) para roadmap, backlog y bugs conocidos.

## Estado
Proyecto público/portfolio. No incluye SVGs, logos ni datos de ningún cliente o
entorno de trabajo real — solo ejemplos genéricos.

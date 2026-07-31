# Checklist de release

1. `python -m py_compile svg_converter_app.py core/converter.py ui/main_ui.py`
2. Probar conversión manual con un SVG real (formatos + tamaños + transparencia).
3. Actualizar versión en `installer/setup.iss` (`MyAppVersion`).
4. `pyinstaller SVG-Converter.spec` → verificar que `dist/SVG-Converter/SVG-Converter.exe` arranca.
5. `ISCC installer/setup.iss` → verificar que el instalador generado en `Output/` instala y ejecuta la app.
6. Crear tag y release en GitHub (`gh release create vX.Y.Z Output/SVG-Converter-Setup.exe`).

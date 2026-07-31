# Backlog

- [x] Conversión por lote de varios `.svg` a la vez (multi-archivo, no solo multi-tamaño). — v1.1.0
- [ ] Renderizar gradientes de verdad (evaluar cairosvg si se resuelve la
  dependencia de `cairo-2.dll`/cairocffi en Windows) en vez de aplanarlos a
  color sólido — ver limitación conocida en README.
- [ ] Padding/margen configurable al exportar (actualmente el ícono se ajusta al lado mayor sin relleno).
- [ ] Soporte para exportar también a `PDF`/`SVG optimizado`.
- [ ] Guardar el último set de opciones usado (formatos/tamaños/color) entre sesiones.
- [ ] Modo CLI (`python -m core.converter archivo.svg --formats png,ico --sizes 16,32,256`) para automatizar sin abrir la GUI.

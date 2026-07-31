# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_all

datas = []
binaries = []
hiddenimports = []

datas += collect_data_files('customtkinter')
datas += collect_data_files('tkinterdnd2')

# reportlab necesita sus archivos de fuentes (AFM/T1) empaquetados para poder
# convertir <text> de un SVG a paths al rasterizar; los hooks estándar de
# PyInstaller no los incluyen y el .exe crashea solo en SVGs con texto
# ('NoneType' object has no attribute 'write'), aunque funcione perfecto
# corriendo desde el código fuente. collect_all trae también svglib completo.
for pkg in ("reportlab", "svglib"):
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(pkg)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

a = Analysis(
    ['svg_converter_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SVG-Converter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)

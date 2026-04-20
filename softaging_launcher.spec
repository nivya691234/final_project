# -*- mode: python ; coding: utf-8 -*-
"""
softaging_launcher.spec
-----------------------
PyInstaller specification for building SoftAgingAnalyzer.exe

Usage:
    pyinstaller softaging_launcher.spec

This produces:
    dist/SoftAgingAnalyzer.exe  (standalone executable)

Distribution:
    - Rename dist/ to SoftAgingAnalyzer/
    - Create installer with NSIS or similar
    - Users run SoftAgingAnalyzer.exe to launch the system
"""

block_cipher = None

a = Analysis(
    ["softaging_launcher.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("dashboard", "dashboard"),
        ("config", "config"),
        ("core", "core"),
        ("database", "database"),
        ("models", "models"),
    ],
    hiddenimports=[
        "psutil",
        "flask",
        "numpy",
        "scipy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="SoftAgingAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window (Windows tray app)
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="dashboard/static/icon.ico",  # Optional: path to icon file
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SoftAgingAnalyzer",
)

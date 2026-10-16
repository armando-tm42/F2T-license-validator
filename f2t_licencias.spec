# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

# Directorios de origen
root_dir = Path.cwd()
src_dir = root_dir / "src"

# Archivos de recursos y activos visuales a incluir
added_files = [
    (str(src_dir / "license_validator" / "gui" / "assets"), "license_validator/gui/assets"),
]

# Si existe .env en la raíz, incluirlo
if (root_dir / ".env").is_file():
    added_files.append((str(root_dir / ".env"), "."))

# Si existe public.pem en la raíz, incluirlo como respaldo local
if (root_dir / "public.pem").is_file():
    added_files.append((str(root_dir / "public.pem"), "."))

# Dependencias e importaciones dinámicas que PyInstaller debe rastrear
hidden_imports = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "sqlalchemy",
    "sqlalchemy.sql.default_comparator",
    "psycopg2",
    "psycopg2.extensions",
    "psycopg2.extras",
    "alembic",
    "bcrypt",
    "cryptography",
    "dotenv",
    "infisical_sdk",
]

a = Analysis(
    ['src/license_validator/main.py'],
    pathex=[str(src_dir)],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='F2T-Licencias',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Sin ventana negra de consola (modo ventana pura)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(src_dir / 'license_validator' / 'gui' / 'assets' / 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='F2T-Licencias',
)

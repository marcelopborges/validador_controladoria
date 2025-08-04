# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Determina o caminho base
if getattr(sys, 'frozen', False):
    base_path = Path(sys.executable).parent
else:
    base_path = Path(__file__).parent

# Configurações do PyInstaller
a = Analysis(
    ['interface_grafica.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src', 'src'),
        ('REGRAS_VALIDACAO.md', '.'),
        ('README.md', '.'),
        ('data/modelo_importacao.xlsx', 'data'),
        ('data/modelo_importacao.csv', 'data'),
        ('config', 'config'),
    ],
    hiddenimports=[
        'openpyxl',
        'xlrd',
        'pandas',
        'numpy',
        'flask',
        'werkzeug',
        'jinja2',
        'markdown',
        'google.cloud.bigquery',
        'google.oauth2.service_account',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        'PIL.ImageTk',
        'PIL.ImageOps',
        'PIL.ImageEnhance',
        'PIL.ImageFilter',
        'PIL.ImageGrab',
        'PIL.ImageMorph',
        'PIL.ImagePalette',
        'PIL.ImagePath',
        'PIL.ImageQt',
        'PIL.ImageSequence',
        'PIL.ImageShow',
        'PIL.ImageStat',
        'PIL.ImageTransform',
        'PIL.ImageWin',
        'PIL.ImageCms',
        'PIL.ImageColor',
        'PIL.ImageDraw2',
        'PIL.ImageFile',
        'PIL.ImageFilter',
        'PIL.ImageMath',
        'PIL.ImageMode',
        'PIL.ImageOps',
        'PIL.ImagePalette',
        'PIL.ImagePath',
        'PIL.ImageQt',
        'PIL.ImageSequence',
        'PIL.ImageShow',
        'PIL.ImageStat',
        'PIL.ImageTransform',
        'PIL.ImageWin',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove duplicatas dos hiddenimports
a.hiddenimports = list(set(a.hiddenimports))

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ImportadorControladoria',
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
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)

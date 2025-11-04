# -*- mode: python ; coding: utf-8 -*-
import sys
import os

is_windows = sys.platform.startswith("win")
codesign_identity = os.environ.get("CODESIGN_IDENTITY")

if codesign_identity:
    print("Using codesign_identity:", codesign_identity)
else:
    print("No codesign_identity set, skipping code signing.")
    codesign_identity = None  # 确保传给 EXE 时是 None

a = Analysis(
    ['opencontext/cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'), 
        ('opencontext/web/static', 'opencontext/web/static'), 
        ('opencontext/web/templates', 'opencontext/web/templates')
    ],
    hiddenimports=[
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets.auto',
        'chromadb.telemetry.product.posthog',
        'chromadb.api.rust',
        'chromadb.db.impl.sqlite',
        'chromadb.db.impl.grpc',
        'chromadb.segment.impl.vector.local_hnsw',
        'chromadb.segment.impl.metadata.sqlite',
        'hnswlib',
        'sqlite3',
        '_ssl',
        '_hashlib',
    ],
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['hook-opencontext.py'],
    excludes=[],
    noarchive=True,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=not is_windows,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    codesign_identity=codesign_identity,
    icon=None,  # Disable icon to avoid Windows resource locking issues
)

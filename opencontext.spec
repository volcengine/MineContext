# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

is_windows = sys.platform.startswith("win")

_numpy_hidden = collect_submodules('numpy')
_pandas_hidden = collect_submodules('pandas')
_numpy_datas = collect_data_files('numpy')
_pandas_datas = collect_data_files('pandas')

# ASGI/uvicorn family
_uvicorn_hidden = collect_submodules('uvicorn')
_starlette_hidden = collect_submodules('starlette')
_fastapi_hidden = collect_submodules('fastapi')
_anyio_hidden = collect_submodules('anyio')
_h11_hidden = collect_submodules('h11')
_websockets_hidden = collect_submodules('websockets')

a = Analysis(
    ['opencontext/cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.yaml', 'config'),
        ('opencontext/web/static', 'opencontext/web/static'),
        ('opencontext/web/templates', 'opencontext/web/templates'),
    ] + _numpy_datas + _pandas_datas,
    hiddenimports=[
        'uvicorn',
        'uvicorn.config',
        'uvicorn.server',
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
    ] + _numpy_hidden + _pandas_hidden + _uvicorn_hidden + _starlette_hidden + _fastapi_hidden + _anyio_hidden + _h11_hidden + _websockets_hidden,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['hook-opencontext.py'],
    excludes=[],
    noarchive=False,   # was True – this avoids importing numpy from a “source-like” dir
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
    codesign_identity=None,
    icon=None,  # Disable icon to avoid Windows resource locking issues
)

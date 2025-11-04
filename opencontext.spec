# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import base64
import subprocess
import tempfile
import random
import string
from pathlib import Path


def get_codesign_identity():
    csc_link_data = os.environ.get("CSC_LINK")
    csc_password = os.environ.get("CSC_KEY_PASSWORD")

    if not csc_link_data or not csc_password:
        return None

    if csc_link_data.startswith("data:application/x-pkcs12;base64,"):
        csc_link_data = csc_link_data.split(",", 1)[1]

    with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as f:
        p12_path = f.name
        f.write(base64.b64decode(csc_link_data))

    # ✅ 使用固定安全路径 + 后缀 .keychain-db
    keychain_dir = Path("/tmp")
    keychain_name = f"temp-sign-{os.getpid()}.keychain-db"
    keychain_path = str(keychain_dir / keychain_name)
    keychain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    try:
        # 创建并解锁 keychain
        subprocess.run(["security", "create-keychain", "-p", keychain_password, keychain_path], check=True)
        subprocess.run(["security", "unlock-keychain", "-p", keychain_password, keychain_path], check=True)

        # 导入证书
        subprocess.run([
            "security", "import", p12_path,
            "-k", keychain_path,
            "-P", csc_password,
            "-T", "/usr/bin/codesign"
        ], check=True)

        # 查找 identity
        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning", keychain_path],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if "Developer ID Application:" in line:
                return line.split('"')[1]

    finally:
        # ✅ 删除临时文件与 keychain
        subprocess.run(["security", "delete-keychain", keychain_path], check=False)
        os.unlink(p12_path)

    return None

is_windows = sys.platform.startswith("win")

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
    codesign_identity=get_codesign_identity(),
    icon=None,  # Disable icon to avoid Windows resource locking issues
)

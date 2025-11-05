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
    if not sys.platform.startswith("darwin"):
        print("Skipping codesign setup: not macOS.")
        return None
        
    csc_link_data = os.environ.get("CSC_LINK")
    csc_password = os.environ.get("CSC_KEY_PASSWORD")

    if not csc_link_data or not csc_password:
        print("No CSC_LINK or CSC_KEY_PASSWORD found, skipping codesign setup.")
        return None

    if csc_link_data.startswith("data:application/x-pkcs12;base64,"):
        csc_link_data = csc_link_data.split(",", 1)[1]

    with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as f:
        p12_path = f.name
        f.write(base64.b64decode(csc_link_data))

    keychain_dir = Path("/tmp")
    keychain_name = f"temp-sign-{os.getpid()}.keychain-db"
    keychain_path = str(keychain_dir / keychain_name)
    keychain_password = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    try:
        subprocess.run(["security", "create-keychain", "-p", keychain_password, keychain_path], check=True)
        subprocess.run(["security", "unlock-keychain", "-p", keychain_password, keychain_path], check=True)

        subprocess.run([
            "security", "import", p12_path,
            "-k", keychain_path,
            "-P", csc_password,
            "-T", "/usr/bin/codesign"
        ], check=True)

        # ✅ 确保 PyInstaller 子进程可见
        subprocess.run(["security", "list-keychains", "-d", "user", "-s", keychain_path], check=True)
        subprocess.run(["security", "default-keychain", "-d", "user", "-s", keychain_path], check=True)
        subprocess.run(["security", "set-keychain-settings", keychain_path], check=True)

        os.environ["KEYCHAIN_PATH"] = keychain_path
        # ✅ 正确导出到 GitHub Actions 环境
        github_env = os.environ.get("GITHUB_ENV")
        if github_env and os.path.exists(github_env):
            with open(github_env, "a") as f:
                f.write(f"KEYCHAIN_PATH={keychain_path}\n")

        print(f"✅ Keychain created: {keychain_path}")

        result = subprocess.run(
            ["security", "find-identity", "-v", "-p", "codesigning", keychain_path],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if "Developer ID Application:" in line:
                identity = line.split('"')[1]
                print(f"✅ Found identity: {identity}")
                return identity

    finally:
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

# -*- mode: python ; coding: utf-8 -*-

# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: Apache-2.0

block_cipher = None

a = Analysis(
    ['window_inspector.py'],        # 入口脚本
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # PyObjC 桥接层和动态加载的模块
        'Quartz',
        'Quartz.CoreGraphics',
        'AppKit',
        'Foundation',
        'CoreFoundation',
        'CoreServices',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='window_inspector',   # 生成的可执行文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,              # 如果你希望隐藏终端窗口改成 False
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='window_inspector'
)
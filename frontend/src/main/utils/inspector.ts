// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { BrowserWindow } from 'electron'

const openInspector = (window: BrowserWindow) => {
  // 使用应用内快捷键监听 F12
  window.webContents.on('before-input-event', (event, input) => {
    // 检测 F12 键（不需要修饰键）
    if (input.key === 'F12' && input.type === 'keyDown') {
      window.webContents.toggleDevTools()
      event.preventDefault()
    }
  })
}

export default openInspector

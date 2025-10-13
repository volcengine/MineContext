// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { globalShortcut, BrowserWindow } from 'electron'

const openInspector = () => {
  // const template = [
  //   {
  //     label: '开发',
  //     submenu: [
  //       {
  //         label: '开发者工具',
  //         accelerator: 'F12',
  //         click: (_item, focusedWindow) => {
  //           if (focusedWindow) {
  //             focusedWindow.webContents.openDevTools()
  //           }
  //         }
  //       }
  //     ]
  //   }
  // ]
  // const menu = Menu.buildFromTemplate(template)
  // Menu.setApplicationMenu(menu)

  // 注册全局快捷键
  globalShortcut.register('F12', () => {
    const focusedWindow = BrowserWindow.getFocusedWindow()
    if (focusedWindow) {
      focusedWindow.webContents.openDevTools()
    }
  })
}

export default openInspector

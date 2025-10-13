// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// don't reorder this file, it's used to initialize the app data dir and
// other which should be run before the main process is ready
// eslint-disable-next-line
import './bootstrap'

import '@main/config'

import { app, shell, BrowserWindow, protocol } from 'electron'
import path, { join } from 'path'
import fs from 'fs'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'

import { registerIpc } from './ipc'
import openInspector from './utils/inspector'
import db from './services/DatabaseService'
import { isDev } from './constant'
import icon from '../../resources/icon.png?asset'
import { ensureBackendRunning, startBackendInBackground, stopBackendServerSync } from './backend'
import { powerWatcher } from './background/os/Power'
import { initLog } from '@shared/logger/init'
import { getLogger } from '@shared/logger/main'
initLog()
const logger = getLogger('MainEntry')

const isPackaged = app.isPackaged
const actuallyDev = isDev && !isPackaged // true

// 保存原始的 console.log
const originalConsoleLog = console.log

function createWindow() {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1180,
    height: 660,
    show: false,
    autoHideMenuBar: true,
    ...(process.platform === 'linux' ? { icon } : {}),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      webSecurity: false
    }
  })

  console.log = (...args) => {
    try {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('main-log', ...args)
      } else {
        originalConsoleLog(...args)
      }
    } catch (error) {
      originalConsoleLog(...args)
    }
  }

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()

    if (!actuallyDev) {
      ensureBackendRunning(mainWindow).catch((error) => {
        logger.error('Failed to ensure backend is running:', error)
      })
    }
  })

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
  return mainWindow
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
let server: any
app.whenReady().then(() => {
  logger.info('app_started', { argv: process.argv, version: app.getVersion() })
  openInspector()

  protocol.registerBufferProtocol('vikingdb', (request, callback) => {
    try {
      let filePath = request.url.replace('vikingdb://', '')
      filePath = decodeURIComponent(filePath)

      const fullPath = path.resolve(filePath)

      console.log('读取文件:', fullPath)

      if (fs.existsSync(fullPath)) {
        const data = fs.readFileSync(fullPath)
        const extension = path.extname(fullPath).toLowerCase()

        // 根据文件类型设置MIME类型
        let mimeType = 'application/octet-stream'
        if (extension === '.png') mimeType = 'image/png'
        else if (extension === '.jpg' || extension === '.jpeg') mimeType = 'image/jpeg'
        else if (extension === '.gif') mimeType = 'image/gif'
        else if (extension === '.svg') mimeType = 'image/svg+xml'

        callback({
          mimeType: mimeType,
          data: data
        })
      } else {
        callback({ error: -6 })
      }
    } catch (error) {
      console.error('读取文件错误:', error)
      callback({ error: -2 })
    }
  })

  // Set app user model id for windows
  electronApp.setAppUserModelId('com.vikingdb.desktop')

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)

    // 在开发环境下自动打开 DevTools

    if (isDev) {
      window.webContents.openDevTools()
      console.log('DevTools opened automatically in development mode')
    }
  })

  const mainWindow = createWindow()
  powerWatcher.run(mainWindow)
  startBackendInBackground(mainWindow)

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })

  registerIpc(mainWindow, app)
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // 恢复原始的 console.log 以避免在退出过程中出现 "Object has been destroyed" 错误
    console.log = originalConsoleLog
    stopBackendServerSync()
    app.quit()
  }
})

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.

// in production mode, handle uncaught exception and unhandled rejection globally
if (!isDev) {
  // handle uncaught exception
  process.on('uncaughtException', (error) => {
    logger.error('Uncaught Exception:', error)
  })

  // handle unhandled rejection
  process.on('unhandledRejection', (reason, promise) => {
    logger.error(`Unhandled Rejection at: ${promise} reason: ${reason}`)
  })
}

app.on('before-quit', () => {
  // 恢复原始的 console.log 以避免在退出过程中出现 "Object has been destroyed" 错误
  console.log = originalConsoleLog

  if (server) {
    server.close()
  }
  stopBackendServerSync()
  db.close()
})

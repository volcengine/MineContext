// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { app, BrowserWindow, powerMonitor, powerSaveBlocker } from 'electron'

class Power {
  private blockerId?: number
  run(mainWindow: BrowserWindow) {
    this.blockerId = powerSaveBlocker.start('prevent-app-suspension')
    app.on('window-all-closed', () => {
      if (this.blockerId && powerSaveBlocker.isStarted(this.blockerId)) {
        powerSaveBlocker.stop(this.blockerId)
        console.log('🛑 powerSaveBlocker stopped')
      }
    })
    // Listen for macOS power events
    powerMonitor.on('suspend', () => {
      console.log('💤 System is about to sleep')
      mainWindow.webContents.send(IpcServerPushChannel.PushPowerMonitor, { key: 'suspend' })
    })

    powerMonitor.on('resume', () => {
      console.log('🌞 System has woken up')
      mainWindow.webContents.send(IpcServerPushChannel.PushPowerMonitor, { key: 'resume' })
    })

    powerMonitor.on('lock-screen', () => {
      console.log('🔒 Screen is locked')
      mainWindow.webContents.send(IpcServerPushChannel.PushPowerMonitor, { key: 'lock-screen' })
    })

    powerMonitor.on('unlock-screen', () => {
      console.log('🔓 Screen is unlocked')
      mainWindow.webContents.send(IpcServerPushChannel.PushPowerMonitor, { key: 'unlock-screen' })
    })
  }
}
const powerWatcher = new Power()
export { powerWatcher }

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { POWER_MONITOR_KEY } from '@shared/constant/power-monitor'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { getLogger } from '@shared/logger/main'
import { monitor } from '@shared/logger/performance'
import { app, BrowserWindow, powerMonitor, powerSaveBlocker } from 'electron'
import displaySleeper from 'displaysleeper'
const logger = getLogger('Power')
class Power {
  private blockerId?: number
  run() {
    this.blockerId = powerSaveBlocker.start('prevent-app-suspension')
    app.on('window-all-closed', () => {
      if (this.blockerId && powerSaveBlocker.isStarted(this.blockerId)) {
        powerSaveBlocker.stop(this.blockerId)
        logger.info('🛑 powerSaveBlocker stopped')
      }
    })

    // Listen for macOS power events
    powerMonitor.on('suspend', () => {
      logger.info('💤 System is about to sleep')
      BrowserWindow.getAllWindows().forEach((window) => {
        window.webContents.send(IpcServerPushChannel.PushPowerMonitor, { eventKey: POWER_MONITOR_KEY.Suspend })
      })
    })

    powerMonitor.on('resume', () => {
      logger.info('🌞 System has woken up')
      BrowserWindow.getAllWindows().forEach((window) => {
        window.webContents.send(IpcServerPushChannel.PushPowerMonitor, { eventKey: POWER_MONITOR_KEY.Resume })
      })
    })

    powerMonitor.on('lock-screen', () => {
      logger.info('🔒 Screen is locked')
      BrowserWindow.getAllWindows().forEach((window) => {
        window.webContents.send(IpcServerPushChannel.PushPowerMonitor, { eventKey: POWER_MONITOR_KEY.LockScreen })
      })
    })

    powerMonitor.on('unlock-screen', () => {
      logger.info('🔓 Screen is unlocked')
      BrowserWindow.getAllWindows().forEach((window) => {
        window.webContents.send(IpcServerPushChannel.PushPowerMonitor, { eventKey: POWER_MONITOR_KEY.UnlockScreen })
      })
    })
    displaySleeper.on('sleep', () => {
      console.log('😴 显示器睡眠了！')
    })

    displaySleeper.on('wake', () => {
      console.log('👀 显示器醒了！')
    })
    // speed-limit-change
    powerMonitor.on('speed-limit-change', (e) => {
      monitor.info(`🔋 Power speed limit changed to ${e.limit}`)
    })
    powerMonitor.on('thermal-state-change', (e) => {
      monitor.info(`🔋 Power thermal state changed to ${e.state}`)
    })
  }
  unregister() {
    if (this.blockerId && powerSaveBlocker.isStarted(this.blockerId)) {
      powerSaveBlocker.stop(this.blockerId)
      logger.info('🛑 powerSaveBlocker stopped')
    }
  }
}
const powerWatcher = new Power()
export { powerWatcher }

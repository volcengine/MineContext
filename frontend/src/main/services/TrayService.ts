// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, BrowserWindow, Menu, nativeImage, NativeImage, Tray } from 'electron'
import path from 'path'
import { getLogger } from '@shared/logger/main'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'

const logger = getLogger('TrayService')

export class TrayService {
  private tray: Tray | null = null
  private mainWindow: BrowserWindow
  private isRecording: boolean = false
  private trayIcon: NativeImage | null = null

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow
    this.loadIcon()
  }

  /**
   * Load tray icon
   */
  private loadIcon() {
    try {
      const iconPath = path.join(__dirname, '../../resources/icon.png')
      logger.info(`Loading tray icon from: ${iconPath}`)

      const originalIcon = nativeImage.createFromPath(iconPath)

      if (originalIcon.isEmpty()) {
        logger.error('Failed to load icon from path')
        return
      }

      // Simple resize for tray
      if (process.platform === 'darwin') {
        this.trayIcon = originalIcon.resize({ width: 18, height: 18 })
      } else {
        this.trayIcon = originalIcon.resize({ width: 16, height: 16 })
      }

      logger.info('Tray icon loaded successfully')
    } catch (error) {
      logger.error('Failed to load tray icon:', error)
    }
  }

  /**
   * Create and show the tray icon
   */
  create(): void {
    if (this.tray) {
      logger.warn('Tray already exists')
      return
    }

    try {
      if (!this.trayIcon) {
        logger.info('Tray icon not loaded, loading now')
        this.loadIcon()
      }

      if (!this.trayIcon || this.trayIcon.isEmpty()) {
        logger.error('Cannot create tray: icon is empty')
        return
      }

      logger.info(`Creating tray with icon size: ${this.trayIcon.getSize().width}x${this.trayIcon.getSize().height}`)

      this.tray = new Tray(this.trayIcon)

      // Set tooltip
      this.tray.setToolTip('MineContext')

      // Platform-specific behavior
      if (process.platform === 'win32') {
        // Windows: Only respond to right-click
        this.tray.on('click', () => {
          // No action on left click as per requirements
        })

        this.tray.on('right-click', () => {
          this.showContextMenu()
        })
      } else if (process.platform === 'darwin') {
        // macOS: Click shows menu
        this.tray.on('click', () => {
          this.showContextMenu()
        })
      } else {
        // Linux: Click shows menu
        this.tray.on('click', () => {
          this.showContextMenu()
        })
      }

      // Set initial context menu
      this.tray.setContextMenu(this.buildContextMenu())

      logger.info(`Tray icon created successfully on platform: ${process.platform}`)
    } catch (error) {
      logger.error('Failed to create tray:', error)
    }
  }

  /**
   * Show context menu
   */
  private showContextMenu(): void {
    if (this.tray) {
      this.tray.popUpContextMenu(this.buildContextMenu())
    }
  }

  /**
   * Build the context menu based on current state
   */
  private buildContextMenu(): Menu {
    const isWindowVisible = this.mainWindow.isVisible()
    const recordingStatusLabel = this.isRecording ? '录制中' : '已暂停'

    const menuTemplate: Electron.MenuItemConstructorOptions[] = [
      {
        label: recordingStatusLabel,
        enabled: false
      },
      {
        type: 'separator'
      },
      {
        label: isWindowVisible ? '隐藏主窗口' : '显示主窗口',
        click: () => {
          this.toggleWindow()
        }
      },
      {
        label: this.isRecording ? '暂停录制' : '继续录制',
        click: () => {
          this.toggleRecording()
        }
      },
      {
        type: 'separator'
      },
      {
        label: '退出 MineContext',
        click: () => {
          this.quitApp()
        }
      }
    ]

    return Menu.buildFromTemplate(menuTemplate)
  }

  /**
   * Toggle window visibility
   */
  private toggleWindow(): void {
    try {
      if (this.mainWindow.isVisible()) {
        this.mainWindow.hide()
      } else {
        this.mainWindow.show()
        this.mainWindow.focus()
      }

      // Update menu to reflect new window state
      if (this.tray) {
        this.tray.setContextMenu(this.buildContextMenu())
      }
    } catch (error) {
      logger.error('Failed to toggle window:', error)
    }
  }

  /**
   * Toggle recording state
   */
  private toggleRecording(): void {
    try {
      // Send event to renderer process to toggle recording
      this.mainWindow.webContents.send(IpcServerPushChannel.Tray_ToggleRecording)
      logger.info('Sent toggle recording event to renderer')
    } catch (error) {
      logger.error('Failed to toggle recording:', error)
    }
  }

  /**
   * Quit the application
   */
  private quitApp(): void {
    try {
      logger.info('Quitting application from tray')
      // Set flag to allow app to quit
      ;(app as any).isQuitting = true
      app.quit()
    } catch (error) {
      logger.error('Failed to quit app:', error)
    }
  }

  /**
   * Update recording status
   */
  updateRecordingStatus(isRecording: boolean): void {
    this.isRecording = isRecording

    if (this.tray) {
      // Update tooltip
      const tooltip = isRecording ? 'MineContext - 录制中' : 'MineContext - 已暂停'
      this.tray.setToolTip(tooltip)

      // Update context menu
      this.tray.setContextMenu(this.buildContextMenu())

      logger.info(`Tray recording status updated: ${isRecording}`)
    }
  }

  /**
   * Destroy the tray icon
   */
  destroy(): void {
    if (this.tray) {
      this.tray.destroy()
      this.tray = null
      logger.info('Tray destroyed')
    }
  }

  /**
   * Check if tray exists
   */
  exists(): boolean {
    return this.tray !== null
  }
}

export default TrayService

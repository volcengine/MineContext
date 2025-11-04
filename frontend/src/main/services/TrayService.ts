// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, BrowserWindow, Menu, nativeImage, NativeImage, Tray } from 'electron'
import path from 'path'
import { getLogger } from '@shared/logger/main'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import screenshotService from './ScreenshotService'

const logger = getLogger('TrayService')

export class TrayService {
  private tray: Tray | null = null
  private mainWindow: BrowserWindow
  private isRecording: boolean = false
  private trayIcon: NativeImage | null = null
  private trayIconRecording: NativeImage | null = null

  constructor(mainWindow: BrowserWindow) {
    this.mainWindow = mainWindow
    this.loadIcons()
  }

  /**
   * Load tray icons (default and recording states)
   */
  private loadIcons() {
    try {
      if (process.platform === 'darwin') {
        // macOS uses one set of PNG icons
        // Electron automatically loads @2x versions for Retina displays
        const defaultIconPath = path.join(__dirname, '../../resources/navigation-darker-default.png')
        const recordingIconPath = path.join(__dirname, '../../resources/navigation-darker-record.png')

        // Load icons - these are 54x54 (3x resolution for 18x18 display size)
        const defaultIcon = nativeImage.createFromPath(defaultIconPath)
        const recordingIcon = nativeImage.createFromPath(recordingIconPath)

        if (defaultIcon.isEmpty() || recordingIcon.isEmpty()) {
          logger.error('[Tray] Failed to load PNG icons')
          return
        }

        // Resize to 18x18 for display (icons are 54x54 which is 3x)
        // This ensures crisp rendering on all displays
        this.trayIcon = defaultIcon.resize({ width: 18, height: 18 })
        this.trayIconRecording = recordingIcon.resize({ width: 18, height: 18 })

        // Set as template image for macOS to enable automatic color adjustment
        // This makes the icon white on dark menu bar and black on light menu bar
        this.trayIcon.setTemplateImage(true)
        this.trayIconRecording.setTemplateImage(true)

        logger.info('[Tray] macOS PNG icons loaded successfully')
      } else if (process.platform === 'win32') {
        // Windows uses PNG format for better quality on high-DPI displays
        const defaultIconPath = path.join(__dirname, '../../resources/navigation-lighter-default.png')
        const recordingIconPath = path.join(__dirname, '../../resources/navigation-lighter-record.png')

        // Load icons - these are 54x54 (high resolution for crisp display)
        const defaultIcon = nativeImage.createFromPath(defaultIconPath)
        const recordingIcon = nativeImage.createFromPath(recordingIconPath)

        if (defaultIcon.isEmpty() || recordingIcon.isEmpty()) {
          logger.error('[Tray] Failed to load Windows PNG icons')
          return
        }

        // Resize to 32x32 for Windows tray to support high-DPI displays
        // 54x54 source ensures crisp rendering even at 200% scaling
        // Windows will automatically scale down for lower DPI displays
        this.trayIcon = defaultIcon.resize({ width: 32, height: 32 })
        this.trayIconRecording = recordingIcon.resize({ width: 32, height: 32 })

        logger.info('[Tray] Windows PNG icons loaded successfully')
      } else {
        // Other platforms (Linux) use the standard PNG icon
        const iconPath = path.join(__dirname, '../../resources/icon.png')
        logger.info(`[Tray] Loading tray icon from: ${iconPath}`)

        const originalIcon = nativeImage.createFromPath(iconPath)

        if (originalIcon.isEmpty()) {
          logger.error('[Tray] Failed to load icon from path')
          return
        }

        this.trayIcon = originalIcon.resize({ width: 16, height: 16 })
        this.trayIconRecording = this.trayIcon // Use same icon for Linux

        logger.info('[Tray] Linux icon loaded successfully')
      }

      logger.info('[Tray] All tray icons loaded successfully')
    } catch (error) {
      logger.error('[Tray] Failed to load tray icons:', error)
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
        this.loadIcons()
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
        // Windows: Left click shows window, right click shows menu
        this.tray.on('click', () => {
          this.mainWindow.show()
          this.mainWindow.focus()
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
        label: '显示主窗口',
        click: () => {
          this.mainWindow.show()
          this.mainWindow.focus()
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
   * Toggle recording state
   */
  private async toggleRecording(): Promise<void> {
    try {
      // If not recording (i.e., trying to start recording), check permissions first
      if (!this.isRecording) {
        const hasPermission = await screenshotService.checkPermissions()

        if (!hasPermission) {
          logger.info('No screen recording permission, showing window and navigating to screen monitor')
          // Show main window
          this.mainWindow.show()
          this.mainWindow.focus()
          // Send navigation event to renderer
          this.mainWindow.webContents.send(IpcServerPushChannel.Tray_NavigateToScreenMonitor)
          return
        }
      }

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
      // Update icon based on recording status
      const icon = isRecording ? this.trayIconRecording : this.trayIcon
      if (icon) {
        this.tray.setImage(icon)
        logger.info(`Tray icon updated for recording status: ${isRecording}`)
      }

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

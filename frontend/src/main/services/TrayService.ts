// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, BrowserWindow, Menu, Tray, nativeImage } from 'electron'
import path from 'path'
import { getLogger } from '@shared/logger/main'
import { isMac, isWin } from '@main/constant'
import { getResourcePath } from '@main/utils'

const logger = getLogger('TrayService')

export class TrayService {
  private static instance: TrayService
  private tray: Tray | null = null
  private mainWindow: BrowserWindow | null = null

  private constructor() {
    // Private constructor to prevent direct instantiation
  }

  public static getInstance(): TrayService {
    if (!TrayService.instance) {
      TrayService.instance = new TrayService()
    }
    return TrayService.instance
  }

  /**
   * Initialize the tray icon
   */
  public initialize(mainWindow: BrowserWindow): void {
    this.mainWindow = mainWindow
    this.createTray()
  }

  /**
   * Create the tray icon and menu
   */
  private createTray(): void {
    try {
      // Get the icon path
      const iconPath = this.getIconPath()
      if (!iconPath) {
        logger.error('Failed to get tray icon path')
        return
      }

      const icon = nativeImage.createFromPath(iconPath)
      if (icon.isEmpty()) {
        logger.error('Failed to create tray icon from path:', iconPath)
        return
      }

      // Resize icon for tray (tray icons should be small)
      const trayIcon = icon.resize({ width: 16, height: 16 })
      this.tray = new Tray(trayIcon)

      // Set tooltip
      this.tray.setToolTip('MineContext')

      // Create and set context menu
      this.updateMenu()

      // Handle tray click
      this.tray.on('click', () => {
        if (this.mainWindow) {
          if (this.mainWindow.isVisible()) {
            this.mainWindow.hide()
          } else {
            this.mainWindow.show()
            this.mainWindow.focus()
          }
        }
      })

      logger.info('Tray icon created successfully')
    } catch (error) {
      logger.error('Failed to create tray icon:', error)
    }
  }

  /**
   * Get the icon path for the tray
   */
  private getIconPath(): string | null {
    try {
      const resourcePath = getResourcePath()
      if (isMac) {
        return path.join(resourcePath, 'icon.png')
      } else if (isWin) {
        return path.join(resourcePath, 'icon.png')
      }
      return null
    } catch (error) {
      logger.error('Failed to get icon path:', error)
      return null
    }
  }

  /**
   * Update the tray menu with current state
   */
  public updateMenu(isRecording: boolean = false): void {

    if (!this.tray) {
      return
    }

    const template: Electron.MenuItemConstructorOptions[] = [
      {
        label: isRecording ? 'Recording' : '',
        enabled: false,
        visible: isRecording
      },
      {
        type: 'separator',
        visible: isRecording
      },
      {
        label: 'Show Main Window',
        click: () => {
          if (this.mainWindow) {
            this.mainWindow.show()
            this.mainWindow.focus()
          }
        }
      },
      {
        label: isRecording ? 'Pause Recording' : '',
        click: () => {
          // This will be handled by the renderer process
          if (this.mainWindow) {
            this.mainWindow.webContents.send('tray-pause-recording')
          }
        },
        visible: isRecording
      },
      {
        type: 'separator'
      },
      {
        label: 'Quit MineContext',
        click: () => {
          app.quit()
        }
      }
    ]

    const contextMenu = Menu.buildFromTemplate(template)
    this.tray.setContextMenu(contextMenu)
  }

  /**
   * Set recording state and update menu
   */
  public setRecording(isRecording: boolean): void {
    this.updateMenu(isRecording)
  }

  /**
   * Destroy the tray icon
   */
  public destroy(): void {
    if (this.tray) {
      this.tray.destroy()
      this.tray = null
    }
    this.mainWindow = null
  }
}

export default TrayService.getInstance()


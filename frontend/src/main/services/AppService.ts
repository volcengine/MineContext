// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getLogger } from '@shared/logger/main'
import { isDev, isLinux, isMac, isWin } from '@main/constant'
import { app } from 'electron'
import fs from 'fs'
import os from 'os'
import path from 'path'

const logger = getLogger('AppService')

export class AppService {
  private static instance: AppService

  private constructor() {
    // Private constructor to prevent direct instantiation
  }

  public static getInstance(): AppService {
    if (!AppService.instance) {
      AppService.instance = new AppService()
    }
    return AppService.instance
  }

  public async setAppLaunchOnBoot(isLaunchOnBoot: boolean): Promise<void> {
    // Set login item settings for windows and mac
    // linux is not supported because it requires more file operations
    if (isWin || isMac) {
      app.setLoginItemSettings({ openAtLogin: isLaunchOnBoot })
    } else if (isLinux) {
      try {
        const autostartDir = path.join(os.homedir(), '.config', 'autostart')
        const desktopFile = path.join(autostartDir, isDev ? 'vikingdb-dev.desktop' : 'vikingdb.desktop')

        if (isLaunchOnBoot) {
          // Ensure autostart directory exists
          try {
            await fs.promises.access(autostartDir)
          } catch {
            await fs.promises.mkdir(autostartDir, { recursive: true })
          }

          // Get executable path
          let executablePath = app.getPath('exe')
          if (process.env.APPIMAGE) {
            // For AppImage packaged apps, use APPIMAGE environment variable
            executablePath = process.env.APPIMAGE
          }

          // Create desktop file content
          const desktopContent = `[Desktop Entry]
  Type=Application
  Name=MineContext
  Comment=A powerful AI assistant for producer.
  Exec=${executablePath}
  Icon=minecontext
  Terminal=false
  StartupNotify=false
  Categories=Development;Utility;
  X-GNOME-Autostart-enabled=true
  Hidden=false`

          // Write desktop file
          await fs.promises.writeFile(desktopFile, desktopContent)
          logger.info('Created autostart desktop file for Linux')
        } else {
          // Remove desktop file
          try {
            await fs.promises.access(desktopFile)
            await fs.promises.unlink(desktopFile)
            logger.info('Removed autostart desktop file for Linux')
          } catch {
            // File doesn't exist, no need to remove
          }
        }
      } catch (error) {
        logger.error('Failed to set launch on boot for Linux:', error as Error)
      }
    }
  }
}

// Default export as singleton instance
export default AppService.getInstance()

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { occupiedDirs } from '@shared/config/constant'
import { app } from 'electron'
import fs from 'fs'
import path from 'path'
import { initAppDataDir } from './utils/init'
import { mainLog } from '@shared/logger/main'

// Only execute initialization after packaging
if (app.isPackaged) {
  initAppDataDir()
}

/**
 * Execute early in the application startup: migrate user data directories that are occupied according to the command line --new-data-path
 * Key points:
 * - Use app.commandLine.getSwitchValue to parse parameters
 * - Cross-platform, no need to restrict to win32
 * - Protection: skip directly if the new and old paths are the same; use try/catch for each item to prevent crashes
 * - Ensure the target parent directory exists before copying
 * - Operate only when the target path is valid and different from the old path
 */
const handleOccupiedDirsMigration = (): void => {
  // Use Electron's provided command line parser
  const switchValue = app.commandLine.getSwitchValue('new-data-path')
  const newAppDataPathRaw = switchValue && switchValue.trim()

  if (!newAppDataPathRaw) return

  // Normalize to an absolute path
  const newAppDataPath = path.isAbsolute(newAppDataPathRaw)
    ? newAppDataPathRaw
    : path.resolve(process.cwd(), newAppDataPathRaw)

  const oldAppDataPath = app.getPath('userData')

  // Skip if the new and old paths are the same
  if (newAppDataPath === oldAppDataPath) {
    mainLog.warn('[Data Migration] New and old data paths are the same. Skipping copy.')
    return
  }

  mainLog.info(`[Data Migration] Start: "${oldAppDataPath}" -> "${newAppDataPath}"`)

  for (const dirName of occupiedDirs) {
    const sourcePath = path.join(oldAppDataPath, dirName)
    const destinationPath = path.join(newAppDataPath, dirName)

    try {
      if (!fs.existsSync(sourcePath)) {
        mainLog.info(`[Data Migration] Skip (not found): ${sourcePath}`)
        continue
      }

      // Ensure the target parent directory exists
      fs.mkdirSync(path.dirname(destinationPath), { recursive: true })

      // Recursively copy (preserving directory structure/files)
      fs.cpSync(sourcePath, destinationPath, { recursive: true })

      mainLog.info(`[Data Migration] Copied: ${sourcePath} -> ${destinationPath}`)
    } catch (error: any) {
      // Common errors: permissions/read-only/disk full, etc.
      mainLog.error(`[Data Migration] Failed copying "${dirName}": ${String(error?.message || error)}`)
    }
  }

  mainLog.info('[Data Migration] Done.')
}

// Execute migration before creating any windows
handleOccupiedDirsMigration()

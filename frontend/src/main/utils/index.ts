// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import fs from 'node:fs'
import fsAsync from 'node:fs/promises'
import path from 'node:path'

import { app } from 'electron'

/**
 * Gets the absolute path to the 'resources' directory within the app.
 * ✨ Pro Tip: In a packaged app, `process.resourcesPath` is often a more reliable
 * way to get the root of the resources directory than `app.getAppPath()`.
 */
export const getResourcePath = (): string => {
  return path.join(app.getAppPath(), 'resources')
}

/**
 * Gets the path to the application's 'Data' directory, creating it if it doesn't exist.
 * ✨ Optimization: Removed the redundant `fs.existsSync` check. `mkdirSync` with the
 * `recursive: true` option handles this internally and won't throw an error if the path already exists.
 */
export const getDataPath = (): string => {
  const dataPath = path.join(app.getPath('userData'), 'Data')
  fs.mkdirSync(dataPath, { recursive: true })
  return dataPath
}

/**
 * Asynchronously calculates the total size of a directory and all its contents.
 * @param directoryPath The path to the directory.
 * @returns A promise that resolves to the total size in bytes.
 */
export const calculateDirectorySize = async (directoryPath: string): Promise<number> => {
  try {
    const items = await fsAsync.readdir(directoryPath)

    // ✨ Performance: Process all directory items in parallel instead of sequentially.
    const sizePromises = items.map(async (item) => {
      const itemPath = path.join(directoryPath, item)

      try {
        const stats = await fsAsync.stat(itemPath)

        if (stats.isFile()) {
          return stats.size
        }
        if (stats.isDirectory()) {
          // Recurse into subdirectory
          return await calculateDirectorySize(itemPath)
        }
      } catch (err) {
        // ✨ Robustness: Ignore files/directories that can't be accessed (e.g., permissions).
        console.error(`Could not stat path ${itemPath}:`, err)
        return 0
      }

      return 0 // Return 0 for other types like symlinks, etc.
    })

    const sizes = await Promise.all(sizePromises)

    // Sum up all the resolved sizes
    return sizes.reduce((acc, size) => acc + (size ?? 0), 0)
  } catch (err) {
    // ✨ Robustness: Handle cases where the top-level directory can't be read.
    console.error(`Could not read directory ${directoryPath}:`, err)
    return 0
  }
}

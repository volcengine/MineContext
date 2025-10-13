// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { spawn } from 'child_process'
import { app } from 'electron'

import * as path from 'path'
import { getLogger } from '@shared/logger/main'
const logger = getLogger('mac-window-manager')
// --- Type Definitions ---

/**
 * @interface WindowBounds
 * @description Defines the structure for a window's geometric bounds.
 */
interface WindowBounds {
  X: number
  Y: number
  Width: number
  Height: number
}

/**
 * @interface QuartzWindowInfo
 * @description Represents the detailed window information parsed from the Python/Quartz script output.
 */
interface QuartzWindowInfo {
  windowId: number
  appName: string
  windowTitle: string
  bounds: WindowBounds
  isOnScreen: boolean
  layer: number
  isImportant: boolean
  area: number
}

/**
 * @interface FinalWindowInfo
 * @description The final, processed window information object returned by the module.
 */
export interface FinalWindowInfo {
  windowId: number
  appName: string
  windowTitle: string
  isOnScreen: boolean
  isImportantApp: boolean
  bounds?: WindowBounds
  layer?: number
}

// --- Private Helper Functions ---

/**
 * Executes a Python script that uses the Quartz framework to get detailed information
 * about all windows, including those on other spaces or minimized.
 * @returns A promise that resolves to an array of detailed window information objects.
 */
const getWindowsWithRealIds = (): Promise<QuartzWindowInfo[]> => {
  return new Promise((resolve, reject) => {
    const basePath = app.isPackaged
      ? path.join(process.resourcesPath, 'bin', 'window_inspector')
      : path.join(__dirname, '../..', 'externals/python/window_inspector/dist', 'window_inspector')
    const exePath = path.join(basePath, 'window_inspector')
    const py = spawn(exePath)

    let output = ''
    let error = ''

    py.stdout.on('data', (data) => (output += data.toString()))
    py.stderr.on('data', (data) => (error += data.toString()))

    py.on('close', (code) => {
      if (code === 0 && output) {
        try {
          resolve(JSON.parse(output))
        } catch (err) {
          reject(err)
        }
      } else {
        reject(new Error(error || 'Python script failed'))
      }
    })
  })
}

// --- Exported Functions ---

/**
 * Gets a list of all relevant application windows. It first attempts to use a detailed
 * method via Python/Quartz for accuracy and falls back to a simpler AppleScript method.
 * @returns A promise that resolves to an array of processed window information.
 */
export const getAllWindows = async (): Promise<FinalWindowInfo[]> => {
  try {
    const windowsWithIds = await getWindowsWithRealIds()

    if (windowsWithIds.length > 0) {
      const allWindows: FinalWindowInfo[] = []
      const importantApps = [
        'zoom.us',
        'Zoom',
        'Microsoft PowerPoint',
        'Notion',
        'Slack',
        'Microsoft Teams',
        'MSTeams',
        'Teams',
        'Discord',
        'Google Chrome',
        'Microsoft Word',
        'Microsoft Excel',
        'Keynote',
        'Figma',
        'Sketch',
        'Adobe Photoshop',
        'Visual Studio Code',
        'Cursor',
        'Safari',
        'Firefox',
        'WeChat',
        'Obsidian',
        'Roam Research'
      ]

      const systemApps = [
        'MineContext',
        'Electron',
        'SystemUIServer',
        'Dock',
        'ControlCenter',
        'WindowManager',
        'NotificationCenter',
        'Spotlight'
      ]

      for (const window of windowsWithIds) {
        if (systemApps.includes(window.appName)) {
          continue
        }

        const isImportant = importantApps.some((app) => window.appName.toLowerCase().includes(app.toLowerCase()))

        if (window.windowTitle || isImportant) {
          let finalTitle = window.windowTitle

          if (!finalTitle.trim()) {
            if (window.appName.includes('zoom')) finalTitle = 'Zoom Meeting'
            else if (window.appName.includes('PowerPoint')) finalTitle = 'PowerPoint Presentation'
            else if (window.appName.includes('Notion')) finalTitle = 'Notion Workspace'
            else if (window.appName.includes('Teams')) finalTitle = 'Teams Meeting'
            else finalTitle = `${window.appName} Window`
          }

          allWindows.push({
            windowId: window.windowId,
            appName: window.appName,
            windowTitle: finalTitle,
            isOnScreen: window.isOnScreen,
            bounds: window.bounds,
            isImportantApp: isImportant,
            layer: window.layer
          })
        }
      }

      // Sort to prioritize important apps
      allWindows.sort((a, b) => {
        if (a.isImportantApp && !b.isImportantApp) return -1
        if (!a.isImportantApp && b.isImportantApp) return 1
        return a.appName.localeCompare(b.appName)
      })

      return allWindows
    }

    // Fallback logic is removed for simplicity, as the Python method is the primary strategy.
    // If needed, the AppleScript fallback could be implemented here.
    return []
  } catch (error) {
    if (error instanceof Error) {
      logger.error('Error in getAllWindows:', error.message)
    }
    return []
  }
}

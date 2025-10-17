// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, desktopCapturer, shell, systemPreferences } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import { getLogger } from '@shared/logger/main'
import { isMac } from '@main/constant'
import { getCacheDir } from '@main/utils/file'
import { CaptureSourcesTools } from '@main/utils/get-capture-sources'
import dayjs from 'dayjs'

const logger = getLogger('ScreenshotService')

class ScreenshotService extends CaptureSourcesTools {
  constructor() {
    super()
    logger.info('ScreenshotService initialized')
  }

  /**
   * Check for screen recording permissions.
   * On macOS, it checks if the app has been granted screen recording permissions.
   * On Windows and Linux, this method will always return true as there is no standard API for this check.
   * @returns {Promise<boolean>} - Returns true if permission is granted, otherwise false.
   */
  async checkPermissions(): Promise<boolean> {
    if (isMac) {
      const status = systemPreferences.getMediaAccessStatus('screen')
      return status === 'granted'
    }
    return true
  }

  /**
   * Open the screen recording privacy settings in System Preferences.
   * This function is only effective on macOS.
   */
  openPrefs(): void {
    if (isMac) {
      shell.openExternal('x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture')
    }
  }

  /**
   * Capture a screenshot of the main display.
   * The screenshot will be saved to a specific directory structure based on the incoming groupIntervalTime (usually the time of the first frame screenshot of the current group).
   * @param {number} groupIntervalTime - The recording interval in seconds, used to construct the save path.
   * @returns {Promise<{ success: boolean; filePath?: string; error?: string }>} - Returns the file path if the operation is successful, otherwise returns an error message.
   */
  async takeScreenshot(
    groupIntervalTime: string,
    sourceId: string
  ): Promise<{ success: boolean; screenshotInfo?: { url: string; date: string; timestamp: number }; error?: string }> {
    try {
      const res = await this.takeSourceScreenshotTools(sourceId)
      if (res.success) {
        const source = res.source as any
        const thumbnail = source.thumbnail
        if (!thumbnail || thumbnail.isEmpty()) {
          logger.info(`[ScreenshotService] Skipping invalid thumbnail source`, source)
        }

        const pngBuffer = thumbnail.toPNG()
        if (pngBuffer.length === 0) {
          logger.info(`[ScreenshotService] Thumbnail is an empty buffer: ${source.name}`)
        }

        const image = source.thumbnail.toPNG()
        // logger.info(
        //   `[ScreenshotService] start Screenshot image size: ---***${dayjs().format('YYYY-MM-DD HH:mm:ss')}***--- ${image.length}`
        // )
        const userDataPath = app.getPath('userData')
        const dateString = dayjs().format('YYYYMMDD')
        const timestamp = dayjs().valueOf()
        const activityPath = path.join(
          userDataPath,
          'Data',
          'screenshot',
          'activity',
          dateString,
          `${groupIntervalTime}-${sourceId.split(':').join('-')}`
        )
        await fs.promises.mkdir(activityPath, { recursive: true })
        const filePath = path.join(activityPath, `${timestamp}.png`)
        await fs.promises.writeFile(filePath, image)
        await fs.promises.access(filePath)
        const screenshotInfo = {
          url: filePath,
          date: dateString,
          timestamp: timestamp
        }
        // logger.info(
        //   `[ScreenshotService] end Screenshot taken: ---***${dayjs().format('YYYY-MM-DD HH:mm:ss')}***--- ${filePath}`
        // )
        return { success: true, screenshotInfo }
      } else {
        return { success: false, error: res.error }
      }
    } catch (error: any) {
      logger.error(`Failed to take screenshot: ${error.message}`)
      return { success: false, error: error.message }
    }
  }

  /**
   * Get all screenshots for a specified date
   * @param {string} date - Date string in YYYYMMDD format, uses today if not provided
   * @returns {Promise<{ success: boolean; screenshots?: ScreenshotRecord[]; error?: string }>}
   */
  async getScreenshotsByDate(date?: string): Promise<{ success: boolean; screenshots?: any[]; error?: string }> {
    try {
      const userDataPath = app.getPath('userData')
      const dateString = date || dayjs().format('YYYYMMDD')
      const activityPath = path.join(userDataPath, 'Data', 'screenshot', 'activity', dateString)

      // Check if the directory exists
      if (!fs.existsSync(activityPath)) {
        logger.info(`Screenshots directory not found for date ${dateString}`)
        return { success: true, screenshots: [] }
      }

      // Recursively traverse the directory structure: date/groupIntervalTime/filename.png
      const screenshots: Array<{
        id: string
        date: string
        timestamp: number
        image_url: string
        description: string
        created_at: string
        group_id: string // Group ID
      }> = []

      // Get all subdirectories (groupIntervalTime) under the date
      const subdirs = await fs.promises.readdir(activityPath, { withFileTypes: true })

      for (const subdir of subdirs) {
        if (subdir.isDirectory()) {
          const groupIntervalTime = subdir.name
          const groupPath = path.join(activityPath, groupIntervalTime)

          // Get all files in the group directory
          const files = await fs.promises.readdir(groupPath)

          for (const file of files) {
            if (path.extname(file).toLowerCase() === '.png') {
              const filePath = path.join(groupPath, file)
              const stats = await fs.promises.stat(filePath)
              const timestamp = parseInt(path.basename(file, '.png'))

              screenshots.push({
                id: `screenshot-${timestamp}`,
                date: dateString,
                timestamp: timestamp,
                image_url: filePath,
                description: 'Historical screenshot',
                created_at: dayjs(stats.birthtime).toISOString(),
                group_id: groupIntervalTime // Group ID parsed from the path
              })
            }
          }
        }
      }

      // Sort by timestamp in descending order
      screenshots.sort((a, b) => b.timestamp - a.timestamp)

      logger.info(
        `Found ${screenshots.length} screenshots for date ${dateString} across ${subdirs.filter((d) => d.isDirectory()).length} groups`
      )
      return { success: true, screenshots }
    } catch (error: any) {
      logger.error('Failed to get screenshots by date:', error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Capture a screenshot of a specific window or screen based on the provided source ID.
   * @param {string} sourceId - The ID of the screen or window to capture.
   * @returns {Promise<{ success: boolean; filePath?: string; error?: string }>} - Returns the file path if the operation is successful, otherwise returns an error message.
   */
  async takeSourceScreenshot(sourceId: string): Promise<{ success: boolean; filePath?: string; error?: string }> {
    try {
      const sources = await desktopCapturer.getSources({ types: ['window', 'screen'] })
      const source = sources.find((s) => s.id === sourceId)
      if (!source) {
        throw new Error(`Source with id ${sourceId} not found.`)
      }
      const image = source.thumbnail.toPNG()
      const filePath = path.join(getCacheDir(), `screenshot-source-${dayjs().valueOf()}.png`)
      await fs.promises.writeFile(filePath, image)
      return { success: true, filePath }
    } catch (error: any) {
      logger.error(`Failed to take source screenshot for ${sourceId}:`, error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Get a list of currently visible window sources.
   * @returns {Promise<{ success: boolean; sources?: Electron.DesktopCapturerSource[]; error?: string }>} - Returns a list of sources if the operation is successful, otherwise returns an error message.
   */
  async getVisibleSources(sourceIds?: string[]): Promise<{
    success: boolean
    sources?: any[]
    error?: string
  }> {
    try {
      return await this.getVisibleSourcesTools(sourceIds)
      // const sources = await desktopCapturer.getSources({
      //   types: ['window', 'screen'],
      //   thumbnailSize: { width: 1, height: 1 },
      //   fetchWindowIcons: false
      // })
      // return { success: true, sources, list }
    } catch (error: any) {
      logger.error('Failed to get visible sources:', error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Delete the screenshot file at the specified path.
   * @param {string} filePath - The full path of the file to delete.
   * @returns {Promise<{ success: boolean; error?: string }>} - Returns success: true if the operation is successful, otherwise returns an error message.
   */
  async deleteScreenshot(filePath: string): Promise<{ success: boolean; error?: string }> {
    try {
      await fs.promises.unlink(filePath)
      return { success: true }
    } catch (error: any) {
      logger.error(`Failed to delete screenshot at ${filePath}:`, error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Read the image file at the specified path as a Base64 encoded string.
   * @param {string} filePath - The full path of the image file.
   * @returns {Promise<{ success: boolean; data?: string; error?: string }>} - Returns the Base64 encoded image data if the operation is successful, otherwise returns an error message.
   */
  async readImageAsBase64(filePath: string): Promise<{ success: boolean; data?: string; error?: string }> {
    try {
      // logger.log(`[ScreenshotService] readImageAsBase64 filePath: ${filePath}`)
      await fs.promises.access(filePath)
      const data = await fs.promises.readFile(filePath, { encoding: 'base64' })
      return { success: true, data }
    } catch (error: any) {
      // logger.log(`[ScreenshotService] readImageAsBase64 filePath: ${filePath}, error: ${error.message}`)
      logger.error(`Failed to read image at ${filePath}:`, error)
      return { success: false, error: error.message }
    }
  }
  async getCaptureAllSources(): Promise<{ success: boolean; sources?: any[]; error?: string; list?: any[] }> {
    try {
      return await this.getCaptureSourcesTools()
    } catch (error: any) {
      logger.error('Failed to get capture sources:', error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Clean up old screenshot files
   * @param {number} retentionDays - Retention period in days, default is 15 days
   * @returns {Promise<{ success: boolean; deletedCount?: number; error?: string }>}
   */
  async cleanupOldScreenshots(
    retentionDays: number = 15
  ): Promise<{ success: boolean; deletedCount?: number; deletedSize?: number; error?: string }> {
    try {
      const userDataPath = app.getPath('userData')
      const screenshotBasePath = path.join(userDataPath, 'Data', 'screenshot', 'activity')

      // Check if directory exists
      if (!fs.existsSync(screenshotBasePath)) {
        logger.info('Screenshot directory does not exist, no cleanup needed')
        return { success: true, deletedCount: 0, deletedSize: 0 }
      }

      // Calculate cutoff date (current date - retention days)
      const cutoffDate = dayjs().subtract(retentionDays, 'day')
      const cutoffDateString = cutoffDate.format('YYYYMMDD')

      logger.info(`Starting cleanup of screenshots older than ${retentionDays} days (before ${cutoffDateString})`)

      let deletedCount = 0
      let deletedSize = 0

      // Get all date directories
      const dateDirs = await fs.promises.readdir(screenshotBasePath, { withFileTypes: true })

      for (const dateDir of dateDirs) {
        if (!dateDir.isDirectory()) continue

        const dateDirName = dateDir.name

        // Check if date is earlier than cutoff date
        if (dateDirName < cutoffDateString) {
          const dateDirPath = path.join(screenshotBasePath, dateDirName)

          try {
            // Calculate directory size
            const dirSize = await this.getDirectorySize(dateDirPath)
            deletedSize += dirSize

            // Delete entire date directory
            await fs.promises.rm(dateDirPath, { recursive: true, force: true })
            deletedCount++
            logger.info(`Deleted screenshot directory: ${dateDirName} (${(dirSize / 1024 / 1024).toFixed(2)} MB)`)
          } catch (error: any) {
            logger.error(`Failed to delete directory ${dateDirName}:`, error)
          }
        }
      }

      logger.info(
        `Cleanup completed. Deleted ${deletedCount} directories, freed ${(deletedSize / 1024 / 1024).toFixed(2)} MB`
      )
      return { success: true, deletedCount, deletedSize }
    } catch (error: any) {
      logger.error('Failed to cleanup old screenshots:', error)
      return { success: false, error: error.message }
    }
  }

  /**
   * Calculate directory size (recursive)
   * @param {string} dirPath - Directory path
   * @returns {Promise<number>} - Directory size in bytes
   */
  private async getDirectorySize(dirPath: string): Promise<number> {
    let totalSize = 0

    try {
      const items = await fs.promises.readdir(dirPath, { withFileTypes: true })

      for (const item of items) {
        const itemPath = path.join(dirPath, item.name)

        if (item.isDirectory()) {
          totalSize += await this.getDirectorySize(itemPath)
        } else if (item.isFile()) {
          const stats = await fs.promises.stat(itemPath)
          totalSize += stats.size
        }
      }
    } catch (error: any) {
      logger.error(`Failed to calculate directory size for ${dirPath}:`, error)
    }

    return totalSize
  }
}

export default new ScreenshotService()

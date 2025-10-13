// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { app, desktopCapturer, shell, systemPreferences } from 'electron'
import fs from 'node:fs'
import path from 'node:path'
import dayjs from 'dayjs'
import { getLogger } from '@shared/logger/main'
import { isMac } from '@main/constant'
import { getCacheDir } from '@main/utils/file'
import { logToBackendFile } from '@main/backend'
import { is } from '@electron-toolkit/utils'
import { CaptureSourcesTools } from '@main/utils/get-capture-sources'

const logger = getLogger('ScreenshotService')

class ScreenshotService extends CaptureSourcesTools {
  constructor() {
    super()
    logger.info('ScreenshotService initialized')
  }

  /**
   * 检查屏幕录制权限。
   * 在 macOS 上，它会检查应用是否已被授予屏幕录制权限。
   * 在 Windows 和 Linux 上，此方法将始终返回 true，因为没有标准的 API 用于此项检查。
   * @returns {Promise<boolean>} - 如果有权限则返回 true，否则返回 false。
   */
  async checkPermissions(): Promise<boolean> {
    if (isMac) {
      const status = systemPreferences.getMediaAccessStatus('screen')
      return status === 'granted'
    }
    return true
  }

  /**
   * 打开系统偏好设置中的屏幕录制隐私设置。
   * 此功能仅在 macOS 上有效。
   */
  openPrefs(): void {
    if (isMac) {
      shell.openExternal('x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture')
    }
  }

  /**
   * 捕获主显示器的屏幕截图。
   * 截图将根据传入的groupIntervalTime(一般是当前组第一帧截图的时间)保存到特定的目录结构中。
   * @param {number} groupIntervalTime - 记录间隔（秒），用于构建保存路径。
   * @returns {Promise<{ success: boolean; filePath?: string; error?: string }>} - 操作成功则返回文件路径，否则返回错误信息。
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
          logger.info(`[ScreenshotService] 跳过无效缩略图 source`, source)
        }

        const pngBuffer = thumbnail.toPNG()
        if (pngBuffer.length === 0) {
          logger.info(`[ScreenshotService] 缩略图为空 buffer: ${source.name}`)
        }

        const image = source.thumbnail.toPNG()
        logger.info(
          `[ScreenshotService] start Screenshot image size: ---***${dayjs().format('YYYY-MM-DD HH:mm:ss')}***--- ${image.length}`
        )
        const userDataPath = app.getPath('userData')
        const today = new Date()
        const dateString = today.toISOString().slice(0, 10).replace(/-/g, '')
        const activityPath = path.join(
          userDataPath,
          'Data',
          'screenshot',
          'activity',
          dateString,
          `${groupIntervalTime}-${sourceId.split(':').join('-')}`
        )
        await fs.promises.mkdir(activityPath, { recursive: true })
        const filePath = path.join(activityPath, `${Date.now()}.png`)
        await fs.promises.writeFile(filePath, image)
        await fs.promises.access(filePath)
        const screenshotInfo = {
          url: filePath,
          date: dateString,
          timestamp: Date.now()
        }
        logger.info(
          `[ScreenshotService] end Screenshot taken: ---***${dayjs().format('YYYY-MM-DD HH:mm:ss')}***--- ${filePath}`
        )
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
   * 获取指定日期的所有截图
   * @param {string} date - 日期字符串，格式为 YYYYMMDD，如果不传则使用今天
   * @param {number} recordInterval - 记录间隔
   * @returns {Promise<{ success: boolean; screenshots?: ScreenshotRecord[]; error?: string }>}
   */
  async getScreenshotsByDate(date?: string): Promise<{ success: boolean; screenshots?: any[]; error?: string }> {
    try {
      const userDataPath = app.getPath('userData')
      const dateString = date || new Date().toISOString().slice(0, 10).replace(/-/g, '')
      const activityPath = path.join(userDataPath, 'Data', 'screenshot', 'activity', dateString)

      // 检查目录是否存在
      if (!fs.existsSync(activityPath)) {
        logger.info(`Screenshots directory not found for date ${dateString}`)
        return { success: true, screenshots: [] }
      }

      // 递归遍历目录结构：date/groupIntervalTime/filename.png
      const screenshots: Array<{
        id: string
        date: string
        timestamp: number
        image_url: string
        description: string
        created_at: string
        group_id: string // 分组id
      }> = []

      // 获取日期下的所有子目录（groupIntervalTime）
      const subdirs = await fs.promises.readdir(activityPath, { withFileTypes: true })

      for (const subdir of subdirs) {
        if (subdir.isDirectory()) {
          const groupIntervalTime = subdir.name
          const groupPath = path.join(activityPath, groupIntervalTime)

          // 获取分组目录下的所有文件
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
                description: '历史截图',
                created_at: stats.birthtime.toISOString(),
                group_id: groupIntervalTime // 从路径解析出的分组ID
              })
            }
          }
        }
      }

      // 按时间戳降序排列
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
   * 根据提供的源 ID 捕获特定窗口或屏幕的截图。
   * @param {string} sourceId - 要捕获的屏幕或窗口的 ID。
   * @returns {Promise<{ success: boolean; filePath?: string; error?: string }>} - 操作成功则返回文件路径，否则返回错误信息。
   */
  async takeSourceScreenshot(sourceId: string): Promise<{ success: boolean; filePath?: string; error?: string }> {
    try {
      const sources = await desktopCapturer.getSources({ types: ['window', 'screen'] })
      const source = sources.find((s) => s.id === sourceId)
      if (!source) {
        throw new Error(`Source with id ${sourceId} not found.`)
      }
      const image = source.thumbnail.toPNG()
      const filePath = path.join(getCacheDir(), `screenshot-source-${Date.now()}.png`)
      await fs.promises.writeFile(filePath, image)
      return { success: true, filePath }
    } catch (error: any) {
      logger.error(`Failed to take source screenshot for ${sourceId}:`, error)
      return { success: false, error: error.message }
    }
  }

  /**
   * 获取当前可见的窗口源列表。
   * @returns {Promise<{ success: boolean; sources?: Electron.DesktopCapturerSource[]; error?: string }>} - 操作成功则返回源列表，否则返回错误信息。
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
   * 删除指定路径的截图文件。
   * @param {string} filePath - 要删除的文件的完整路径。
   * @returns {Promise<{ success: boolean; error?: string }>} - 操作成功则返回 success: true，否则返回错误信息。
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
   * 将指定路径的图片文件读取为 Base64 编码的字符串。
   * @param {string} filePath - 图片文件的完整路径。
   * @returns {Promise<{ success: boolean; data?: string; error?: string }>} - 操作成功则返回 Base64 编码的图片数据，否则返回错误信息。
   */
  async readImageAsBase64(filePath: string): Promise<{ success: boolean; data?: string; error?: string }> {
    try {
      logger.log(`[ScreenshotService] readImageAsBase64 filePath: ${filePath}`)
      await fs.promises.access(filePath)
      const data = await fs.promises.readFile(filePath, { encoding: 'base64' })
      return { success: true, data }
    } catch (error: any) {
      logger.log(`[ScreenshotService] readImageAsBase64 filePath: ${filePath}, error: ${error.message}`)
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
}

export default new ScreenshotService()

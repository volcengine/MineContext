// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { AppDispatch, RootState } from '@renderer/store'
import { ScreenshotRecord } from '@renderer/store/screen'
import { loggerService } from '@logger'

const logger = loggerService.withContext('ScreenThunk')

/**
 * 计算当前截图应该归属的分组时间戳
 * 如果当前会话为空或者距离最近分组超过5分钟，则创建新分组
 * 否则使用现有分组的时间戳
 */
export const calculateGroupTimestamp = (currentSession: any, newTimestamp: number): string => {
  if (!currentSession || !currentSession.screenshots) {
    // 没有会话或截图，使用当前时间戳创建新分组
    return String(newTimestamp)
  }

  const screenshots = currentSession.screenshots
  const keys = Object.keys(screenshots)

  if (keys.length === 0) {
    // 没有现有截图，创建新分组
    return String(newTimestamp)
  }

  // 获取最近的分组key
  keys.sort((a, b) => parseInt(b) - parseInt(a))
  const latestKey = keys[0]
  const latestTimestamp = parseInt(latestKey)
  const fiveMinutesInMillis = 5 * 60 * 1000

  // 判断是否距离最近分组超过5分钟
  if (newTimestamp - latestTimestamp < fiveMinutesInMillis) {
    // 未超过5分钟，使用现有分组
    return latestKey
  } else {
    // 超过5分钟，创建新分组
    return String(newTimestamp)
  }
}

/**
 * 截图 Thunk（参考 vaultThunk 模式）
 * 处理分组时间戳计算、截图拍摄、数据转换等完整流程
 */
export const captureScreenshotThunk =
  (sourceId: string) => async (_dispatch: AppDispatch, getState: () => RootState) => {
    try {
      const state = getState()
      const { currentSession } = state.screen

      const currentTimestamp = Date.now()

      // 计算分组时间戳
      const groupTimestamp = calculateGroupTimestamp(currentSession, currentTimestamp)

      logger.info(`📸 开始截图，分组时间戳: ${groupTimestamp}`)

      // 调用截图 API
      const result = await window.screenMonitorAPI.takeScreenshot(groupTimestamp, sourceId)
      if (!result.success || !result.screenshotInfo) {
        throw new Error(result.error || 'Screenshot failed to return screenshotInfo.')
      }

      // 读取图片 Base64 数据
      const imageBase64 = await window.screenMonitorAPI.readImageAsBase64(result.screenshotInfo.url)
      if (!imageBase64.success || !imageBase64.data) {
        throw new Error(imageBase64.error || 'Failed to read image data.')
      }

      // 构建截图记录
      const newScreenshot: ScreenshotRecord = {
        id: `screenshot-${result.screenshotInfo.timestamp}`,
        date: result.screenshotInfo.date,
        timestamp: result.screenshotInfo.timestamp,
        base64_url: `data:image/png;base64,${imageBase64.data}`,
        image_url: result.screenshotInfo.url,
        description: '自动截图',
        group_id: groupTimestamp // 添加分组ID
      }

      // 暂弃用
      // 使用新的 action 直接添加到计算好的分组
      // dispatch(addScreenshotToGroup({
      //   screenshot: newScreenshot,
      //   groupKey: groupTimestamp
      // }))

      // logger.info(`📸 截图成功，添加到分组: ${groupTimestamp}，文件路径: ${result.screenshotInfo.url}`)
      return newScreenshot
    } catch (error: any) {
      logger.error('📸 截图失败:', error)
      throw error
    }
  }

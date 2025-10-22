// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { AppDispatch, RootState } from '@renderer/store'
import { ScreenshotRecord } from '@renderer/store/screen'

import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('ScreenThunk')

/**
 * Calculate the group timestamp to which the current screenshot should belong.
 * If the current session is empty or the time since the last group exceeds 5 minutes, a new group is created.
 * Otherwise, the timestamp of the existing group is used.
 */
export const calculateGroupTimestamp = (currentSession: any, newTimestamp: number): string => {
  if (!currentSession || !currentSession.screenshots) {
    // No session or screenshots, create a new group using the current timestamp
    return String(newTimestamp)
  }

  const screenshots = currentSession.screenshots
  const keys = Object.keys(screenshots)

  if (keys.length === 0) {
    // No existing screenshots, create a new group
    return String(newTimestamp)
  }

  // Get the most recent group key
  keys.sort((a, b) => parseInt(b) - parseInt(a))
  const latestKey = keys[0]
  const latestTimestamp = parseInt(latestKey)
  const fiveMinutesInMillis = 5 * 60 * 1000

  // Check if the time since the last group exceeds 5 minutes
  if (newTimestamp - latestTimestamp < fiveMinutesInMillis) {
    // Not more than 5 minutes, use the existing group
    return latestKey
  } else {
    // More than 5 minutes, create a new group
    return String(newTimestamp)
  }
}

/**
 * Screenshot Thunk (following the vaultThunk pattern)
 * Handles the complete process of calculating group timestamps, taking screenshots, and converting data.
 */
export const captureScreenshotThunk =
  (sourceId: string) => async (_dispatch: AppDispatch, getState: () => RootState) => {
    try {
      const state = getState()
      const { currentSession } = state.screen

      const currentTimestamp = Date.now()

      // Calculate group timestamp
      const groupTimestamp = calculateGroupTimestamp(currentSession, currentTimestamp)

      // logger.info(`📸 Starting screenshot, group timestamp: ${groupTimestamp}`)

      // Call the screenshot API
      const result = await window.screenMonitorAPI.takeScreenshot(groupTimestamp, sourceId)
      if (!result.success || !result.screenshotInfo) {
        throw new Error(result.error || 'Screenshot failed to return screenshotInfo.')
      }

      // Read image Base64 data
      const imageBase64 = await window.screenMonitorAPI.readImageAsBase64(result.screenshotInfo.url)
      if (!imageBase64.success || !imageBase64.data) {
        throw new Error(imageBase64.error || 'Failed to read image data.')
      }

      // Build the screenshot record
      const newScreenshot: ScreenshotRecord = {
        id: `screenshot-${result.screenshotInfo.timestamp}`,
        date: result.screenshotInfo.date,
        timestamp: result.screenshotInfo.timestamp,
        base64_url: `data:image/png;base64,${imageBase64.data}`,
        image_url: result.screenshotInfo.url,
        description: '自动截图',
        group_id: groupTimestamp // 添加分组ID
      }

      // Temporarily deprecated
      // Use the new action to add directly to the calculated group
      // dispatch(addScreenshotToGroup({
      //   screenshot: newScreenshot,
      //   groupKey: groupTimestamp
      // }))

      // logger.info(`📸 Screenshot successful, added to group: ${groupTimestamp}, file path: ${result.screenshotInfo.url}`)
      return newScreenshot
    } catch (error: any) {
      logger.error('📸 Screenshot failed:', error)
      throw error
    }
  }

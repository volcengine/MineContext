// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
export interface ScreenshotRecord {
  id: string
  date: string
  timestamp: number
  base64_url?: string
  image_url: string
  description?: string
  group_id?: string // 分组ID，用于标识截图属于哪个时间分组
}
export interface MonitorSession {
  date: string // 日期，当作唯一的key
  screenshots: Record<string, ScreenshotRecord[]>
}

export interface ScreenState {
  isMonitoring: boolean
  currentSession: MonitorSession | null
}

const initialState = {
  isMonitoring: false,
  // TODO：第一次打开应用时，应该根据当天日期从后台获取数据，并且isMonitoring 为false
  // 由于后端会去重截图，数据一致性如何保证？ —— 当前不考虑
  currentSession: null as MonitorSession | null
}

const screenSlice = createSlice({
  name: 'screen',
  initialState,
  reducers: {
    setIsMonitoring(state, action: PayloadAction<boolean>) {
      state.isMonitoring = action.payload
    },
    setCurrentSession(state, action: PayloadAction<MonitorSession | null>) {
      state.currentSession = action.payload
    },
    // 添加截图到指定分组（简化版，分组逻辑在 thunk 中处理）
    addScreenshotToGroup(state, action: PayloadAction<{ screenshot: ScreenshotRecord; groupKey: string }>) {
      if (!state.currentSession) return

      const { screenshot, groupKey } = action.payload
      const newScreenshots = { ...state.currentSession.screenshots }

      // 直接添加到指定分组
      if (!newScreenshots[groupKey]) {
        newScreenshots[groupKey] = []
      }
      newScreenshots[groupKey] = [...newScreenshots[groupKey], screenshot]

      state.currentSession.screenshots = newScreenshots
      console.log('添加截图到分组:', groupKey, state.currentSession)
    },
    // 专门处理删除截图的 action
    removeScreenshot(state, action: PayloadAction<{ screenshotId: string }>) {
      if (!state.currentSession) return

      const { screenshotId } = action.payload
      const newScreenshots = { ...state.currentSession.screenshots }

      for (const key in newScreenshots) {
        const index = newScreenshots[key].findIndex((s) => s.id === screenshotId)
        if (index !== -1) {
          newScreenshots[key].splice(index, 1)
          // If the group becomes empty, remove the group key
          if (newScreenshots[key].length === 0) {
            delete newScreenshots[key]
          }
          break // Assume screenshot IDs are unique, so we can stop.
        }
      }

      state.currentSession.screenshots = newScreenshots
    },
    // 初始化当天的截图数据
    initializeSessionWithScreenshots(state, action: PayloadAction<{ date: string; screenshots: ScreenshotRecord[] }>) {
      const { date, screenshots } = action.payload

      // 创建或更新当前会话
      if (!state.currentSession || state.currentSession.date !== date) {
        state.currentSession = {
          date,
          screenshots: {}
        }
      }

      // 按照 group_id 分组处理截图（使用后端返回的分组信息）
      const groupedScreenshots: Record<string, ScreenshotRecord[]> = {}

      screenshots.forEach(screenshot => {
        // 使用 group_id 作为分组键，如果没有则使用时间戳作为后备
        const groupKey = screenshot.group_id || String(screenshot.timestamp)

        if (!groupedScreenshots[groupKey]) {
          groupedScreenshots[groupKey] = []
        }

        groupedScreenshots[groupKey].push(screenshot)
      })

      state.currentSession.screenshots = groupedScreenshots
      console.log('初始化会话截图数据:', state.currentSession)
    }
  }
})

export const {
  setIsMonitoring,
  setCurrentSession,
  addScreenshotToGroup,
  removeScreenshot,
  initializeSessionWithScreenshots,
} = screenSlice.actions

export default screenSlice.reducer

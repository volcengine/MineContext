// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('screen')

export interface ScreenshotRecord {
  id: string
  date: string
  timestamp: number
  base64_url?: string
  image_url: string
  description?: string
  group_id?: string // Group ID, used to identify which time group the screenshot belongs to
}
export interface MonitorSession {
  date: string // Date, used as a unique key
  screenshots: Record<string, ScreenshotRecord[]>
}

export interface ScreenState {
  isMonitoring: boolean
  currentSession: MonitorSession | null
}

const initialState = {
  isMonitoring: false,
  // TODO: When the application is opened for the first time, data should be fetched from the backend based on the current date, and isMonitoring should be false
  // Since the backend will deduplicate screenshots, how to ensure data consistency? - Not considered for now
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
    // Add screenshot to a specified group (simplified version, grouping logic is handled in the thunk)
    addScreenshotToGroup(state, action: PayloadAction<{ screenshot: ScreenshotRecord; groupKey: string }>) {
      if (!state.currentSession) return

      const { screenshot, groupKey } = action.payload
      const newScreenshots = { ...state.currentSession.screenshots }

      // Add directly to the specified group
      if (!newScreenshots[groupKey]) {
        newScreenshots[groupKey] = []
      }
      newScreenshots[groupKey] = [...newScreenshots[groupKey], screenshot]

      state.currentSession.screenshots = newScreenshots
      logger.debug('Adding screenshot to group', { groupKey, session: state.currentSession })
    },
    // Action specifically for deleting screenshots
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
    // Initialize screenshot data for the current day
    initializeSessionWithScreenshots(state, action: PayloadAction<{ date: string; screenshots: ScreenshotRecord[] }>) {
      const { date, screenshots } = action.payload

      // Create or update the current session
      if (!state.currentSession || state.currentSession.date !== date) {
        state.currentSession = {
          date,
          screenshots: {}
        }
      }

      // Group screenshots by group_id (using grouping information returned from the backend)
      const groupedScreenshots: Record<string, ScreenshotRecord[]> = {}

      screenshots.forEach((screenshot) => {
        // Use group_id as the grouping key, or the timestamp as a fallback if it doesn't exist
        const groupKey = screenshot.group_id || String(screenshot.timestamp)

        if (!groupedScreenshots[groupKey]) {
          groupedScreenshots[groupKey] = []
        }

        groupedScreenshots[groupKey].push(screenshot)
      })

      state.currentSession.screenshots = groupedScreenshots
      logger.debug('Initializing session screenshot data', { session: state.currentSession })
    }
  }
})

export const {
  setIsMonitoring,
  setCurrentSession,
  addScreenshotToGroup,
  removeScreenshot,
  initializeSessionWithScreenshots
} = screenSlice.actions

export default screenSlice.reducer

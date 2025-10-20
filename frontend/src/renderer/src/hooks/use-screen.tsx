// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Message } from '@arco-design/web-react'
import { useSelector } from 'react-redux'
import { useMemoizedFn, useMount } from 'ahooks'
import dayjs from 'dayjs'

import { RootState, useAppDispatch } from '@renderer/store'
import {
  setIsMonitoring as setIsMonitoringAction,
  setCurrentSession as setCurrentSessionAction,
  removeScreenshot as removeScreenshotAction,
  MonitorSession,
  ScreenshotRecord
} from '@renderer/store/screen'
import { captureScreenshotThunk } from '@renderer/store/thunk/screenThunk'
import { CaptureSource } from '@renderer/atom/capture.atom'
import axiosInstance from '@renderer/services/axiosConfig'
import { timeToISOTimeString } from '@renderer/utils/time'
import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('useScreen')

// As long as the application is not closed, this variable resides in memory and will not be garbage collected
export const intervalRef: { current: NodeJS.Timeout | null } = { current: null }

export const useScreen = () => {
  const dispatch = useAppDispatch()
  const isMonitoring = useSelector((state: RootState) => state.screen.isMonitoring)
  const currentSession = useSelector((state: RootState) => state.screen.currentSession) as MonitorSession | null
  const [hasPermission, setHasPermission] = useState(false)
  // const [initialized, setInitialized] = useState(false)
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  const checkPermissions = useMemoizedFn(async () => {
    const permission = await window.screenMonitorAPI.checkPermissions()
    if (!permission) {
      Message.error('Screen recording permission is required.')
      setHasPermission(false)
    } else {
      setHasPermission(true)
    }
  })

  const grantPermission = useMemoizedFn(() => {
    window.screenMonitorAPI.openPrefs()
    setTimeout(checkPermissions, 5000)
  })

  const setIsMonitoring = useMemoizedFn((isMonitoring: boolean) => {
    dispatch(setIsMonitoringAction(isMonitoring))
  })

  const setCurrentSession = useMemoizedFn((newCurrentSession: MonitorSession | null) => {
    dispatch(setCurrentSessionAction(newCurrentSession))
  })

  const removeScreenshot = useMemoizedFn((screenshotId: string) => {
    dispatch(removeScreenshotAction({ screenshotId }))
  })
  const [isProgressing, setIsProgressing] = useState(false)

  // Automatic screenshot (using thunk)
  const captureScreenshot = useMemoizedFn(async (visibleSources: CaptureSource[]) => {
    if (isProgressing) {
      return
    }
    setIsProgressing(true)
    try {
      // Step 1: Capture only visible sources
      const capturePromises = visibleSources.map(async (source) => {
        try {
          const screenshot = await dispatch(captureScreenshotThunk(source.id))
          if (screenshot) {
            await postScreenshotToServer(screenshot)
          }
          return { source: source, success: true }
        } catch (error) {
          logger.error(`Failed to capture ${source.name}`, { error })
          return { source: source, success: false }
        }
      })

      const captureResults = await Promise.all(capturePromises)
      setIsProgressing(false)
      logger.debug(
        'Capture results:',
        captureResults.map((r) => ({ name: r.source?.name, success: r.success }))
      )
    } catch (error) {
      setIsProgressing(false)
      logger.error('Failed to capture visible sources', { error })
    }
  })

  // Get new activities
  const getNewActivities = useMemoizedFn(async (lastEndTime: string) => {
    const res = await window.dbAPI.getNewActivities(lastEndTime)
    if (res) {
      return res
    } else {
      console.log('No new activities')
      return []
    }
  })

  // Get activities for a specific date
  const getActivitiesByDate = useMemoizedFn(async (date: Date) => {
    const startOfDay = dayjs(date).startOf('day').toDate()
    const endOfDay = dayjs(date).endOf('day').toDate()

    const res = await window.dbAPI.getNewActivities(timeToISOTimeString(startOfDay), timeToISOTimeString(endOfDay))
    if (res.length > 0) {
      console.log('Retrieved activities for the day')
      return res
    } else {
      console.log('No activities for the day')
      return []
    }
  })

  // Load and display image
  const loadAndShowImage = useMemoizedFn(async (screenshot: ScreenshotRecord) => {
    if (screenshot.base64_url) {
      setSelectedImage(screenshot.base64_url)
    } else if (screenshot.image_url) {
      try {
        const result = await window.screenMonitorAPI.readImageAsBase64(screenshot.image_url)
        if (result.success && result.data) {
          const base64Url = `data:image/png;base64,${result.data}`
          setSelectedImage(base64Url)
        } else {
          Message.error('Failed to load image')
        }
      } catch (error) {
        console.error('Failed to load image:', error)
        Message.error('Failed to load image')
      }
    }
  })

  // Screenshot download handler
  const downloadScreenshot = useMemoizedFn(async (screenshot: ScreenshotRecord) => {
    console.log('downloadScreenshot', screenshot)
    try {
      let base64Url = screenshot.base64_url

      // If no base64 data, load from file
      if (!base64Url && screenshot.image_url) {
        const result = await window.screenMonitorAPI.readImageAsBase64(screenshot.image_url)
        if (result.success && result.data) {
          base64Url = `data:image/png;base64,${result.data}`
        } else {
          console.error('Failed to read image data')
          return
        }
      }

      if (base64Url) {
        const link = document.createElement('a')
        link.href = base64Url
        link.download = `screenshot-${screenshot.timestamp}.png`
        link.click()
        Message.success('Download has started')
      } else {
        Message.error('Unable to get image data')
      }
    } catch (error) {
      console.error('Failed to download screenshot:', error)
    }
  })

  const postScreenshotToServer = useMemoizedFn(async (screenshot: ScreenshotRecord) => {
    try {
      const data = {
        path: screenshot.image_url,
        window: 'Test Window',
        create_time: dayjs(screenshot.timestamp).toISOString(),
        app: 'Test App'
      }
      const res = await axiosInstance.post('/api/add_screenshot', data)
      if (res.status === 200) {
        console.log('Screenshot uploaded successfully')
      } else {
        console.error('Screenshot upload failed')
      }
    } catch (error) {
      console.error('Failed to upload screenshot:', error)
    }
  })

  useMount(() => {
    checkPermissions()
  })

  return {
    isMonitoring,
    setIsMonitoring,
    currentSession,
    setCurrentSession,
    removeScreenshot,
    captureScreenshot,
    hasPermission,
    grantPermission,
    selectedImage,
    setSelectedImage,
    loadAndShowImage,
    downloadScreenshot,
    getNewActivities,
    getActivitiesByDate
  }
}

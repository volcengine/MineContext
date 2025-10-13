// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useState } from 'react'
import { Message } from '@arco-design/web-react'
import { useSelector } from 'react-redux'
import { RootState, useAppDispatch } from '@renderer/store'
import axiosInstance from '@renderer/services/axiosConfig'

import {
  setIsMonitoring as setIsMonitoringAction,
  setCurrentSession as setCurrentSessionAction,
  removeScreenshot as removeScreenshotAction,
  MonitorSession,
  ScreenshotRecord
} from '@renderer/store/screen'
import { captureScreenshotThunk } from '@renderer/store/thunk/screenThunk'
import { timeToISOTimeString } from '@renderer/utils/time'
import { useMemoizedFn, useMount } from 'ahooks'
import { CaptureSource } from '@renderer/atom/capture.atom'

// 只要应用不关闭，此变量常驻内存，不会被GC
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
      Message.error('需要屏幕录制权限。')
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

  // 自动截图（使用 thunk）
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
          console.error(`[ScreenshotMonitor] Exception capturing ${source.name}:`, error)
          return { source: source, success: false }
        }
      })

      const captureResults = await Promise.all(capturePromises)
      setIsProgressing(false)
      console.log(
        `[ScreenshotMonitor] Capture results:`,
        captureResults.map((r) => ({ name: r.source?.name, success: r.success }))
      )
    } catch (error) {
      setIsProgressing(false)
      console.error('[ScreenshotMonitor] Exception capturing visibleSources:', error)
    }
  })

  // 获取新的activities
  const getNewActivities = useMemoizedFn(async (lastEndTime: string) => {
    const res = await window.dbAPI.getNewActivities(lastEndTime)
    if (res) {
      console.log('有新的活动')
      return res
    } else {
      console.log('没有新的活动')
      return []
    }
  })

  // 获取指定日期的activities
  const getActivitiesByDate = useMemoizedFn(async (date: Date) => {
    const startOfDay = new Date(date)
    startOfDay.setHours(0, 0, 0, 0)

    const endOfDay = new Date(date)
    endOfDay.setHours(23, 59, 59, 999)

    const res = await window.dbAPI.getNewActivities(timeToISOTimeString(startOfDay), timeToISOTimeString(endOfDay))
    if (res.length > 0) {
      console.log('获取到当天的 activities')
      return res
    } else {
      console.log('当天没有 activities')
      return []
    }
  })

  // 加载并显示图片
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
          Message.error('加载图片失败')
        }
      } catch (error) {
        console.error('加载图片失败:', error)
        Message.error('加载图片失败')
      }
    }
  })

  // 下载截图处理函数
  const downloadScreenshot = useMemoizedFn(async (screenshot: ScreenshotRecord) => {
    console.log('downloadScreenshot', screenshot)
    try {
      let base64Url = screenshot.base64_url

      // 如果没有 base64 数据，则从文件加载
      if (!base64Url && screenshot.image_url) {
        const result = await window.screenMonitorAPI.readImageAsBase64(screenshot.image_url)
        if (result.success && result.data) {
          base64Url = `data:image/png;base64,${result.data}`
        } else {
          console.error('读取图片数据失败')
          return
        }
      }

      if (base64Url) {
        const link = document.createElement('a')
        link.href = base64Url
        link.download = `screenshot-${screenshot.timestamp}.png`
        link.click()
        Message.success('下载已开始')
      } else {
        Message.error('无法获取图片数据')
      }
    } catch (error) {
      console.error('下载截图失败:', error)
    }
  })

  const postScreenshotToServer = useMemoizedFn(async (screenshot: ScreenshotRecord) => {
    try {
      const data = {
        path: screenshot.image_url,
        window: 'Test Window',
        create_time: new Date(screenshot.timestamp).toISOString(),
        app: 'Test App'
      }
      const res = await axiosInstance.post('/api/add_screenshot', data)
      if (res.status === 200) {
        console.log('截图上传成功')
      } else {
        console.error('截图上传失败')
      }
    } catch (error) {
      console.error('上传截图失败:', error)
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

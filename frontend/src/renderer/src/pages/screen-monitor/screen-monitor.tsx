import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Modal, Image, Form, Message } from '@arco-design/web-react'
import { useSetting } from '@renderer/hooks/useSetting'
import { useScreen, intervalRef } from '@renderer/hooks/useScreen'

import { useMemoizedFn } from 'ahooks'
import { useCheckVisibleSources } from './hooks/useCheckVisibleSources'
import {
  appStore,
  CaptureSource,
  loadableCaptureSourcesAtom,
  loadableCaptureSourcesFromSettingsAtom,
  refreshCaptureSourcesAtom,
  refreshCaptureSourcesFromSettingsAtom
} from '@renderer/atom/capture.atom'
import { get } from 'lodash'
import { useAtomValue } from 'jotai'
import { useServiceHandler } from '@renderer/atom/event-loop.atom'
// Extracted components
import ScreenMonitorHeader from './components/screen-monitor-header'
import DateNavigation from './components/date-navigation'
import RecordingTimeline from './components/recording-timeline'
import EmptyStatePlaceholder from './components/empty-state-placeholder'
import SettingsModal from './components/settings-modal'
import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('ScreenMonitor')

export interface Activity {
  id: string
  start_time: string
  end_time: string // Add optional end_time field
  resources: Array<{
    type: string
    id: string
    path: string
  }>
  title: string
  content: string
}

const ScreenMonitor: React.FC = () => {
  const {
    recordInterval,
    recordingHours,
    enableRecordingHours,
    applyToDays,
    setRecordInterval,
    setEnableRecordingHours,
    setRecordingHours,
    setApplyToDays
  } = useSetting()
  const {
    isMonitoring,
    setIsMonitoring,
    currentSession,
    captureScreenshot,
    hasPermission,
    grantPermission,
    selectedImage,
    setSelectedImage,
    getNewActivities,
    getActivitiesByDate
  } = useScreen()
  // Get selectable sources
  const sources = useAtomValue(loadableCaptureSourcesAtom, { store: appStore })
  // Used to update whether the optional application list has been read to render the page
  // const [sourcesRead, setSourcesRead] = useState(false)
  const screenAllSources = useMemo(() => {
    return (sources.state === 'hasData' ? sources.data.screenSources : []).filter((v) => v.isVisible)
  }, [sources])
  const appAllSources = useMemo(() => {
    return (sources.state === 'hasData' ? sources.data.appSources : []).filter((v) => v.isVisible)
  }, [sources])
  const { checkVisibleSources, clearCache } = useCheckVisibleSources()

  const [currentDate, setCurrentDate] = useState(new Date())
  const isToday = currentDate.toDateString() === new Date().toDateString()
  const screenshots = currentSession?.screenshots || {}
  const [settingsVisible, setSettingsVisible] = useState(false)
  const [activities, setActivities] = useState<Activity[]>([])
  const activityPollingRef = useRef<NodeJS.Timeout | null>(null)
  const lastCheckedTimeRef = useRef<string>(
    activities.length > 0
      ? activities[activities.length - 1].end_time || activities[activities.length - 1].start_time
      : new Date().toISOString()
  )
  const isScreenLockedRef = useRef(false)

  // Settings form state
  const [tempRecordInterval, setTempRecordInterval] = useState(recordInterval)
  const [tempEnableRecordingHours, setTempEnableRecordingHours] = useState(enableRecordingHours)
  const [tempRecordingHours, setTempRecordingHours] = useState<[string, string]>(recordingHours as [string, string])
  const [tempApplyToDays, setTempApplyToDays] = useState(applyToDays)

  // Refresh the application list and trigger a re-render
  const refreshSourcesRead = useMemoizedFn(async () => {
    await appStore.set(refreshCaptureSourcesAtom)
  })

  useEffect(() => {
    const initActivities = async () => {
      const date = new Date(currentDate)
      date.setHours(0, 0, 0, 0)
      const todayActivities = await getActivitiesByDate(date)
      const todayActivitiesParsed: Activity[] = todayActivities.map((item: any) => ({
        ...item,
        resources: JSON.parse(item.resources)
      }))
      const uniqueActivities = Array.from(new Map(todayActivitiesParsed.map((item) => [item.id, item])).values())
      setActivities(uniqueActivities)

      // Reset lastCheckedTimeRef to the time of the last activity of the day
      if (uniqueActivities.length > 0) {
        const latestActivity = uniqueActivities[uniqueActivities.length - 1]
        lastCheckedTimeRef.current = latestActivity.end_time || latestActivity.start_time
      } else {
        // If there are no activities, reset to the start of the day
        const dayStart = new Date(currentDate)
        dayStart.setHours(0, 0, 0, 0)
        lastCheckedTimeRef.current = dayStart.toISOString()
      }
    }
    initActivities()
  }, [currentDate, getActivitiesByDate])

  // Manage polling when date or monitoring status changes
  useEffect(() => {
    if (isMonitoring) {
      if (isToday) {
        // If switched to today and monitoring, start polling
        startActivityPolling()
      } else {
        // If switched to historical date, stop polling
        stopActivityPolling()
      }
    }
  }, [currentDate, isMonitoring, isToday])

  const handlePreviousDay = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() - 1)
    setCurrentDate(newDate)
  }

  const handleNextDay = () => {
    const newDate = new Date(currentDate)
    newDate.setDate(newDate.getDate() + 1)
    setCurrentDate(newDate)
  }

  const handleDateChange = (_dateString, date) => {
    setCurrentDate(date.toDate())
  }

  const disabledDate = (current) => {
    return current && current > new Date()
  }

  // Start monitoring session
  const startMonitoring = () => {
    // Take screenshot, save locally, and send to backend
    startCapture()
    // Start polling for new activities
    startActivityPolling()
  }

  // Stop monitoring
  const stopMonitoring = () => {
    if (isMonitoring) {
      setIsMonitoring(false)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      // Stop polling for new activities
      stopActivityPolling()
      clearCache()
    }
  }

  // Pause monitoring (when screen is locked)
  const pauseMonitoring = useMemoizedFn(() => {
    logger.info('Screen locked, pausing monitoring timers')
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    stopActivityPolling()
  })

  // Resume monitoring (when screen is unlocked)
  const resumeMonitoring = useMemoizedFn(() => {
    logger.info('Screen unlocked, resuming monitoring timers')
    if (isMonitoring && !isScreenLockedRef.current) {
      // Resume screenshot timer
      startCapture()
      // Resume activity polling
      startActivityPolling()
    }
  })

  // Start polling for new activities
  const startActivityPolling = useMemoizedFn(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
    }
    // Immediately execute a check for new activities
    const checkNewActivities = async () => {
      try {
        // Only poll for new activities when viewing today
        if (!isToday) {
          return
        }

        const newActivities = await getNewActivities(lastCheckedTimeRef.current)
        const newActivitiesParsed: Activity[] = newActivities.map((item: any) => ({
          ...item,
          resources: JSON.parse(item.resources)
        }))
        if (newActivitiesParsed && newActivitiesParsed.length > 0) {
          // Filter activities for the current date
          const currentDateStr = currentDate.toISOString().split('T')[0]
          const filteredActivities = newActivitiesParsed.filter((activity) => {
            const activityDateStr = new Date(activity.start_time).toISOString().split('T')[0]
            return activityDateStr === currentDateStr
          })

          if (filteredActivities.length > 0) {
            // Update last checked time to the latest activity's start time
            const latestActivity = filteredActivities[filteredActivities.length - 1]
            lastCheckedTimeRef.current = latestActivity.start_time
            // Add new activities to the beginning of the activities array (maintaining time order) and deduplicate
            setActivities((prev) => {
              const existingIds = new Set(prev.map((a) => a.id))
              const uniqueNewActivities = filteredActivities.filter((a) => !existingIds.has(a.id))
              return [...uniqueNewActivities, ...prev]
            })
          }
        }
      } catch (error) {
        logger.error('Failed to check new activity', { error })
      }
    }
    // Execute immediately
    checkNewActivities()
    // Set timer
    activityPollingRef.current = setInterval(checkNewActivities, 5000) // Poll every 5 seconds
  })

  // Stop polling for new activities
  const stopActivityPolling = useMemoizedFn(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
      activityPollingRef.current = null
    }
  })

  // Clean up polling on component unmount
  useEffect(() => {
    return () => {
      stopActivityPolling()
    }
  }, [stopActivityPolling])

  // Listen for lock/unlock screen events
  useServiceHandler('lock-screen', () => {
    isScreenLockedRef.current = true
    if (isMonitoring) {
      pauseMonitoring()
    }
  })

  useServiceHandler('unlock-screen', () => {
    isScreenLockedRef.current = false
    if (isMonitoring) {
      resumeMonitoring()
    }
  })

  const openSettings = useMemoizedFn(async () => {
    // Refresh the application list before opening settings
    try {
      setSettingsVisible(true)
      await refreshSourcesRead()
    } catch (error) {
      logger.error('Failed to refresh application list', { error })
    }
  })
  const [applicationVisible, setApplicationVisible] = useState(false)

  const handleCancelSettings = useMemoizedFn(() => {
    setTempRecordInterval(recordInterval)
    setTempEnableRecordingHours(enableRecordingHours)
    setTempRecordingHours(recordingHours as [string, string])
    setTempApplyToDays(applyToDays)
    setSettingsVisible(false)
    setApplicationVisible(false)
  })

  const handleSaveSettings = useMemoizedFn(() => {
    setRecordInterval(tempRecordInterval)
    setEnableRecordingHours(tempEnableRecordingHours)
    setRecordingHours(tempRecordingHours as [string, string])
    setApplyToDays(tempApplyToDays as 'weekday' | 'everyday')
    setSettingsVisible(false)
  })

  // Check if recording is possible under the current settings
  const [canRecord, setCanRecord] = useState(false)
  const checkCanRecord = useMemoizedFn(() => {
    if (enableRecordingHours) {
      const currentDay = new Date().getDay()
      const currentHour = new Date().getHours()
      const currentMinute = new Date().getMinutes()

      // Check if within the allowed date range
      if (applyToDays === 'weekday') {
        // 0 = Sunday, 6 = Saturday, 1-5 = Monday-Friday
        if (currentDay === 0 || currentDay === 6) {
          setCanRecord(false)
          return false
        }
      }

      // Check if within the allowed time range
      if (recordingHours && recordingHours.length === 2) {
        const [startTime, endTime] = recordingHours
        const [startHour, startMinute] = startTime.split(':').map(Number)
        const [endHour, endMinute] = endTime.split(':').map(Number)

        const currentTotalMinutes = currentHour * 60 + currentMinute
        const startTotalMinutes = startHour * 60 + startMinute
        const endTotalMinutes = endHour * 60 + endMinute

        // If the end time is less than the start time, it spans across midnight
        if (endTotalMinutes < startTotalMinutes) {
          // The current time is after the start time or before the end time
          const result = currentTotalMinutes >= startTotalMinutes || currentTotalMinutes <= endTotalMinutes
          setCanRecord(result)
          return result
        } else {
          // Normal time range
          const result = currentTotalMinutes >= startTotalMinutes && currentTotalMinutes <= endTotalMinutes
          setCanRecord(result)
          return result
        }
      }
    }
    setCanRecord(true)
    return true
  })

  // Check recording status on component mount
  useEffect(() => {
    checkCanRecord()
  }, [checkCanRecord])

  // Periodically check recording status
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isMonitoring && enableRecordingHours) {
      interval = setInterval(() => {
        checkCanRecord()
      }, 60000) // Check every minute
    }
    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [isMonitoring, enableRecordingHours, checkCanRecord])
  // Get sources
  const settingSources = useAtomValue(loadableCaptureSourcesFromSettingsAtom, { store: appStore })
  const settingScreenSources = useMemo(
    () => (settingSources.state === 'hasData' ? get(settingSources, 'data.screenSources') : ([] as CaptureSource[])),
    [settingSources]
  )
  const settingWindowSources = useMemo(
    () => (settingSources.state === 'hasData' ? get(settingSources, 'data.appSources') : ([] as CaptureSource[])),
    [settingSources]
  )
  const [form] = Form.useForm<{ screenSources?: string[]; windowSources?: string[] }>()
  // Save settings to local
  const entry = useMemoizedFn(async () => {
    const screenIds = settingScreenSources?.map((v) => v.id) || []
    const windowIds = settingWindowSources?.map((v) => v.id) || []
    const screenList = screenAllSources?.filter((source) => screenIds?.includes(source.id)) || []
    const windowList = appAllSources?.filter((source) => windowIds?.includes(source.id)) || []
    const screenSources = screenList.map((source) => source.id)
    form.setFieldsValue({
      screenSources: screenSources.length > 0 ? screenSources : [get(screenAllSources[0], 'id')].filter(Boolean),
      windowSources: windowList.map((source) => source.id)
    })
  })
  // When the user has not selected any screen or window, the first screen is selected by default, but you need to wait for the settings to be saved successfully to start recording, which will lose a few seconds of screenshots
  const getVisibleSources = useMemoizedFn(async () => {
    const screenIds = settingScreenSources?.map((v) => v.id) || []
    const windowIds = settingWindowSources?.map((v) => v.id) || []
    // Get raw data
    const screenSourcesData =
      screenIds.length === 0 && windowIds.length === 0
        ? [get(screenAllSources, '0')].filter(Boolean)
        : screenAllSources?.filter((source) => screenIds?.includes(source.id)) || []
    const windowSourcesData = appAllSources?.filter((source) => windowIds?.includes(source.id)) || []

    const visibleScreenSources = await checkVisibleSources([...screenSourcesData, ...windowSourcesData])
    const visibleSources = [...screenSourcesData, ...windowSourcesData].filter(
      (source) => visibleScreenSources[source.id]
    )

    //
    if (visibleSources.length === 0) {
      logger.debug('No selected apps are currently visible, skipping capture')
      return []
    }
    return visibleSources
  })
  // Start taking screenshots
  const startCapture = useMemoizedFn(async () => {
    setIsMonitoring(true)
    try {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      // Take a screenshot immediately
      const canRecordNow = checkCanRecord()
      if (canRecordNow) {
        const visibleSources = await getVisibleSources()
        if (!visibleSources) {
          return
        }
        await captureScreenshot(visibleSources)
      }
      // Set timer
      intervalRef.current = setInterval(async () => {
        // Check if the timer is still valid (to prevent execution after component unmount)
        if (intervalRef.current) {
          const canRecordNow = checkCanRecord()
          // Check if within the allowed recording time range
          if (canRecordNow) {
            const visibleSources = await getVisibleSources()
            if (!visibleSources) {
              return
            }
            await captureScreenshot(visibleSources)
          }
        }
      }, recordInterval * 1000)
    } catch (error) {
      logger.error('Failed to start screenshot service', { error })
    }
  })

  // Tips: The biggest problem with using Form for management is that when the user does not select any screen or window, it will cause the save to fail
  const handleSave = useMemoizedFn(async () => {
    const values = form.getFieldsValue()
    if (![...(values.screenSources || []), ...(values.windowSources || [])].length) {
      Message.info('Please select at least one screen or window')
      return
    }
    const screenList = screenAllSources?.filter((source) => values.screenSources?.includes(source.id)) || []
    const windowList = appAllSources?.filter((source) => values.windowSources?.includes(source.id)) || []
    await window.screenMonitorAPI.setSettings('settings', {
      screenList,
      windowList
    })
    handleSaveSettings()
    await appStore.set(refreshCaptureSourcesFromSettingsAtom)
  })

  useEffect(() => {
    if (settingSources.state === 'hasData' && sources.state === 'hasData') {
      entry()
      setTempRecordInterval(recordInterval)
      setTempEnableRecordingHours(enableRecordingHours)
      setTempRecordingHours(recordingHours as [string, string])
      setTempApplyToDays(applyToDays)
    }
  }, [settingSources, sources])

  const handleRequestPermission = useMemoizedFn(async () => {
    await grantPermission()
  })

  return (
    <div className="fixed top-0 left-0 flex flex-col h-screen overflow-y-hidden p-[8px] pl-0 rounded-[20px] relative">
      <div className="bg-white rounded-[16px] p-6 h-[calc(100%-8px)] flex flex-col overflow-y-auto overflow-x-hidden scrollbar-hide pb-2">
        <ScreenMonitorHeader
          hasPermission={hasPermission}
          isMonitoring={isMonitoring}
          isToday={isToday}
          screenAllSources={screenAllSources}
          appAllSources={appAllSources}
          onOpenSettings={openSettings}
          onStartMonitoring={startMonitoring}
          onStopMonitoring={stopMonitoring}
          onRequestPermission={handleRequestPermission}
        />

        {/* Recording area */}
        <div className="w-full mb-0 mx-auto flex-1 flex flex-col">
          <div className="border-2 border-dashed border-gray-300 rounded-[12px] p-[30px] bg-gray-50 transition-all duration-300 flex-1 flex flex-col overflow-auto">
            <DateNavigation
              hasPermission={hasPermission}
              currentDate={currentDate}
              isToday={isToday}
              onPreviousDay={handlePreviousDay}
              onNextDay={handleNextDay}
              onDateChange={handleDateChange}
              onSetCurrentDate={setCurrentDate}
              disabledDate={disabledDate}
            />
            {(isMonitoring && isToday) || activities.length > 0 || Object.keys(screenshots).length > 0 ? (
              <RecordingTimeline
                isMonitoring={isMonitoring}
                isToday={isToday}
                canRecord={canRecord}
                activities={activities}
              />
            ) : (
              <EmptyStatePlaceholder
                hasPermission={hasPermission}
                isToday={isToday}
                onGrantPermission={grantPermission}
              />
            )}
          </div>
        </div>

        <Modal
          style={{ width: '60%', minHeight: '30%' }}
          title="Display Screenshot"
          visible={!!selectedImage}
          onCancel={() => setSelectedImage(null)}
          footer={null}>
          {selectedImage && (
            <Image src={selectedImage} alt="Display Screenshot" style={{ width: '100%', borderRadius: 8 }} />
          )}
        </Modal>

        <SettingsModal
          visible={settingsVisible}
          form={form}
          sources={sources}
          screenAllSources={screenAllSources}
          appAllSources={appAllSources}
          applicationVisible={applicationVisible}
          tempRecordInterval={tempRecordInterval}
          tempEnableRecordingHours={tempEnableRecordingHours}
          tempRecordingHours={tempRecordingHours}
          tempApplyToDays={tempApplyToDays}
          onCancel={handleCancelSettings}
          onSave={handleSave}
          onSetApplicationVisible={setApplicationVisible}
          onSetTempRecordInterval={setTempRecordInterval}
          onSetTempEnableRecordingHours={setTempEnableRecordingHours}
          onSetTempRecordingHours={setTempRecordingHours}
          onSetTempApplyToDays={setTempApplyToDays}
        />
      </div>
    </div>
  )
}

export default ScreenMonitor

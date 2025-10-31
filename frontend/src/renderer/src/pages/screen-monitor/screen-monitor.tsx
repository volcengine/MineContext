import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Modal, Image, Form, Message } from '@arco-design/web-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useSetting } from '@renderer/hooks/use-setting'
import { useScreen } from '@renderer/hooks/use-screen'
import dayjs from 'dayjs'

import { useMemoizedFn, useMount } from 'ahooks'
import {
  appStore,
  loadableCaptureSourcesAtom,
  loadableCaptureSourcesFromSettingsAtom,
  refreshCaptureSourcesAtom,
  refreshCaptureSourcesFromSettingsAtom
} from '@renderer/atom/capture.atom'
import { get } from 'lodash'
import { useAtomValue } from 'jotai'
import { useObservableTask } from '@renderer/atom/event-loop.atom'
// Extracted components
import ScreenMonitorHeader from './components/screen-monitor-header'
import DateNavigation from './components/date-navigation'
import RecordingTimeline from './components/recording-timeline'
import EmptyStatePlaceholder from './components/empty-state-placeholder'
import SettingsModal from './components/settings-modal'
import { getLogger } from '@shared/logger/renderer'
import { IpcChannel } from '@shared/IpcChannel'
import type { RecordingStats } from './components/recording-stats-card'
import { CaptureSource } from '@interface/common/source'

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
  const location = useLocation()
  const navigate = useNavigate()
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
    currentSession,
    hasPermission,
    grantPermission,
    selectedImage,
    setSelectedImage,
    getNewActivities,
    getActivitiesByDate
  } = useScreen()
  const [isMonitoring, setIsMonitoring] = useState(false)
  useMount(() => {
    window.serverPushAPI.pushScreenMonitorStatus((status) => {
      setIsMonitoring(status === 'running')
    })
  })
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

  const [currentDate, setCurrentDate] = useState(dayjs().toDate())
  const isToday = dayjs(currentDate).isSame(dayjs(), 'day')
  const screenshots = currentSession?.screenshots || {}
  const [settingsVisible, setSettingsVisible] = useState(false)
  const [activities, setActivities] = useState<Activity[]>([])
  const [recordingStats, setRecordingStats] = useState<RecordingStats | null>(null)
  const activityPollingRef = useRef<NodeJS.Timeout | null>(null)
  const statsPollingRef = useRef<NodeJS.Timeout | null>(null)
  const lastCheckedTimeRef = useRef<string>(
    activities.length > 0
      ? activities[activities.length - 1].end_time || activities[activities.length - 1].start_time
      : dayjs().toISOString()
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
      const date = dayjs(currentDate).startOf('day').toDate()
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
        lastCheckedTimeRef.current = dayjs(currentDate).startOf('day').toISOString()
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
        startStatsPolling()
      } else {
        // If switched to historical date, stop polling
        stopActivityPolling()
        stopStatsPolling()
      }
    } else {
      // If not monitoring, stop all polling
      stopActivityPolling()
      stopStatsPolling()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentDate, isMonitoring, isToday])

  const handlePreviousDay = () => {
    const newDate = dayjs(currentDate).subtract(1, 'day').toDate()
    setCurrentDate(newDate)
  }

  const handleNextDay = () => {
    const newDate = dayjs(currentDate).add(1, 'day').toDate()
    setCurrentDate(newDate)
  }

  const handleDateChange = (_dateString, date) => {
    setCurrentDate(date.toDate())
  }

  const disabledDate = (current) => {
    return current && dayjs(current).isAfter(dayjs(), 'day')
  }

  // Start monitoring session
  const startMonitoring = useMemoizedFn(async () => {
    await window.screenMonitorAPI.updateModelConfig({
      recordInterval,
      recordingHours,
      enableRecordingHours,
      applyToDays
    })
    await window.screenMonitorAPI.startTask()
    // Start polling for new activities
    startActivityPolling()
    // Start polling for recording stats
    startStatsPolling()
  })

  // Stop monitoring
  const stopMonitoring = useMemoizedFn(async () => {
    if (isMonitoring) {
      await window.screenMonitorAPI.stopTask()
      stopActivityPolling()
      stopStatsPolling()
    }
  })

  const pauseMonitoring = useMemoizedFn(() => {
    logger.info('Screen locked, pausing monitoring timers')
    stopActivityPolling()
    stopStatsPolling()
  })

  // Resume monitoring (when screen is unlocked)
  const resumeMonitoring = useMemoizedFn(() => {
    if (isMonitoring && !isScreenLockedRef.current) {
      // Resume activity polling
      startActivityPolling()
      // Resume stats polling
      startStatsPolling()
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
          const currentDateStr = dayjs(currentDate).format('YYYY-MM-DD')
          const filteredActivities = newActivitiesParsed.filter((activity) => {
            const activityDateStr = dayjs(activity.start_time).format('YYYY-MM-DD')
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

  // Start polling for recording stats
  const startStatsPolling = useMemoizedFn(() => {
    if (statsPollingRef.current) {
      clearInterval(statsPollingRef.current)
    }

    const fetchStats = async () => {
      try {
        if (!isToday || !isMonitoring) {
          return
        }
        const stats = await window.screenMonitorAPI.getRecordingStats()
        if (stats) {
          setRecordingStats(stats)
        }
      } catch (error) {
        logger.error('Failed to fetch recording stats', { error })
      }
    }

    // Execute immediately
    fetchStats()
    // Poll every 5 seconds
    statsPollingRef.current = setInterval(fetchStats, 5000)
  })

  // Stop polling for recording stats
  const stopStatsPolling = useMemoizedFn(() => {
    if (statsPollingRef.current) {
      clearInterval(statsPollingRef.current)
      statsPollingRef.current = null
    }
    setRecordingStats(null)
  })

  // Clean up polling on component unmount
  useEffect(() => {
    return () => {
      stopActivityPolling()
      stopStatsPolling()
    }
  }, [stopActivityPolling, stopStatsPolling])

  // Listen for lock/unlock screen events
  useObservableTask(
    {
      active: () => {
        isScreenLockedRef.current = true
        if (isMonitoring) {
          pauseMonitoring()
        }
      },
      inactive: () => {
        isScreenLockedRef.current = false
        if (isMonitoring) {
          resumeMonitoring()
        }
      }
    },
    'screen-monitor'
  )

  // Listen for tray toggle recording event (from Router.tsx when already on this page)
  useEffect(() => {
    const handleTrayToggleRecording = () => {
      if (isMonitoring) {
        stopMonitoring()
      } else {
        startMonitoring()
      }
    }

    window.addEventListener('tray-toggle-recording', handleTrayToggleRecording)

    return () => {
      window.removeEventListener('tray-toggle-recording', handleTrayToggleRecording)
    }
  }, [isMonitoring, startMonitoring, stopMonitoring])

  // Handle navigation state when coming from tray icon while on a different page
  useEffect(() => {
    const state = location.state as { toggleRecording?: boolean } | null
    if (state?.toggleRecording) {
      // Clear the navigation state first to prevent re-triggering
      navigate(location.pathname, { replace: true, state: {} })

      // Toggle recording based on current state
      if (isMonitoring) {
        stopMonitoring()
      } else {
        startMonitoring()
      }
    }
    // Only depend on location.state to avoid re-triggering when isMonitoring changes
    // startMonitoring and stopMonitoring are memoized so they're stable
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

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
  const checkCanRecord = useMemoizedFn(async () => {
    const result = await window.screenMonitorAPI.checkCanRecord()
    setCanRecord(result.canRecord)
    setIsMonitoring(result.status === 'running')
    return result
  })

  // Check recording status on component mount
  useEffect(() => {
    checkCanRecord()
  }, [setCanRecord])

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

  // Sync recording status to tray
  useEffect(() => {
    if (isToday) {
      window.electron.ipcRenderer
        .invoke(IpcChannel.Tray_UpdateRecordingStatus, isMonitoring && canRecord)
        .catch((error) => {
          logger.error('Failed to update tray recording status:', error)
        })
    }
  }, [isMonitoring, canRecord, isToday])

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
    await window.screenMonitorAPI.updateCurrentRecordApp([
      ...(screenList.length > 0 ? screenList : [get(screenAllSources, 0)].filter(Boolean)),
      ...windowList
    ])
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
    await window.screenMonitorAPI.updateCurrentRecordApp([...screenList, ...windowList])
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
    <div className="top-0 left-0 flex flex-col h-screen overflow-y-hidden pr-2 pb-2 pl-0 rounded-[20px] relative">
      <div style={{ height: '8px', appRegion: 'drag' } as React.CSSProperties} />
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
                recordingStats={recordingStats}
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

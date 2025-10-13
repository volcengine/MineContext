// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import {
  Button,
  Space,
  Typography,
  Timeline,
  Modal,
  Image,
  Switch,
  Slider,
  TimePicker,
  Radio,
  Form,
  DatePicker,
  Checkbox,
  Message,
  Popover,
  Spin
} from '@arco-design/web-react'
import { IconPlayArrow, IconSettings, IconRecordStop, IconDown, IconVideoCamera } from '@arco-design/web-react/icon'
import { useSetting } from '@renderer/hooks/useSetting'
import { useScreen, intervalRef } from '@renderer/hooks/useScreen'
import Stopped from '@renderer/assets/images/screen-monitor/stopped.png'
import NeedPermission from '@renderer/assets/images/screen-monitor/need-permission.svg'
import screenMonitorEmpty from '@renderer/assets/images/screen-monitor/screen-monitor-empty.svg'
import { IconLeft, IconRight } from '@arco-design/web-react/icon'

import './ScreenMonitor.css'
import { SCREEN_INTERVAL_TIME } from './constant'
import dayjs from 'dayjs'
import clsx from 'clsx'
import { Application } from './components/application'
import { useMemoizedFn } from 'ahooks'
import screenIcon from '@renderer/assets/icons/screen.svg'
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
import { ActivityTimelineItem } from './components/activitie-timeline-item'
import { formatTime } from '@renderer/utils/time'
import styles from './ScreenMonitor.module.less'
import { useAtomValue } from 'jotai'
import { useServiceHandler } from '@renderer/atom/event-loop.atom'

const { Title, Text } = Typography
const TimelineItem = Timeline.Item

export interface Activity {
  id: string
  start_time: string
  end_time: string // 添加可选的end_time字段
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
  // 获取可以选择的源
  const sources = useAtomValue(loadableCaptureSourcesAtom, { store: appStore })
  // 用于更新可选应用程序列表是否已读取来渲染页面
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
  const [tempRecordingHours, setTempRecordingHours] = useState(recordingHours)
  const [tempApplyToDays, setTempApplyToDays] = useState(applyToDays)

  // 刷新应用程序列表并触发重渲染
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
    }
    initActivities()
  }, [currentDate, getActivitiesByDate])

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

  // 开始监控会话
  const startMonitoring = () => {
    // 截屏、保存本地并向后端发送
    startCapture()
    // 开始轮询检查新活动
    startActivityPolling()
  }

  // 停止监控
  const stopMonitoring = () => {
    if (isMonitoring) {
      setIsMonitoring(false)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      // 停止轮询检查新活动
      stopActivityPolling()
      clearCache()
    }
  }

  // 暂停监控（锁屏时）
  const pauseMonitoring = useMemoizedFn(() => {
    console.log('🔒 Screen locked, pausing monitoring timers...')
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
    stopActivityPolling()
  })

  // 恢复监控（解锁时）
  const resumeMonitoring = useMemoizedFn(() => {
    console.log('🔓 Screen unlocked, resuming monitoring timers...')
    if (isMonitoring && !isScreenLockedRef.current) {
      // 恢复截屏定时器
      startCapture()
      // 恢复活动轮询
      startActivityPolling()
    }
  })

  // 开始轮询检查新活动
  const startActivityPolling = useCallback(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
    }
    // 立即执行一次检查新活动
    const checkNewActivities = async () => {
      try {
        const newActivities = await getNewActivities(lastCheckedTimeRef.current)
        const newActivitiesParsed: Activity[] = newActivities.map((item: any) => ({
          ...item,
          resources: JSON.parse(item.resources)
        }))
        if (newActivitiesParsed && newActivitiesParsed.length > 0) {
          // 更新最后检查时间为最新活动的开始时间
          const latestActivity = newActivitiesParsed[newActivitiesParsed.length - 1]
          lastCheckedTimeRef.current = latestActivity.start_time
          // 将新活动添加到activities数组开头（保持时间顺序），并去重
          setActivities((prev) => {
            const existingIds = new Set(prev.map((a) => a.id))
            const uniqueNewActivities = newActivitiesParsed.filter((a) => !existingIds.has(a.id))
            return [...uniqueNewActivities, ...prev]
          })
        }
      } catch (error) {
        console.error('检查新活动失败:', error)
      }
    }
    // 立即执行一次
    checkNewActivities()
    // 设置定时器
    activityPollingRef.current = setInterval(checkNewActivities, 5000) // 每5秒轮询一次
  }, [])

  // 停止轮询检查新活动
  const stopActivityPolling = useMemoizedFn(() => {
    if (activityPollingRef.current) {
      clearInterval(activityPollingRef.current)
      activityPollingRef.current = null
    }
  })

  // 组件卸载时清理轮询
  useEffect(() => {
    return () => {
      stopActivityPolling()
    }
  }, [stopActivityPolling])

  // 监听锁屏/解锁事件
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
    // 在打开设置前先刷新应用程序列表
    try {
      setSettingsVisible(true)
      await refreshSourcesRead()
    } catch (error) {
      console.error('刷新应用程序列表失败:', error)
    }
  })
  const [applicationVisible, setApplicationVisible] = useState(false)

  const handleCancelSettings = useMemoizedFn(() => {
    setTempRecordInterval(recordInterval)
    setTempEnableRecordingHours(enableRecordingHours)
    setTempRecordingHours(recordingHours)
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

  // 检查当前设置下是否可以录制
  const [canRecord, setCanRecord] = useState(false)
  const checkCanRecord = useMemoizedFn(() => {
    if (enableRecordingHours) {
      const currentDay = new Date().getDay()
      const currentHour = new Date().getHours()
      const currentMinute = new Date().getMinutes()

      // 检查是否在允许的日期范围内
      if (applyToDays === 'weekday') {
        // 0 = Sunday, 6 = Saturday, 1-5 = Monday-Friday
        if (currentDay === 0 || currentDay === 6) {
          setCanRecord(false)
          return false
        }
      }

      // 检查是否在允许的时间范围内
      if (recordingHours && recordingHours.length === 2) {
        const [startTime, endTime] = recordingHours
        const [startHour, startMinute] = startTime.split(':').map(Number)
        const [endHour, endMinute] = endTime.split(':').map(Number)

        const currentTotalMinutes = currentHour * 60 + currentMinute
        const startTotalMinutes = startHour * 60 + startMinute
        const endTotalMinutes = endHour * 60 + endMinute

        // 如果结束时间小于开始时间，说明跨越了午夜
        if (endTotalMinutes < startTotalMinutes) {
          // 当前时间在开始时间之后或结束时间之前
          const result = currentTotalMinutes >= startTotalMinutes || currentTotalMinutes <= endTotalMinutes
          setCanRecord(result)
          return result
        } else {
          // 正常时间范围
          const result = currentTotalMinutes >= startTotalMinutes && currentTotalMinutes <= endTotalMinutes
          setCanRecord(result)
          return result
        }
      }
    }
    setCanRecord(true)
    return true
  })

  // 组件挂载时检查录制状态
  useEffect(() => {
    checkCanRecord()
  }, [checkCanRecord])

  // 定期检查录制状态
  useEffect(() => {
    let interval: NodeJS.Timeout | null = null
    if (isMonitoring && enableRecordingHours) {
      interval = setInterval(() => {
        checkCanRecord()
      }, 60000) // 每分钟检查一次
    }
    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [isMonitoring, enableRecordingHours, checkCanRecord])
  // 获取源
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
  // 保存setting到local
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
  // 当用户没有选择任何屏幕或窗口时，默认选择第一个屏幕，但是开始录制的时候需要等待settings保存成功，会丢失几秒的截图
  const getVisibleSources = useMemoizedFn(async () => {
    const screenIds = settingScreenSources?.map((v) => v.id) || []
    const windowIds = settingWindowSources?.map((v) => v.id) || []
    // 获取原始数据
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
      console.log('[ScreenshotMonitor] No selected apps are currently visible, skipping capture')
      return []
    }
    return visibleSources
  })
  // 开始截屏
  const startCapture = useMemoizedFn(async () => {
    setIsMonitoring(true)
    try {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      // 立即执行一次截图
      const canRecordNow = checkCanRecord()
      if (canRecordNow) {
        const visibleSources = await getVisibleSources()
        if (!visibleSources) {
          return
        }
        await captureScreenshot(visibleSources)
      }
      // 设置定时器
      intervalRef.current = setInterval(async () => {
        // 检查定时器是否仍然有效（防止组件卸载后继续执行）
        if (intervalRef.current) {
          const canRecordNow = checkCanRecord()
          // 检查是否在允许录制的时间范围内
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
      console.error('启动截图服务失败:', error)
    }
  })

  // Tips: 用Form管理最大的问题是当用户没有选择任何屏幕或窗口时，会导致保存失败
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
      setTempRecordingHours(recordingHours)
      setTempApplyToDays(applyToDays)
    }
  }, [settingSources, sources])

  const handleRequestPermission = useMemoizedFn(async () => {
    await grantPermission()
  })

  return (
    <div className="screen-monitor-container">
      <div className="monitor-content-wrapper">
        <div className="monitor-header">
          <div className="monitor-header-left">
            <Title heading={3} style={{ marginTop: 5, fontWeight: 700, fontSize: 24 }}>
              Screen Monitor
            </Title>
            <Text type="secondary" style={{ fontSize: 13 }}>
              Screen Monitor captures anything on your screen and transforms it into intelligent, connected Contexts.
              All data stays local with full privacy protection ✨
            </Text>
          </div>
          <div className="monitor-header-right">
            {hasPermission ? (
              <Space>
                <Popover content="Settings can only be adjusted after Stop Recording." disabled={!isMonitoring}>
                  <Button
                    type="outline"
                    icon={<IconSettings />}
                    size="large"
                    disabled={isMonitoring}
                    onClick={openSettings}>
                    Settings
                  </Button>
                </Popover>
                {!isMonitoring ? (
                  <Popover
                    content="Please click the settings button and select your monitoring window or screen."
                    disabled={!(screenAllSources.length === 0 && appAllSources.length === 0)}>
                    <Button
                      type="primary"
                      icon={<IconPlayArrow />}
                      size="large"
                      onClick={startMonitoring}
                      disabled={isMonitoring || !isToday}
                      style={{ background: '#000' }}>
                      Start Recording
                    </Button>
                  </Popover>
                ) : (
                  <Button
                    type="primary"
                    status="danger"
                    icon={<IconRecordStop />}
                    size="large"
                    onClick={stopMonitoring}>
                    Stop Recording
                  </Button>
                )}
              </Space>
            ) : (
              <Button
                type="primary"
                status="danger"
                icon={<IconVideoCamera />}
                size="large"
                onClick={handleRequestPermission}>
                Request permission
              </Button>
            )}
          </div>
        </div>

        {/* 录制区域 */}
        <div className="recording-area-container">
          <div className="recording-area-dashed" style={{ overflow: 'auto' }}>
            <div
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center' }}>
                {hasPermission && (
                  <>
                    <Button
                      style={{
                        background: '#fff',
                        border: '1px solid #E1E3EF',
                        height: '24px',
                        color: '#000',
                        fontSize: '12px',
                        marginRight: '8px'
                      }}
                      onClick={() => setCurrentDate(new Date())}>
                      Today
                    </Button>
                    <Button
                      icon={<IconLeft />}
                      onClick={handlePreviousDay}
                      style={{ marginRight: '12px', background: 'transparent', border: 'none' }}
                    />
                    <DatePicker
                      value={currentDate}
                      onChange={handleDateChange}
                      disabledDate={disabledDate}
                      triggerElement={
                        <Button style={{ height: '22px', background: 'transparent', border: 'none', padding: 0 }}>
                          <Text style={{ fontWeight: 'medium', fontSize: 14 }}>
                            {dayjs(currentDate).format('MMMM D, YYYY')}
                          </Text>
                          <IconDown style={{ marginLeft: '4px', width: '12px', height: '12px' }} />
                        </Button>
                      }
                    />
                    <Button
                      icon={<IconRight />}
                      onClick={handleNextDay}
                      style={{ marginLeft: '12px', background: 'transparent', border: 'none' }}
                      disabled={isToday}></Button>
                  </>
                )}
              </div>
            </div>
            {(isMonitoring && isToday) || activities.length > 0 || Object.keys(screenshots).length > 0 ? (
              <div className="recording-timeline">
                <Timeline labelPosition="relative">
                  {isToday && (
                    <TimelineItem label="Now">
                      {isMonitoring ? (
                        canRecord ? (
                          <div style={{ width: '100%', fontSize: 14 }}>
                            <Text style={{ fontWeight: 'bold', color: '#5252FF', fontSize: 12 }}>
                              Recording screen...
                            </Text>
                            <div style={{ color: '#C9C9D4' }}>
                              Every {SCREEN_INTERVAL_TIME} minutes, MineContext generates an Activity based on screen
                              analysis.
                            </div>
                          </div>
                        ) : (
                          <div style={{ width: '100%', fontSize: 14 }}>
                            <Text style={{ fontWeight: 'bold', color: '#FF4D4F', fontSize: 12 }}>
                              Recording stopped
                            </Text>
                            <div style={{ color: '#C9C9D4' }}>
                              It's not in recording hours now. Recording will automatically start at the next allowed
                              time.
                            </div>
                          </div>
                        )
                      ) : (
                        <div style={{ width: '100%', fontSize: 14 }}>
                          <Text style={{ fontWeight: 'bold', color: '#FF4D4F', fontSize: 12 }}>Recording stopped</Text>
                          <div style={{ color: '#C9C9D4' }}>You can start recording again</div>
                        </div>
                      )}
                    </TimelineItem>
                  )}

                  {/* 显示activities */}
                  {activities
                    .sort((a, b) => new Date(b.start_time).getTime() - new Date(a.start_time).getTime()) // 按时间倒序排列
                    .map((activity) => (
                      <TimelineItem label={formatTime(activity?.end_time)} key={activity.id}>
                        <ActivityTimelineItem key={activity.id} activity={activity} />
                      </TimelineItem>
                    ))}
                </Timeline>
              </div>
            ) : (
              <div className="recording-area-content">
                <div className="recording-placeholder">
                  {hasPermission ? (
                    isToday ? (
                      <>
                        <img src={Stopped} alt="Screen recording" style={{ width: 66, height: 78 }} />
                        <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                          Start screen recording, and then it will take screenshots and summarize your work records
                          every {SCREEN_INTERVAL_TIME} minutes
                        </Text>
                      </>
                    ) : (
                      <>
                        <img src={screenMonitorEmpty} alt="Screen recording" style={{ width: 66, height: 78 }} />
                        <Text style={{ marginTop: 16, width: 270, color: '#6C7191', fontSize: 12 }}>
                          No data available
                        </Text>
                      </>
                    )
                  ) : (
                    <>
                      <img
                        src={NeedPermission}
                        alt="Need permission"
                        style={{ width: 286, height: 168, marginLeft: 67 }}
                      />
                      <Text style={{ marginTop: 16, width: 440, color: '#6C7191', fontSize: 12 }}>
                        Enable screen recording permission, summary with AI every {SCREEN_INTERVAL_TIME} minutes
                      </Text>
                      <Button
                        type="primary"
                        size="large"
                        onClick={() => grantPermission()}
                        style={{ marginTop: 24, fontWeight: 500, background: '#000' }}>
                        Enable Permission
                      </Button>
                    </>
                  )}
                </div>
              </div>
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

        {/* 设置弹窗 */}
        <Modal
          title="Settings"
          visible={settingsVisible}
          autoFocus={false}
          focusLock
          onCancel={handleCancelSettings}
          className="text-[#AEAFC2]"
          unmountOnExit
          footer={
            <>
              <Button onClick={handleCancelSettings} style={{ fontSize: 12 }}>
                Cancel
              </Button>
              <Button type="primary" onClick={handleSave} style={{ background: '#000' }}>
                Save
              </Button>
            </>
          }>
          <Form layout="vertical" form={form}>
            <div className="flex w-full flex-1 mt-5">
              <div className="flex flex-col flex-1 pr-[24px]">
                <Form.Item label="Record Interval" style={{ fontSize: 12 }}>
                  <Slider
                    value={tempRecordInterval}
                    onChange={(value) => setTempRecordInterval(value as number)}
                    min={5}
                    max={300}
                    marks={{
                      5: '5s',
                      300: '5min'
                    }}
                    style={{ marginTop: 15 }}
                    formatTooltip={(value) => `${value}s`}
                  />
                </Form.Item>
                <Form.Item label="Choose what to record" shouldUpdate>
                  {(values) => {
                    const { screenSources = [], windowSources = [] } = values || {}
                    const screenList = screenAllSources?.filter((source) => screenSources.includes(source.id)) || []
                    const windowList = appAllSources?.filter((source) => windowSources.includes(source.id)) || []
                    return (
                      <Spin loading={sources.state === 'loading'} block>
                        <Application
                          value={[...screenList, ...windowList]}
                          onCancel={() => setApplicationVisible(false)}
                          visible={applicationVisible}
                          onOk={() => setApplicationVisible(true)}
                        />
                      </Spin>
                    )
                  }}
                </Form.Item>
                <Form.Item label="Enable recording hours" style={{ marginBottom: 0, fontSize: 12 }}>
                  <Switch
                    checked={tempEnableRecordingHours}
                    onChange={setTempEnableRecordingHours}
                    style={!tempEnableRecordingHours ? { background: '#e2e3ef' } : { background: '#000' }}
                  />
                </Form.Item>
                {tempEnableRecordingHours && (
                  <div style={{ marginTop: 12 }}>
                    <Form.Item label="Set recording hours" style={{ fontSize: 12 }}>
                      <TimePicker.RangePicker
                        format="HH:mm"
                        value={tempRecordingHours}
                        onChange={(value) => setTempRecordingHours(value as [string, string])}
                      />
                    </Form.Item>
                    <Form.Item label="Apply to days" style={{ fontSize: 12 }}>
                      <Radio.Group value={tempApplyToDays} onChange={setTempApplyToDays}>
                        <Radio value="weekday" className={styles.radio}>
                          Only weekday
                        </Radio>
                        <Radio value="everyday" className={styles.radio}>
                          Everyday
                        </Radio>
                      </Radio.Group>
                    </Form.Item>
                  </div>
                )}
              </div>
              <div
                className={clsx(
                  'flex flex-col flex-1 border-l border-[#efeff4] max-h-[360px] h-[360px] overflow-x-hidden overflow-y-auto px-[16px]  [&_.arco-checkbox-checked_.arco-checkbox-mask]:!bg-[#000000] [&_.arco-checkbox-checked_.arco-checkbox-mask]:!border-[#000000]',
                  { hidden: !applicationVisible }
                )}>
                <div className="text-[15px] leading-[18px] text-[#42464e] mb-[12px] font-medium">
                  Choose what to record
                </div>
                <div className="[&_.arco-checkbox]:!flex [&_.arco-checkbox]:!items-center">
                  <div className="text-[14px] leading-[20px] text-[#42464e] mb-[4px]">Screen</div>
                  <Form.Item field="screenSources">
                    <Checkbox.Group>
                      {screenAllSources.map((source) => (
                        <Checkbox key={source.id} value={source.id}>
                          <div className="flex items-center space-x-[4px]">
                            {source.appIcon ? (
                              <img
                                src={source.appIcon || ''}
                                alt=""
                                className="w-[14px] h-[14px] inline-block object-cover"
                              />
                            ) : (
                              <img src={screenIcon} alt="" className="w-[14px] h-[14px] inline-block object-cover" />
                            )}
                            <div className="text-[13px] leading-[22px] text-[#0b0b0f] !ml-[4px] line-clamp-1">
                              {source.name}
                            </div>
                          </div>
                        </Checkbox>
                      ))}
                    </Checkbox.Group>
                  </Form.Item>
                </div>
                <div className="[&_.arco-checkbox]:!flex [&_.arco-checkbox]:!items-center">
                  <div className="text-[14px] leading-[20px] text-[#42464e] mb-[4px]">Window</div>
                  <div className="text-[10px] leading-[12px] text-[#737a87] mb-[4px]">
                    Only opened applications can be selected
                  </div>
                  <Form.Item field="windowSources">
                    <Checkbox.Group className="flex flex-col space-y-4">
                      {appAllSources.map((source) => (
                        <Checkbox key={source.id} value={source.id}>
                          <div className="flex items-center space-x-[4px]">
                            <img
                              src={source.appIcon || source.thumbnail || ''}
                              alt=""
                              className="w-[14px] h-[14px] inline-block object-cover"
                            />
                            <div className="text-[13px] leading-[22px] text-[#0b0b0f] !ml-[4px] line-clamp-1">
                              {source.name}
                            </div>
                          </div>
                        </Checkbox>
                      ))}
                    </Checkbox.Group>
                  </Form.Item>
                </div>
              </div>
            </div>
          </Form>
        </Modal>
      </div>
    </div>
  )
}

export default ScreenMonitor

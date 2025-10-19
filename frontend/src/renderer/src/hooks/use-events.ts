// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { RootState, useAppDispatch } from '@renderer/store'
import { useSelector } from 'react-redux'
import GlobalEventService from '@renderer/services/GlobalEventService'
import { PushDataTypes } from '@renderer/constant/feed'
import { removeExistEvent, setActiveEvent, setIsModalVisible } from '@renderer/store/events'

export interface FeedEvent {
  id: string
  type: PushDataTypes.TIP_GENERATED | PushDataTypes.DAILY_SUMMARY_GENERATED | PushDataTypes.WEEKLY_SUMMARY_GENERATED
  data: Record<string, unknown>
  timestamp: number
}

export function useEvents() {
  // 存储轮询定时器ID
  // 可选：存储获取到的事件数据
  const events = useSelector((state: RootState) => state.events.events)
  const activeEvent = useSelector((state: RootState) => state.events.activeEvent)
  const currentModalVisible = useSelector((state: RootState) => state.events.isModalVisible)
  // 事件分发
  const feedEvents =
    (events.filter(
      (event) =>
        event.type === PushDataTypes.TIP_GENERATED ||
        event.type === PushDataTypes.DAILY_SUMMARY_GENERATED ||
        event.type === PushDataTypes.WEEKLY_SUMMARY_GENERATED
    ) as FeedEvent[]) || ([] as FeedEvent[])
  const activityEvents = events.filter((event) => event.type === PushDataTypes.ACTIVITY_GENERATED) || []

  const eventService = GlobalEventService.getInstance()
  const dispatch = useAppDispatch()

  const removeEvent = (id: string) => dispatch(removeExistEvent(id))

  const setCurrentActiveEvent = (id: string) => dispatch(setActiveEvent(id))

  const setCurrentModalVisible = (visible: boolean) => dispatch(setIsModalVisible(visible))

  // 导出函数和状态供组件使用
  return {
    events,
    feedEvents,
    activityEvents,
    activeEvent,
    currentModalVisible,
    // 可以手动控制轮询的函数
    removeEvent,
    fetchEvents: () => eventService.fetchEvents(dispatch),
    startPolling: () => eventService.startPolling(dispatch),
    stopPolling: () => eventService.stopPolling(),
    setCurrentActiveEvent,
    setCurrentModalVisible
  }
}

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from '@renderer/services/axiosConfig'
import { NotificationQueue } from '@renderer/utils/queue/NotificationQueue'
import { Notification } from '@renderer/types/notification'
import { addEvent } from '@renderer/store/events'
import { removeMarkdownSymbols } from '@renderer/utils/time'
import { PushDataTypes } from '@renderer/constant/feed'

// Define polling intervals (in milliseconds)
const NORMAL_POLLING_INTERVAL = 30 * 1000 // Normal: 30 seconds
const LOCKED_POLLING_INTERVAL = 300 * 1000 // Locked: 5 minutes

class GlobalEventService {
  private static instance: GlobalEventService
  private pollingTimer: NodeJS.Timeout | null = null
  private notificationQueue: NotificationQueue
  private isLocked = false
  private currentDispatch: any = null

  private constructor() {
    this.notificationQueue = NotificationQueue.getInstance()
  }

  public static getInstance(): GlobalEventService {
    if (!GlobalEventService.instance) {
      GlobalEventService.instance = new GlobalEventService()
    }
    return GlobalEventService.instance
  }

  // Set the screen lock state
  public setLocked(locked: boolean): void {
    if (this.isLocked === locked) return

    this.isLocked = locked
    console.log(`GlobalEventService: Screen ${locked ? 'locked' : 'unlocked'}, adjusting polling interval`)

    // Restart polling to apply the new interval
    if (this.pollingTimer && this.currentDispatch) {
      this.stopPolling()
      this.startPolling(this.currentDispatch)
    }
  }

  // Start polling
  public startPolling(dispatch): void {
    if (this.pollingTimer) {
      this.stopPolling()
    }

    this.currentDispatch = dispatch
    const interval = this.isLocked ? LOCKED_POLLING_INTERVAL : NORMAL_POLLING_INTERVAL

    // Execute immediately
    this.fetchEvents(dispatch)

    // Set polling timer
    this.pollingTimer = setInterval(() => {
      this.fetchEvents(dispatch)
    }, interval)

    console.log('Global event polling started, interval:', interval, 'ms')
  }

  // Stop polling
  public stopPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer)
      this.pollingTimer = null
      console.log('Global event polling stopped')
    }
  }

  // Fetch and process events
  public async fetchEvents(dispatch): Promise<void> {
    try {
      const res = await axiosInstance.get('/api/events/fetch')
      if (res.status === 200 && res.data && res.data.data.events) {
        // Store events in Redux
        dispatch(addEvent(res.data.data.events))

        // Convert each event to a notification and add it to the queue
        this.processEventsToNotifications(res.data.data.events)
      }
    } catch (error) {
      console.error('Error fetching global events:', error)
    }
  }

  // Convert events to notifications
  private processEventsToNotifications(events: any[]): void {
    if (!events || !Array.isArray(events)) {
      return
    }

    events.forEach((event) => {
      if (event.type === PushDataTypes.ACTIVITY_GENERATED) {
        return
      }
      // Create a corresponding notification based on the event type
      const notification: Notification = {
        id: `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: this.mapEventTypeToNotificationType(event.type),
        title: this.getEventTitle(event),
        message: removeMarkdownSymbols(event.data.title || '有新的事件通知'),
        timestamp: Date.now(),
        source: 'assistant', // Can be set based on the event source
        channel: 'in-app',
        meta: event // Save the original event data
      }

      // Add the notification to the queue
      this.notificationQueue.add(notification)
    })
  }

  // Map event type to notification type
  private mapEventTypeToNotificationType(eventType: string): Notification['type'] {
    const typeMap: Record<string, Notification['type']> = {
      tip: 'info',
      todo: 'action',
      activity: 'info',
      daily_summary: 'info',
      weekly_summary: 'info',
      system_status: 'warning'
    }
    return typeMap[eventType] || 'info'
  }

  // Get event title
  private getEventTitle(event: any): string {
    const titleMap: Record<string, string> = {
      tip: '提示信息',
      todo: '待办事项',
      activity: '活动通知',
      daily_summary: '每日总结',
      weekly_summary: '每周总结',
      system_status: '系统状态'
    }
    return titleMap[event.type] || '新通知'
  }
}

export default GlobalEventService

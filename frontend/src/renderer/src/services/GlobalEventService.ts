// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from '@renderer/services/axiosConfig'
import { NotificationQueue } from '@renderer/utils/queue/NotificationQueue'
import { Notification } from '@renderer/types/notification'
import { addEvent } from '@renderer/store/events'
import { removeMarkdownSymbols } from '@renderer/utils/time'
import { PushDataTypes } from '@renderer/constant/feed'

// 定义轮询间隔（毫秒）
const DEFAULT_POLLING_INTERVAL = 30 * 1000

class GlobalEventService {
  private static instance: GlobalEventService
  private pollingTimer: NodeJS.Timeout | null = null
  private notificationQueue: NotificationQueue

  private constructor() {
    this.notificationQueue = NotificationQueue.getInstance()
  }

  public static getInstance(): GlobalEventService {
    if (!GlobalEventService.instance) {
      GlobalEventService.instance = new GlobalEventService()
    }
    return GlobalEventService.instance
  }

  // 启动轮询
  public startPolling(dispatch): void {
    if (this.pollingTimer) {
      this.stopPolling()
    }

    // 立即执行一次
    this.fetchEvents(dispatch)

    // 设置轮询定时器
    this.pollingTimer = setInterval(() => {
      this.fetchEvents(dispatch)
    }, DEFAULT_POLLING_INTERVAL)

    console.log('全局事件轮询已启动，间隔：', DEFAULT_POLLING_INTERVAL, 'ms')
  }

  // 停止轮询
  public stopPolling(): void {
    if (this.pollingTimer) {
      clearInterval(this.pollingTimer)
      this.pollingTimer = null
      console.log('全局事件轮询已停止')
    }
  }

  // 获取事件并处理
  public async fetchEvents(dispatch): Promise<void> {
    try {
      const res = await axiosInstance.get('/api/events/fetch')
      if (res.status === 200 && res.data && res.data.data.events) {
        // 存储事件到Redux
        dispatch(addEvent(res.data.data.events))

        // 将每个事件转换为通知并加入队列
        this.processEventsToNotifications(res.data.data.events)
      }
    } catch (error) {
      console.error('获取全局事件时发生错误:', error)
    }
  }

  // 将事件转换为通知
  private processEventsToNotifications(events: any[]): void {
    if (!events || !Array.isArray(events)) {
      return
    }

    events.forEach((event) => {
      if (event.type === PushDataTypes.ACTIVITY_GENERATED) {
        return
      }
      // 根据事件类型创建对应的通知
      const notification: Notification = {
        id: `event-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: this.mapEventTypeToNotificationType(event.type),
        title: this.getEventTitle(event),
        message: removeMarkdownSymbols(event.data.title || '有新的事件通知'),
        timestamp: Date.now(),
        source: 'assistant', // 可以根据事件来源设置
        channel: 'in-app',
        meta: event // 保存原始事件数据
      }

      // 将通知加入队列
      this.notificationQueue.add(notification)
    })
  }

  // 映射事件类型到通知类型
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

  // 获取事件标题
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

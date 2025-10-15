// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { NotificationQueue } from '@renderer/utils/queue/NotificationQueue'
import { Notification as NotificationType } from '@renderer/types/notification'
import { isFocused } from '@renderer/utils/window'
import { Notification, NotificationHookReturnType } from '@arco-design/web-react'
import React, { createContext, use, useEffect, useMemo } from 'react'

type NotificationContextType = {
  open: NotificationHookReturnType
  destroy: typeof Notification.clear
}

const typeMap: Record<string, 'info' | 'success' | 'warning' | 'error' | 'normal'> = {
  error: 'error',
  success: 'success',
  warning: 'warning',
  info: 'info',
  normal: 'normal',
  progress: 'info',
  action: 'info'
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined)

export const NotificationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [api, contextHolder] = Notification.useNotification({
    maxCount: 3
  })

  useEffect(() => {
    const queue = NotificationQueue.getInstance()
    const listener = async (notification: NotificationType) => {
      // Determine if a system notification is needed
      if (notification.channel === 'system' || !isFocused()) {
        window.api.notification.send(notification)
        return
      }
      return new Promise<void>((resolve) => {
        const notificationMethod = api[typeMap[notification.type] || 'info'] as any
        notificationMethod({
          title: notification.title,
          content: notification.message.length > 50 ? notification.message.slice(0, 47) + '...' : notification.message,
          duration: 30000,
          requiredConfirm: true,
          requireInteraction: true,
          position: 'topRight',
          id: notification.id,
          onClose: resolve
        })
      })
    }
    queue.subscribe(listener)
    return () => queue.unsubscribe(listener)
  }, [api])

  const value = useMemo(
    () => ({
      open: api,
      destroy: Notification.clear
    }),
    [api]
  )

  return (
    <NotificationContext value={value}>
      {contextHolder}
      {children}
    </NotificationContext>
  )
}

export const useNotification = () => {
  const ctx = use(NotificationContext)
  if (!ctx) throw new Error('useNotification must be used within a NotificationProvider')
  return ctx
}

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export type NotificationType = 'progress' | 'success' | 'error' | 'warning' | 'info' | 'action' | 'normal'
export type NotificationSource = 'assistant' | 'backup' | 'knowledge' | 'update'

export interface Notification<T = any> {
  /** Unique identifier for the notification */
  id: string
  /** Notification category */
  type: NotificationType
  /** Brief title, used as the main text in lists or pop-ups */
  title: string
  /** Detailed description, can include execution context, result summary, etc. */
  message: string
  /** Timestamp, for sorting and deduplication */
  timestamp: number
  /** Optional progress value (0-1), for feedback on long tasks */
  progress?: number
  /** Additional metadata, T can be customized with various business fields */
  meta?: T
  /** Click or action callback identifier, the frontend can trigger routing or functions based on this field */
  actionKey?: string
  /** Sound/sound switch identifier, determines whether to play based on user preferences */
  silent?: boolean
  /** Channel: system-level (OS notification) | in-app (UI notification) */
  channel?: 'system' | 'in-app'
  /** Click callback function, only valid when type is 'action' */
  onClick?: () => void
  /** Notification source */
  source: NotificationSource
}

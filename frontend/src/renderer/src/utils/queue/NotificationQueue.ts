// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import type { Notification } from '@renderer/types/notification'
import PQueue from 'p-queue'

type NotificationListener = (notification: Notification) => Promise<void> | void

export class NotificationQueue {
  private static instance: NotificationQueue
  private queue = new PQueue({ concurrency: 1 })
  private listeners: NotificationListener[] = []

  // eslint-disable-next-line @typescript-eslint/no-empty-function
  private constructor() {}

  public static getInstance(): NotificationQueue {
    if (!NotificationQueue.instance) {
      NotificationQueue.instance = new NotificationQueue()
    }
    return NotificationQueue.instance
  }

  public subscribe(listener: NotificationListener) {
    this.listeners.push(listener)
  }

  public unsubscribe(listener: NotificationListener) {
    this.listeners = this.listeners.filter((l) => l !== listener)
  }

  public async add(notification: Notification): Promise<void> {
    await this.queue.add(() => Promise.all(this.listeners.map((listener) => listener(notification))))
  }

  /**
   * Clear the notification queue
   */
  public clear(): void {
    this.queue.clear()
  }

  /**
   * Get the number of pending tasks in the queue
   */
  public get pending(): number {
    return this.queue.pending
  }

  /**
   * Get the size of the queue (including running and pending tasks)
   */
  public get size(): number {
    return this.queue.size
  }
}

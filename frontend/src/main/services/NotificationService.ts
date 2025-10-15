// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { BrowserWindow, Notification as ElectronNotificationApp } from 'electron'
import { Notification } from 'src/renderer/src/types/notification'

class NotificationService {
  private window: BrowserWindow

  constructor(window: BrowserWindow) {
    this.window = window
  }

  async sendNotification(notification: Notification) {
    const electronNotification = new ElectronNotificationApp({
      title: notification.title,
      body: notification.message
    })

    electronNotification.on('click', () => {
      this.window.show()
      this.window.webContents.send(IpcServerPushChannel.NotificationClick, notification)
    })

    electronNotification.show()
  }
}

export { NotificationService }

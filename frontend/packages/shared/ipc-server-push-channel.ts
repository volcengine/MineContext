// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export enum IpcServerPushChannel {
  PushGetInitCheckData = 'push:get-init-check-data',
  PushPowerMonitor = 'push:power-monitor',
  PushScreenMonitorStatus = 'push:screen-monitor-status',
  NotificationClick = 'push:IpcServerPushChannel.NotificationClick',
  Tray_ToggleRecording = 'push:tray-toggle-recording',
  Tray_NavigateToScreenMonitor = 'push:tray-navigate-to-screen-monitor',
  Home_PushLatestActivity = 'push:latest-activity'
}

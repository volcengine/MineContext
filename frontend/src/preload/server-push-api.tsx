// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { ipcRenderer } from 'electron'
import { getLogger } from '@shared/logger/main'
const logger = getLogger('ServerPushAPI')

export const serverPushAPI = {
  getInitCheckData: (callback: (data: any) => void) => {
    ipcRenderer.on(IpcServerPushChannel.PushGetInitCheckData, (_, data) => callback(data))
  },
  powerMonitor: (callback: (data: any) => void) => {
    try {
      ipcRenderer.on(IpcServerPushChannel.PushPowerMonitor, (_, data) => {
        callback(data)
      })
    } catch (error) {
      logger.error('Error setting up powerMonitor event listener', error)
    }
  },
  pushScreenMonitorStatus: (callback: (data: any) => void): any => {
    try {
      const wrapper = (_: unknown, data: unknown) => callback(data as any)
      ipcRenderer.on(IpcServerPushChannel.PushScreenMonitorStatus, wrapper)
      return () => {
        ipcRenderer.off(IpcServerPushChannel.PushScreenMonitorStatus, wrapper)
      }
    } catch (error) {
      logger.error('Error setting up screenMonitorStatus event listener', error)
    }
  },
  pushHomeLatestActivity: (callback: (data: any) => void): any => {
    try {
      const wrapper = (_: unknown, data: unknown) => callback(data as any)
      ipcRenderer.on(IpcServerPushChannel.Home_PushLatestActivity, wrapper)
      return () => {
        ipcRenderer.off(IpcServerPushChannel.Home_PushLatestActivity, wrapper)
      }
    } catch (error) {
      logger.error('Error setting up homeLatestActivity event listener', error)
    }
  }
}

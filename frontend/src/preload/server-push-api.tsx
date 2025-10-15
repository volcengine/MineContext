// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'
import { ipcRenderer } from 'electron'

export const serverPushAPI = {
  getInitCheckData: (callback: (data: any) => void) => {
    ipcRenderer.on(IpcServerPushChannel.PushGetInitCheckData, (_, data) => callback(data))
  },
  powerMonitor: (callback: (data: any) => void) => {
    ipcRenderer.on(IpcServerPushChannel.PushPowerMonitor, (_, data) => {
      callback(data)
    })
  }
}

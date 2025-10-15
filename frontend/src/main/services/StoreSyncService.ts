// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { BrowserWindow, ipcMain } from 'electron'
import { IpcChannel } from '@shared/IpcChannel'
import type { StoreSyncAction } from '@types'

function isFSA(a: any): a is { type: string; [k: string]: any } {
  return a && typeof a === 'object' && typeof a.type === 'string'
}

export class StoreSyncService {
  private static instance: StoreSyncService | null = null
  static getInstance() {
    if (!this.instance) this.instance = new StoreSyncService()
    return this.instance
  }

  private windowIds = new Set<number>()
  private isIpcHandlerRegistered = false

  private constructor() {}

  public registerIpcHandler(): void {
    if (this.isIpcHandlerRegistered) return

    // Prevent duplicate registration during dev hot-reloading
    ipcMain.removeHandler(IpcChannel.StoreSync_Subscribe)
    ipcMain.removeHandler(IpcChannel.StoreSync_Unsubscribe)
    ipcMain.removeHandler(IpcChannel.StoreSync_OnUpdate)

    ipcMain.handle(IpcChannel.StoreSync_Subscribe, (event) => {
      const win = BrowserWindow.fromWebContents(event.sender)
      if (win) this.subscribe(win.id, win)
    })

    ipcMain.handle(IpcChannel.StoreSync_Unsubscribe, (event) => {
      const win = BrowserWindow.fromWebContents(event.sender)
      if (win) this.unsubscribe(win.id)
    })

    ipcMain.handle(IpcChannel.StoreSync_OnUpdate, (event, action: StoreSyncAction) => {
      const win = BrowserWindow.fromWebContents(event.sender)
      const sourceWindowId = win?.id
      if (!sourceWindowId) return

      // Only allow subscribed windows as sources
      if (!this.windowIds.has(sourceWindowId)) return

      // Minimal validation to prevent crashes from abnormal actions
      if (!isFSA(action)) return

      this.broadcastToOtherWindows(sourceWindowId, action)
    })

    this.isIpcHandlerRegistered = true
  }

  public subscribe(windowId: number, win?: BrowserWindow): void {
    if (!this.windowIds.has(windowId)) {
      this.windowIds.add(windowId)

      // Automatic cleanup: remove subscription when the window is closed
      const target = win ?? BrowserWindow.fromId(windowId)
      target?.once('closed', () => this.windowIds.delete(windowId))
    }
  }

  public unsubscribe(windowId: number): void {
    this.windowIds.delete(windowId)
  }

  /** Main process actively broadcasts to all windows (without the fromSync flag for the source window logic, uniformly use -1) */
  public syncToRenderer(typeOrAction: string | StoreSyncAction, payload?: any): void {
    const action: StoreSyncAction =
      typeof typeOrAction === 'string' ? { type: typeOrAction, payload } : (typeOrAction as StoreSyncAction)

    this.broadcastToOtherWindows(-1, action)
  }

  private broadcastToOtherWindows(sourceWindowId: number, action: StoreSyncAction): void {
    const syncAction: StoreSyncAction = {
      ...action,
      meta: {
        ...(action.meta || {}),
        fromSync: true,
        source: `windowId:${sourceWindowId}`
      }
    }

    // Copy the list of IDs to avoid modifying the Set during iteration
    const ids = Array.from(this.windowIds)
    for (const windowId of ids) {
      if (windowId === sourceWindowId) continue

      const targetWindow = BrowserWindow.fromId(windowId)
      if (targetWindow && !targetWindow.isDestroyed()) {
        targetWindow.webContents.send(IpcChannel.StoreSync_BroadcastSync, syncAction)
      } else {
        // Clean up invalid IDs
        this.windowIds.delete(windowId)
      }
    }
  }
}

export default StoreSyncService.getInstance()

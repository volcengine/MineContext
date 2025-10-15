// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import type { Middleware, Store, UnknownAction } from '@reduxjs/toolkit'
import { IpcChannel } from '@shared/IpcChannel'
import type { StoreSyncAction } from '@types'

import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('StoreSyncService')

export type SyncOptions = {
  /** Whitelist of action type prefixes to sync, e.g., ['user/', 'settings/'] */
  syncList: string[]
  /** Optional: Finer-grained filtering logic (returns true to participate in sync) */
  shouldSync?: (action: UnknownAction) => boolean
}

function isFSA(action: any): action is { type: string; [k: string]: any } {
  return action && typeof action === 'object' && typeof action.type === 'string'
}

export class StoreSyncService {
  private static instance: StoreSyncService | null = null
  static getInstance() {
    if (!this.instance) this.instance = new StoreSyncService()
    return this.instance
  }

  private store: Store | null = null
  private options: SyncOptions = { syncList: [] }
  private broadcastSyncRemover: (() => void) | null = null
  private initialized = false

  private constructor() {}

  /**
   * Unified initialization entry point: injects store + options, and automatically completes subscription
   */
  init(store: Store, options?: Partial<SyncOptions>) {
    if (this.initialized) {
      logger.warn('StoreSyncService already initialized; ignoring subsequent init.')
      return
    }

    this.store = store
    this.options = { ...this.options, ...(options || {}) }

    this.subscribe() // Automatic subscription

    // Automatic cleanup
    window.addEventListener('beforeunload', () => this.unsubscribe())
    this.initialized = true
  }

  /** Redux middleware: intercepts and broadcasts whitelisted local actions */
  createMiddleware(): Middleware {
    return () => (next) => (action) => {
      const result = next(action)

      if (!isFSA(action)) return result

      const isFromSync = Boolean((action as StoreSyncAction)?.meta?.fromSync)
      const inWhitelist = this.shouldSyncAction(action.type)
      const passCustom = this.options.shouldSync ? this.options.shouldSync(action) : true

      if (!isFromSync && inWhitelist && passCustom) {
        try {
          // Notify the main process to broadcast to other windows via the preload API
          window.api?.storeSync?.onUpdate(action as StoreSyncAction)
        } catch (e) {
          logger.error('storeSync.onUpdate failed:', e as Error)
        }
      }

      return result
    }
  }

  /** Whitelist matching (prefix) */
  private shouldSyncAction(actionType: string): boolean {
    const { syncList } = this.options
    if (!Array.isArray(syncList) || syncList.length === 0) return false
    return syncList.some((prefix) => actionType.startsWith(prefix))
  }

  /** Subscribe to main process broadcasts (private) */
  private subscribe() {
    if (this.broadcastSyncRemover) return
    if (!window.api?.storeSync) {
      logger.warn('window.api.storeSync is unavailable; sync disabled.')
      return
    }

    // Listen for action broadcasts from the main process
    this.broadcastSyncRemover = window.electron.ipcRenderer.on(
      IpcChannel.StoreSync_BroadcastSync,
      (_evt, action: StoreSyncAction) => {
        try {
          if (!this.store) return
          // Mark fromSync to prevent loops
          const synced: StoreSyncAction = {
            ...action,
            meta: { ...(action.meta || {}), fromSync: true }
          }
          this.store.dispatch(synced as unknown as UnknownAction)
        } catch (error) {
          logger.error('Error dispatching synced action:', error as Error)
        }
      }
    )

    // Start subscription (notify the main process to add this window to the broadcast list)
    try {
      window.api.storeSync.subscribe()
    } catch (e) {
      logger.error('storeSync.subscribe failed:', e as Error)
    }
  }

  /** Unsubscribe (private) */
  private unsubscribe() {
    try {
      window.api?.storeSync?.unsubscribe()
    } catch (e) {
      logger.error('storeSync.unsubscribe failed:', e as Error)
    }

    if (this.broadcastSyncRemover) {
      try {
        this.broadcastSyncRemover()
      } catch (e) {
        // Some preload wrappers may not be function removers, so swallow the error here
      } finally {
        this.broadcastSyncRemover = null
      }
    }
  }
}

export default StoreSyncService.getInstance()

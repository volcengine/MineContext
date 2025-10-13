// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { loggerService } from '@logger'
import type { Middleware, Store, UnknownAction } from '@reduxjs/toolkit'
import { IpcChannel } from '@shared/IpcChannel'
import type { StoreSyncAction } from '@types'

const logger = loggerService.withContext('StoreSyncService')

export type SyncOptions = {
  /** 需要同步的 action type 前缀白名单，如 ['user/', 'settings/'] */
  syncList: string[]
  /** 可选：更精细的过滤逻辑（返回 true 则参与同步）*/
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
   * 统一初始化入口：注入 store + options，并自动完成订阅
   */
  init(store: Store, options?: Partial<SyncOptions>) {
    if (this.initialized) {
      logger.warn('StoreSyncService already initialized; ignoring subsequent init.')
      return
    }

    this.store = store
    this.options = { ...this.options, ...(options || {}) }

    this.subscribe() // 自动订阅

    // 自动清理
    window.addEventListener('beforeunload', () => this.unsubscribe())
    this.initialized = true
  }

  /** Redux 中间件：拦截并广播白名单内的本地 action */
  createMiddleware(): Middleware {
    return () => (next) => (action) => {
      const result = next(action)

      if (!isFSA(action)) return result

      const isFromSync = Boolean((action as StoreSyncAction)?.meta?.fromSync)
      const inWhitelist = this.shouldSyncAction(action.type)
      const passCustom = this.options.shouldSync ? this.options.shouldSync(action) : true

      if (!isFromSync && inWhitelist && passCustom) {
        try {
          // 通过 preload API 通知主进程广播到其他窗口
          window.api?.storeSync?.onUpdate(action as StoreSyncAction)
        } catch (e) {
          logger.error('storeSync.onUpdate failed:', e as Error)
        }
      }

      return result
    }
  }

  /** 白名单匹配（前缀）*/
  private shouldSyncAction(actionType: string): boolean {
    const { syncList } = this.options
    if (!Array.isArray(syncList) || syncList.length === 0) return false
    return syncList.some((prefix) => actionType.startsWith(prefix))
  }

  /** 订阅主进程广播（私有） */
  private subscribe() {
    if (this.broadcastSyncRemover) return
    if (!window.api?.storeSync) {
      logger.warn('window.api.storeSync is unavailable; sync disabled.')
      return
    }

    // 监听来自主进程的 action 广播
    this.broadcastSyncRemover = window.electron.ipcRenderer.on(
      IpcChannel.StoreSync_BroadcastSync,
      (_evt, action: StoreSyncAction) => {
        try {
          if (!this.store) return
          // 标记 fromSync，防止回环
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

    // 启动订阅（通知主进程将本窗口加入广播列表）
    try {
      window.api.storeSync.subscribe()
    } catch (e) {
      logger.error('storeSync.subscribe failed:', e as Error)
    }
  }

  /** 反订阅（私有） */
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
        // 某些 preload 封装可能不是函数移除器，这里吞错
      } finally {
        this.broadcastSyncRemover = null
      }
    }
  }
}

export default StoreSyncService.getInstance()

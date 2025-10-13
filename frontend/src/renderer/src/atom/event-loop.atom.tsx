// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { ReactNode, useEffect, useRef } from 'react'
import { Provider, atom, useAtomValue, useSetAtom, createStore } from 'jotai'
import { useMemoizedFn } from 'ahooks'

// 创建一个独立的 store 用于事件系统
export const eventLoopStore = createStore()

// ---------------------------
// 1. 全局存储：key -> handlers[]
// ---------------------------
export const serviceDataAtom = atom<Record<string, ((payload: any) => void)[]>>({})

// ---------------------------
// 2. Provider：统一监听并分发
// ---------------------------
export const ServiceProvider = ({ children }: { children: ReactNode }) => {
  const handlers = useAtomValue(serviceDataAtom, { store: eventLoopStore })
  const handlersRef = useRef(handlers)

  useEffect(() => {
    handlersRef.current = handlers
  }, [handlers])

  const stableHandler = useMemoizedFn((raw: string) => {
    let parsed: { key: string; payload?: any } | null = null

    try {
      // 如果已经是对象，直接使用
      if (typeof raw === 'object' && raw !== null) {
        parsed = raw as { key: string; payload?: any }
      } else if (typeof raw === 'string') {
        // 尝试JSON解析
        parsed = JSON.parse(raw)
      }
    } catch {
      // 尝试简单分割
      if (typeof raw === 'string') {
        const [key, payload] = raw.split(':')
        parsed = { key, payload }
      }
    }

    if (!parsed?.key) {
      console.warn('[ServiceProvider] Invalid data received:', raw)
      return
    }

    const list = handlersRef.current[parsed.key] || []
    list.forEach((fn) => fn(parsed!.payload))
  })

  useEffect(() => {
    window.serverPushAPI.powerMonitor(stableHandler)
  }, [stableHandler])

  return <Provider store={eventLoopStore}>{children}</Provider>
}

// ---------------------------
// 3. Hook：组件内直接注册
// ---------------------------
export const useServiceHandler = (key: string, fn: (payload: any) => void) => {
  const setHandlers = useSetAtom(serviceDataAtom, { store: eventLoopStore })
  const stableFn = useMemoizedFn(fn)

  useEffect(() => {
    // 注册
    setHandlers((prev) => {
      const list = prev[key] || []
      return { ...prev, [key]: [...list, stableFn] }
    })
  }, [key, setHandlers, stableFn])
}

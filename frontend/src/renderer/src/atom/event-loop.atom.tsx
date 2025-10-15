// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { ReactNode, useEffect, useRef } from 'react'
import { Provider, atom, useAtomValue, useSetAtom, createStore } from 'jotai'
import { useMemoizedFn } from 'ahooks'

// Create an independent store for the event system
export const eventLoopStore = createStore()

// ---------------------------
// 1. Global storage: key -> handlers[]
// ---------------------------
export const serviceDataAtom = atom<Record<string, ((payload: any) => void)[]>>({})

// ---------------------------
// 2. Provider: Listen and dispatch uniformly
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
      // If it's already an object, use it directly
      if (typeof raw === 'object' && raw !== null) {
        parsed = raw as { key: string; payload?: any }
      } else if (typeof raw === 'string') {
        // Try JSON parsing
        parsed = JSON.parse(raw)
      }
    } catch {
      // Try simple splitting
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
// 3. Hook: Register directly within a component
// ---------------------------
export const useServiceHandler = (key: string, fn: (payload: any) => void) => {
  const setHandlers = useSetAtom(serviceDataAtom, { store: eventLoopStore })
  const stableFn = useMemoizedFn(fn)

  useEffect(() => {
    // Register
    setHandlers((prev) => {
      const list = prev[key] || []
      return { ...prev, [key]: [...list, stableFn] }
    })
  }, [key, setHandlers, stableFn])
}

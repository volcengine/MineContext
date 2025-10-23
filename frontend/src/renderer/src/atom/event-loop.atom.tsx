// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, PropsWithChildren, ReactNode, useEffect } from 'react'
import { useMemoizedFn, useUnmount } from 'ahooks'
import mitt from 'mitt'
import { POWER_MONITOR_KEY } from '@shared/constant/power-monitor'
type Events<T extends string> = {
  [key in T]: (data: any) => void
}

const emitter = mitt<Events<POWER_MONITOR_KEY>>()

export const ServiceProvider: FC<PropsWithChildren> = (props) => {
  const { children } = props

  const stableHandler = useMemoizedFn((raw: Record<string, any>) => {
    const { eventKey, data } = raw
    emitter.emit(eventKey as POWER_MONITOR_KEY, data)
  })

  useEffect(() => {
    window.serverPushAPI.powerMonitor(stableHandler)
  }, [stableHandler])

  return <>{children}</>
}

export const useServiceHandler = (eventKey: POWER_MONITOR_KEY, fn: (payload: any) => void) => {
  const stableFn = useMemoizedFn(fn)

  useEffect(() => {
    emitter.on(eventKey, stableFn)
  }, [eventKey, stableFn])

  useUnmount(() => {
    console.log('unmount', eventKey, stableFn)
    emitter.off(eventKey, stableFn)
  })
}
export interface ObservableTaskProps {
  active: (...params: any[]) => void
  inactive: (...params: any[]) => void
}
export const useObservableTask = (props: ObservableTaskProps) => {
  const { active, inactive } = props
  useServiceHandler(POWER_MONITOR_KEY.LockScreen, inactive)
  useServiceHandler(POWER_MONITOR_KEY.UnlockScreen, active)
  useServiceHandler(POWER_MONITOR_KEY.Suspend, inactive)
  useServiceHandler(POWER_MONITOR_KEY.Resume, active)
}

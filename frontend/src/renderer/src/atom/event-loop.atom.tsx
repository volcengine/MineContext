// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { FC, PropsWithChildren, useEffect } from 'react'
import { useMemoizedFn } from 'ahooks'
import mitt from 'mitt'
import { POWER_MONITOR_KEY } from '@shared/constant/power-monitor'
import { getLogger } from '@shared/logger/renderer'
const logger = getLogger('EventLoopAtom')
type Events<T extends string> = {
  [key in T]: (data: any) => void
}

const emitter = mitt<Events<POWER_MONITOR_KEY | `${POWER_MONITOR_KEY}:${string}`>>()

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

export const useServiceHandler = (eventKey: POWER_MONITOR_KEY, fn: (payload: any) => void, scope?: string) => {
  const stableFn = useMemoizedFn(fn)

  useEffect(() => {
    if (scope) {
      if (emitter.all.get(`${eventKey}:${scope}`)) {
        return
      } else {
        emitter.on(`${eventKey}:${scope}`, stableFn)
      }
    } else {
      emitter.on(eventKey, stableFn)
    }
    logger.info('register event handler', eventKey, !!emitter.all.get(eventKey))
    return () => {
      if (!scope) {
        emitter.off(eventKey, stableFn)
        logger.info('unregister event handler', eventKey, !!emitter.all.get(eventKey))
      } else {
        logger.info('unregister event handler', `${eventKey}:${scope}`, !!emitter.all.get(`${eventKey}:${scope}`))
      }
    }
  }, [eventKey, stableFn, scope])
}
export interface ObservableTaskProps {
  active: (...params: any[]) => void
  inactive: (...params: any[]) => void
}
export const useObservableTask = (props: ObservableTaskProps, scope?: string) => {
  const { active, inactive } = props
  useServiceHandler(POWER_MONITOR_KEY.LockScreen, inactive, scope)
  useServiceHandler(POWER_MONITOR_KEY.UnlockScreen, active, scope)
  useServiceHandler(POWER_MONITOR_KEY.Suspend, inactive, scope)
  useServiceHandler(POWER_MONITOR_KEY.Resume, active, scope)
}

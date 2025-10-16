// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { CaptureSource } from '@renderer/atom/capture.atom'
import { useMemoizedFn } from 'ahooks'
import { useRef } from 'react'
import dayjs from 'dayjs'
const VISIBILITY_CHECK_INTERVAL = 2000

const useCheckVisibleSources = () => {
  // Whether it is visible
  const lastVisibilityCheckRef = useRef(0)
  const cachedVisibleSourcesRef = useRef<Record<string, any>>(null)
  const checkVisibleSources = useMemoizedFn(async (sources: CaptureSource[]) => {
    const now = dayjs().valueOf()
    const timeSinceLastCheck = now - lastVisibilityCheckRef.current

    // Use cached visibility if recent enough
    if (cachedVisibleSourcesRef.current && timeSinceLastCheck < VISIBILITY_CHECK_INTERVAL) {
      return cachedVisibleSourcesRef.current
    }

    try {
      const sourceIds = sources.map((s) => s.id)
      const result = await window.screenMonitorAPI.getVisibleSources(sourceIds)
      const allVisibleResult = await window.screenMonitorAPI.getVisibleSources()
      if (result.success) {
        const visibleMap = {} as Record<string, any>
        ;(result.sources || []).forEach((s) => {
          visibleMap[s.id] = s.isVisible
        })

        // Store all visible sources for logging
        if (allVisibleResult.success) {
          visibleMap._allVisible = allVisibleResult.sources
        }

        cachedVisibleSourcesRef.current = visibleMap
        lastVisibilityCheckRef.current = now
        return visibleMap
      }
    } catch (error) {
      console.error('[ScreenshotMonitor] Error checking visibility:', error)
    }

    // If check fails, assume all are visible (fallback)
    const fallbackMap = {}
    sources.forEach((s) => {
      fallbackMap[s.id] = true
    })
    return fallbackMap
  })
  const clearCache = useMemoizedFn(() => {
    // Clear visibility cache
    cachedVisibleSourcesRef.current = null
    lastVisibilityCheckRef.current = 0
  })
  return {
    checkVisibleSources,
    clearCache
  }
}
export { useCheckVisibleSources }

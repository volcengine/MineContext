// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { formatName } from '@renderer/utils/format-mame'
import { atom, createStore, Provider } from 'jotai'
import { loadable } from 'jotai/utils'
import { get } from 'lodash'
import { FC, PropsWithChildren } from 'react'
export interface CaptureSource {
  id: string
  name: string
  type: 'screen' | 'window'
  thumbnail: string | null
  appIcon: string | null
  isVisible: boolean
  // Optional properties for windows added from the native module
  isVirtual?: boolean
  appName?: string
  windowTitle?: string
  windowId?: number
}

const fetchCaptureSources = async () => {
  if (!window.screenMonitorAPI || !window.screenMonitorAPI.getCaptureAllSources) {
    return { screenSources: [], appSources: [] }
  }

  const result = await window.screenMonitorAPI.getCaptureAllSources()

  if (!result.success) {
    throw new Error(result.error || 'Failed to load capture sources')
  }

  const { sources } = result
  const screenSources = (sources || []).filter((s) => s.type === 'screen')
  const appSources = (sources || []).filter((s) => s.type === 'window')

  return {
    screenSources: formatName(screenSources),
    appSources: formatName(appSources)
  }
}
const fetchCaptureSourcesFromSettings = async () => {
  const settings = await window.screenMonitorAPI.getSettings<{
    screenList: CaptureSource[]
    windowList: CaptureSource[]
  }>('settings')
  const screenList = get(settings, 'screenList', [])
  const windowList = get(settings, 'windowList', [])
  return {
    screenSources: formatName(screenList),
    appSources: formatName(windowList)
  }
}
// -----------------------
// 2. Define Jotai atoms
// -----------------------
export const captureSourcesAtom = atom(fetchCaptureSources())
export const captureSourcesFromSettingsAtom = atom(fetchCaptureSourcesFromSettings())
// Wrap with loadable to expose state
export const loadableCaptureSourcesAtom = loadable(captureSourcesAtom)
export const loadableCaptureSourcesFromSettingsAtom = loadable(captureSourcesFromSettingsAtom)
// Atom for refreshing data (write operation)
export const refreshCaptureSourcesAtom = atom(null, async (_get, set) => {
  set(captureSourcesAtom, fetchCaptureSources())
})
export const refreshCaptureSourcesFromSettingsAtom = atom(null, async (_get, set) => {
  set(captureSourcesFromSettingsAtom, fetchCaptureSourcesFromSettings())
})
// store.ts

export const appStore = createStore()

const CaptureSourcesProvider: FC<PropsWithChildren> = (props) => {
  const { children } = props
  return <Provider store={appStore}>{children}</Provider>
}
export { CaptureSourcesProvider }

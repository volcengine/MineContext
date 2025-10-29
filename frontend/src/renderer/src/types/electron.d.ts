// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { WindowApiType } from '../../../preload'
import { ElectronAPI } from '@electron-toolkit/preload'

interface ScreenMonitorAPI {
  checkPermissions: () => Promise<boolean>
  openPrefs: () => Promise<void>
  takeScreenshot: (
    groupIntervalTime: string,
    sourceId: string
  ) => Promise<{
    success: boolean
    screenshotInfo?: { url: string; date: string; timestamp: number }
    error?: string
  }>
  getVisibleSources: (ids?: string[]) => Promise<{ success: boolean; sources?: any[]; error?: string }>
  deleteScreenshot: (filePath: string) => Promise<{ success: boolean; error?: string }>
  readImageAsBase64: (filePath: string) => Promise<{
    success: boolean
    data?: string
    error?: string
  }>
  getScreenshotsByDate: (
    date?: string,
    recordInterval?: number
  ) => Promise<{
    success: boolean
    screenshots?: Array<{
      id: string
      date: string
      timestamp: number
      image_url: string
      description: string
      created_at: string
      group_id: string
    }>
    error?: string
  }>
  getCaptureAllSources: (thumbnailSize?: { width: number; height: number }) => Promise<{
    success: boolean
    sources?: any[]
    error?: string
  }>
  getSettings: <T>(key: string) => Promise<T>
  setSettings: (
    key: string,
    value: unknown
  ) => Promise<{
    success: boolean
    error?: string
  }>
  clearSettings: (key: string) => Promise<{
    success: boolean
    error?: string
  }>
  updateCurrentRecordApp: (appInfo: CaptureSource[]) => Promise<{
    success: boolean
    error?: string
  }>
  updateModelConfig: (config: Record<string, unknown>) => Promise<{
    success: boolean
    error?: string
  }>
  stopTask: () => Promise<{
    success: boolean
    error?: string
  }>
  startTask: () => Promise<{
    success: boolean
    error?: string
  }>
  checkCanRecord: () => Promise<{
    canRecord: boolean
    status: string
  }>
  getRecordingStats: () => Promise<{
    processed_screenshots: number
    failed_screenshots: number
    generated_activities: number
    next_activity_eta_seconds: number
    last_activity_time: string | null
    session_start_time: string
    recent_errors: Array<{
      error_message: string
      processor_name: string
      timestamp: string
    }>
    recent_screenshots: string[]
  } | null>
}

interface dbAPI {
  getVaultsByDocumentType: (documentType: VaultDocumentType | VaultDocumentType[]) => Promise<Vault[]>
  getVaultByTitle: (title: string) => Promise<Vault[]>
  getAllVaults: () => Promise<Vault[]>
  [propName: string]: (...args: any[]) => any
}

declare global {
  interface Window {
    electron: ElectronAPI
    api: WindowApiType
    dbAPI: dbAPI
    screenMonitorAPI: ScreenMonitorAPI
    fileService: any
    serverPushAPI: any
  }
}

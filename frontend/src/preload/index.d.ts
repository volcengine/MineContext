// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { ElectronAPI } from '@electron-toolkit/preload'

import type { WindowApiType } from './index'

declare global {
  interface Window {
    electron: ElectronAPI
    api: WindowApiType
    dbAPI: {
      getAllVaults: (type?: string) => Promise<any>
      getVaultsByParentId: (parentId: number | null) => Promise<any>
      getVaultById: (id: number) => Promise<any>
      getVaultByTitle: (title: string) => Promise<any>
      insertVault: (vault: any) => Promise<{ id: number }>
      updateVaultById: (id: number, vault: Partial<any>) => Promise<{ changes: number }>
      deleteVaultById: (id: number) => Promise<{ changes: number }>
      getFolders: () => Promise<any>
      softDeleteVaultById: (id: number) => Promise<{ changes: number }>
      restoreVaultById: (id: number) => Promise<{ changes: number }>
      hardDeleteVaultById: (id: number) => Promise<{ changes: number }>
      createFolder: (title: string, parentId?: number) => Promise<{ id: number }>
      getAllActivities: () => Promise<any[]>
      getNewActivities: (startTime: string, endTime?: string) => Promise<any[]>

      // tasks
      getTasks: (startTime: string, endTime?: string) => Promise<any>
      toggleTaskStatus: (id: number) => Promise<any>
      // tips
      getAllTips: () => Promise<any>
    }
    screenMonitorAPI: {
      getVisibleSources: () => Promise<any[]>
      deleteScreenshot: (filePath: string) => Promise<{ success: boolean; error?: string }>
      readImageAsBase64: (filePath: string) => Promise<{ success: boolean; data?: string; error?: string }>
    }
    fileService: {
      saveFile: (fileName: string, fileData: Uint8Array) => Promise<any>
      readFile: (filePath: string) => Promise<any>
      copyFile: (srcPath: string) => Promise<any>
      getFiles: () => Promise<any>
    }
  }
}

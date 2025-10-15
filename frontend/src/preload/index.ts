// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { contextBridge, ipcRenderer } from 'electron'
import { electronAPI } from '@electron-toolkit/preload'
import { IpcChannel } from '@shared/IpcChannel'
import type { LogLevel, LogSourceWithContext } from '@shared/config/logger'
import type { Vault } from 'src/renderer/src/types/vault'
import { Notification } from 'src/renderer/src/types/notification'
import { serverPushAPI } from './server-push-api'

// Custom APIs for renderer
const api = {
  logToMain: (source: LogSourceWithContext, level: LogLevel, message: string, data: any[]) =>
    ipcRenderer.invoke(IpcChannel.App_LogToMain, source, level, message, data),
  notification: {
    send: (notification: Notification) => ipcRenderer.invoke(IpcChannel.Notification_Send, notification)
  },
  storeSync: {
    subscribe: () => ipcRenderer.invoke(IpcChannel.StoreSync_Subscribe),
    unsubscribe: () => ipcRenderer.invoke(IpcChannel.StoreSync_Unsubscribe),
    onUpdate: (action: any) => ipcRenderer.invoke(IpcChannel.StoreSync_OnUpdate, action)
  },
  // Window event listeners
  onWindowShow: (callback) => {
    // @ts-ignore
    const wrappedCallback = (event, ...args) => callback(...args)
    ipcRenderer.on('window-show', wrappedCallback)
    return () => ipcRenderer.removeListener('window-show', wrappedCallback)
  },
  onAppActivate: (callback) => {
    // @ts-ignore
    const wrappedCallback = (event, ...args) => callback(...args)
    ipcRenderer.on('app-activate', wrappedCallback)
    return () => ipcRenderer.removeListener('app-activate', wrappedCallback)
  }
}

const dbAPI = {
  getAllActivities: () => ipcRenderer.invoke(IpcChannel.Database_GetAllActivities),
  getNewActivities: (startTime: string, endTime?: string) =>
    ipcRenderer.invoke(IpcChannel.Database_GetNewActivities, startTime, endTime),
  getAllVaults: (type?: string) => ipcRenderer.invoke(IpcChannel.Database_GetAllVaults, type),
  getVaultsByParentId: (parentId: number | null) =>
    ipcRenderer.invoke(IpcChannel.Database_GetVaultsByParentId, parentId),
  getVaultById: (id: number) => ipcRenderer.invoke(IpcChannel.Database_GetVaultById, id),
  getVaultByTitle: (title: string) => ipcRenderer.invoke(IpcChannel.Database_GetVaultByTitle, title),
  insertVault: (vault: Vault) => ipcRenderer.invoke(IpcChannel.Database_InsertVault, vault),
  updateVaultById: (id: number, vault: Partial<Vault>) =>
    ipcRenderer.invoke(IpcChannel.Database_UpdateVaultById, id, vault),
  deleteVaultById: (id: number) => ipcRenderer.invoke(IpcChannel.Database_DeleteVaultById, id),
  getFolders: () => ipcRenderer.invoke(IpcChannel.Database_GetFolders),
  softDeleteVaultById: (id: number) => ipcRenderer.invoke(IpcChannel.Database_SoftDeleteVaultById, id),
  restoreVaultById: (id: number) => ipcRenderer.invoke(IpcChannel.Database_RestoreVaultById, id),
  hardDeleteVaultById: (id: number) => ipcRenderer.invoke(IpcChannel.Database_HardDeleteVaultById, id),
  createFolder: (title: string, parentId?: number) =>
    ipcRenderer.invoke(IpcChannel.Database_CreateFolder, title, parentId),
  getLatestActivity: () => ipcRenderer.invoke(IpcChannel.Database_GetLatestActivity),

  // tasks
  getTasks: (startTime: string, endTime?: string) =>
    ipcRenderer.invoke(IpcChannel.Database_GetAllTasks, startTime, endTime),
  updateTask: (id: number, task: Partial<{ content: string; urgency: number; start_time: string; end_time: string }>) =>
    ipcRenderer.invoke(IpcChannel.Database_UpdateTask, id, task),
  deleteTask: (id: number) => ipcRenderer.invoke(IpcChannel.Database_DeleteTask, id),
  toggleTaskStatus: (id: number) => ipcRenderer.invoke(IpcChannel.Database_ToggleTaskStatus, id),
  addTask: (
    taskData: Partial<{ content?: string; status?: number; start_time?: string; end_time?: string; urgency?: number }>
  ) => ipcRenderer.invoke(IpcChannel.Database_AddTask, taskData), // 新增

  // tips
  getAllTips: () => ipcRenderer.invoke(IpcChannel.Database_GetAllTips)
}

const screenMonitorAPI = {
  checkPermissions: () => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Check_Permissions),
  openPrefs: () => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Open_Prefs),
  takeScreenshot: (groupIntervalTime: string, sourceId: string) =>
    ipcRenderer.invoke(IpcChannel.Screen_Monitor_Take_Screenshot, groupIntervalTime, sourceId),
  getVisibleSources: () => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Get_Visible_Sources),
  deleteScreenshot: (filePath: string) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Delete_Screenshot, filePath),
  readImageAsBase64: (filePath: string) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Read_Image_Base64, filePath),
  getScreenshotsByDate: (date?: string) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Get_Screenshots_By_Date, date),
  getCaptureAllSources: (thumbnailSize?: { width: number; height: number }) =>
    ipcRenderer.invoke(IpcChannel.Screen_Monitor_Get_Capture_All_Sources, thumbnailSize),
  getSettings: (key: string) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Get_Settings, key),
  setSettings: (key: string, value: unknown) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Set_Settings, key, value),
  clearSettings: (key: string) => ipcRenderer.invoke(IpcChannel.Screen_Monitor_Clear_Settings, key)
}

const fileService = {
  saveFile: (fileName: string, fileData: Uint8Array) => ipcRenderer.invoke(IpcChannel.File_Save, fileName, fileData),
  readFile: (filePath: string) => ipcRenderer.invoke(IpcChannel.File_Read, filePath),
  copyFile: (srcPath: string) => ipcRenderer.invoke(IpcChannel.File_Copy, srcPath),
  getFiles: () => ipcRenderer.invoke(IpcChannel.File_Get_All)
}

// Use `contextBridge` APIs to expose Electron APIs to
// renderer only if context isolation is enabled, otherwise
// just add to the DOM global.
if (process.contextIsolated) {
  try {
    contextBridge.exposeInMainWorld('electron', electronAPI)
    contextBridge.exposeInMainWorld('api', api)
    contextBridge.exposeInMainWorld('dbAPI', dbAPI)
    contextBridge.exposeInMainWorld('screenMonitorAPI', screenMonitorAPI)
    contextBridge.exposeInMainWorld('fileService', fileService)
    contextBridge.exposeInMainWorld('serverPushAPI', serverPushAPI)
  } catch (error) {
    console.error(error)
  }
} else {
  // @ts-ignore (define in dts)
  window.electron = electronAPI
  // @ts-ignore (define in dts)
  window.api = api
  // @ts-ignore (define in dts)
  window.dbAPI = dbAPI
  // @ts-ignore (define in dts)
  window.screenMonitorAPI = screenMonitorAPI
  // @ts-ignore (define in dts)
  window.fileService = fileService
  // @ts-ignore (define in dts)
  window.serverPushAPI = serverPushAPI
}

ipcRenderer.on('main-log', (_, ...args) => {
  console.log('[主进程日志]:', ...args)
})
export type WindowApiType = typeof api

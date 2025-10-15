// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import fs from 'node:fs'
import { arch } from 'node:os'
import path from 'node:path'

import { getLogger } from '@shared/logger/main'
import Logger from 'electron-log/main'
import { isLinux, isMac, isPortable, isWin } from '@main/constant'
import { MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH } from '@shared/config/constant'
import { IpcChannel } from '@shared/IpcChannel'
import { BrowserWindow, dialog, ipcMain, ProxyConfig, session, shell, systemPreferences } from 'electron'
import { Notification } from 'src/renderer/src/types/notification'

import appService from './services/AppService'
import { fileStorage as fileManager } from './services/FileStorage'
// import FileService from './services/FileSystemService'
import { NotificationService } from './services/NotificationService'
import { proxyManager } from './services/ProxyManager'
import storeSyncService from './services/StoreSyncService'
import db from './services/DatabaseService'
import { getBackendPort, getBackendStatus } from './backend'

// 确保数据库已初始化的辅助函数
async function ensureDbInitialized() {
  await db.initialize()
}
import screenshotService from './services/ScreenshotService'
import FileService from './services/FileService'
import { calculateDirectorySize, getResourcePath } from './utils'
import { getCacheDir, getConfigDir, getFilesDir, hasWritePermission, isPathInside, untildify } from './utils/file'
import { updateAppDataConfig } from './utils/init'
import { localStoreService } from './services/LocalStoreService'
import { activityService } from './services/ActivityService'
import { IpcServerPushChannel } from '@shared/ipc-server-push-channel'

const logger = getLogger('IPC')

export function registerIpc(mainWindow: BrowserWindow, app: Electron.App) {
  const notificationService = new NotificationService(mainWindow)

  // Backend 服务相关
  // ipcMain.handle(IpcChannel.Backend_GetPort, () => {
  //   return getBackendPort()
  // })

  // ipcMain.handle(IpcChannel.Backend_GetStatus, () => {
  //   return {
  //     status: getBackendStatus(),
  //     port: getBackendPort(),
  //     timestamp: new Date().toISOString()
  //   }
  // })

  ipcMain.handle(IpcChannel.App_Info, () => ({
    version: app.getVersion(),
    isPackaged: app.isPackaged,
    appPath: app.getAppPath(),
    filesPath: getFilesDir(),
    configPath: getConfigDir(),
    appDataPath: app.getPath('userData'),
    resourcesPath: getResourcePath(),
    logsPath: path.dirname(Logger.transports.file.getFile().path),
    arch: arch(),
    isPortable: isWin && 'PORTABLE_EXECUTABLE_DIR' in process.env,
    installPath: path.dirname(app.getPath('exe'))
  }))

  ipcMain.handle(IpcChannel.App_Proxy, async (_, proxy: string, bypassRules?: string) => {
    let proxyConfig: ProxyConfig

    if (proxy === 'system') {
      // system proxy will use the system filter by themselves
      proxyConfig = { mode: 'system' }
    } else if (proxy) {
      proxyConfig = { mode: 'fixed_servers', proxyRules: proxy, proxyBypassRules: bypassRules }
    } else {
      proxyConfig = { mode: 'direct' }
    }

    await proxyManager.configureProxy(proxyConfig)
  })

  ipcMain.handle(IpcChannel.App_Reload, () => mainWindow.reload())
  ipcMain.handle(IpcChannel.Open_Website, (_, url: string) => shell.openExternal(url))

  // launch on boot
  ipcMain.handle(IpcChannel.App_SetLaunchOnBoot, (_, isLaunchOnBoot: boolean) => {
    appService.setAppLaunchOnBoot(isLaunchOnBoot)
  })

  //only for mac
  if (isMac) {
    ipcMain.handle(IpcChannel.App_MacIsProcessTrusted, (): boolean => {
      return systemPreferences.isTrustedAccessibilityClient(false)
    })

    //return is only the current state, not the new state
    ipcMain.handle(IpcChannel.App_MacRequestProcessTrust, (): boolean => {
      return systemPreferences.isTrustedAccessibilityClient(true)
    })
  }

  // clear cache
  ipcMain.handle(IpcChannel.App_ClearCache, async () => {
    const sessions = [session.defaultSession, session.fromPartition('persist:webview')]

    try {
      await Promise.all(
        sessions.map(async (session) => {
          await session.clearCache()
          await session.clearStorageData({
            storages: ['cookies', 'filesystem', 'shadercache', 'websql', 'serviceworkers', 'cachestorage']
          })
        })
      )
      await fileManager.clearTemp()
      // do not clear logs for now
      // TODO clear logs
      // await fs.writeFileSync(log.transports.file.getFile().path, '')
      return { success: true }
    } catch (error: any) {
      logger.error('Failed to clear cache:', error)
      return { success: false, error: error.message }
    }
  })

  // get cache size
  ipcMain.handle(IpcChannel.App_GetCacheSize, async () => {
    const cachePath = getCacheDir()
    logger.info(`Calculating cache size for path: ${cachePath}`)

    try {
      const sizeInBytes = await calculateDirectorySize(cachePath)
      const sizeInMB = (sizeInBytes / (1024 * 1024)).toFixed(2)
      return `${sizeInMB}`
    } catch (error: any) {
      logger.error(`Failed to calculate cache size for ${cachePath}: ${error.message}`)
      return '0'
    }
  })

  let preventQuitListener: ((event: Electron.Event) => void) | null = null
  ipcMain.handle(IpcChannel.App_SetStopQuitApp, (_, stop: boolean = false, reason: string = '') => {
    if (stop) {
      // Only add listener if not already added
      if (!preventQuitListener) {
        preventQuitListener = (event: Electron.Event) => {
          event.preventDefault()
          notificationService.sendNotification({
            title: reason,
            message: reason
          } as Notification)
        }
        app.on('before-quit', preventQuitListener)
      }
    } else {
      // Remove listener if it exists
      if (preventQuitListener) {
        app.removeListener('before-quit', preventQuitListener)
        preventQuitListener = null
      }
    }
  })

  // Select app data path
  ipcMain.handle(IpcChannel.App_Select, async (_, options: Electron.OpenDialogOptions) => {
    try {
      const { canceled, filePaths } = await dialog.showOpenDialog(options)
      if (canceled || filePaths.length === 0) {
        return null
      }
      return filePaths[0]
    } catch (error: any) {
      logger.error('Failed to select app data path:', error)
      return null
    }
  })

  ipcMain.handle(IpcChannel.App_HasWritePermission, async (_, filePath: string) => {
    const hasPermission = await hasWritePermission(filePath)
    return hasPermission
  })

  ipcMain.handle(IpcChannel.App_ResolvePath, async (_, filePath: string) => {
    return path.resolve(untildify(filePath))
  })

  // Check if a path is inside another path (proper parent-child relationship)
  ipcMain.handle(IpcChannel.App_IsPathInside, async (_, childPath: string, parentPath: string) => {
    return isPathInside(childPath, parentPath)
  })

  // Set app data path
  ipcMain.handle(IpcChannel.App_SetAppDataPath, async (_, filePath: string) => {
    updateAppDataConfig(filePath)
    app.setPath('userData', filePath)
  })

  ipcMain.handle(IpcChannel.App_GetDataPathFromArgs, () => {
    return process.argv
      .slice(1)
      .find((arg) => arg.startsWith('--new-data-path='))
      ?.split('--new-data-path=')[1]
  })

  ipcMain.handle(IpcChannel.App_FlushAppData, () => {
    BrowserWindow.getAllWindows().forEach((w) => {
      w.webContents.session.flushStorageData()
      w.webContents.session.cookies.flushStore()

      w.webContents.session.closeAllConnections()
    })

    session.defaultSession.flushStorageData()
    session.defaultSession.cookies.flushStore()
    session.defaultSession.closeAllConnections()
  })

  ipcMain.handle(IpcChannel.App_IsNotEmptyDir, async (_, path: string) => {
    return fs.readdirSync(path).length > 0
  })

  // Copy user data to new location
  ipcMain.handle(IpcChannel.App_Copy, async (_, oldPath: string, newPath: string, occupiedDirs: string[] = []) => {
    try {
      await fs.promises.cp(oldPath, newPath, {
        recursive: true,
        filter: (src) => {
          if (occupiedDirs.some((dir) => src.startsWith(path.resolve(dir)))) {
            return false
          }
          return true
        }
      })
      return { success: true }
    } catch (error: any) {
      logger.error('Failed to copy user data:', error)
      return { success: false, error: error.message }
    }
  })

  // Relaunch app
  ipcMain.handle(IpcChannel.App_RelaunchApp, (_, options?: Electron.RelaunchOptions) => {
    // Fix for .AppImage
    if (isLinux && process.env.APPIMAGE) {
      logger.info(`Relaunching app with options: ${process.env.APPIMAGE}`, options)
      // On Linux, we need to use the APPIMAGE environment variable to relaunch
      // https://github.com/electron-userland/electron-builder/issues/1727#issuecomment-769896927
      options = options || {}
      options.execPath = process.env.APPIMAGE
      options.args = options.args || []
      options.args.unshift('--appimage-extract-and-run')
    }

    if (isWin && isPortable) {
      options = options || {}
      options.execPath = process.env.PORTABLE_EXECUTABLE_FILE
      options.args = options.args || []
    }

    app.relaunch(options)
    app.exit(0)
  })

  // notification
  ipcMain.handle(IpcChannel.Notification_Send, async (_, notification: Notification) => {
    await notificationService.sendNotification(notification)
  })
  ipcMain.handle(IpcChannel.Notification_OnClick, (_, notification: Notification) => {
    mainWindow.webContents.send(IpcServerPushChannel.NotificationClick, notification)
  })

  // system
  ipcMain.handle(IpcChannel.System_GetDeviceType, () => (isMac ? 'mac' : isWin ? 'windows' : 'linux'))
  ipcMain.handle(IpcChannel.System_GetHostname, () => require('os').hostname())
  ipcMain.handle(IpcChannel.System_ToggleDevTools, (e) => {
    const win = BrowserWindow.fromWebContents(e.sender)
    win && win.webContents.toggleDevTools()
  })

  // 新增 addTask 处理器
  ipcMain.handle(
    IpcChannel.Database_AddTask,
    async (
      _,
      taskData: Partial<{ content?: string; status?: number; start_time?: string; end_time?: string; urgency?: number }>
    ) => {
      await ensureDbInitialized()
      return db.addTask(taskData)
    }
  )

  // tips

  // file
  // ipcMain.handle(IpcChannel.File_Open, fileManager.open.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_OpenPath, fileManager.openPath.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Select, fileManager.selectFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Upload, fileManager.uploadFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Clear, fileManager.clear.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Delete, fileManager.deleteFile.bind(fileManager))
  // ipcMain.handle('file:deleteDir', fileManager.deleteDir.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Get, fileManager.getFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_SelectFolder, fileManager.selectFolder.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_CreateTempFile, fileManager.createTempFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Write, fileManager.writeFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_WriteWithId, fileManager.writeFileWithId.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_SaveImage, fileManager.saveImage.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Base64Image, fileManager.base64Image.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_SaveBase64Image, fileManager.saveBase64Image.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Base64File, fileManager.base64File.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Download, fileManager.downloadFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_Copy, fileManager.copyFile.bind(fileManager))
  // ipcMain.handle(IpcChannel.File_BinaryImage, fileManager.binaryImage.bind(fileManager))
  // ipcMain.handle(
  //   IpcChannel.File_OpenWithRelativePath,
  //   fileManager.openFileWithRelativePath.bind(fileManager)
  // )

  // fs
  // ipcMain.handle(IpcChannel.Fs_Read, FileService.readFile.bind(FileService))

  // open path
  ipcMain.handle(IpcChannel.Open_Path, async (_, path: string) => {
    await shell.openPath(path)
  })

  // window
  ipcMain.handle(IpcChannel.Windows_SetMinimumSize, (_, width: number, height: number) => {
    mainWindow?.setMinimumSize(width, height)
  })

  ipcMain.handle(IpcChannel.Windows_ResetMinimumSize, () => {
    mainWindow?.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
    const [width, height] = mainWindow?.getSize() ?? [MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT]
    if (width < MIN_WINDOW_WIDTH) {
      mainWindow?.setSize(MIN_WINDOW_WIDTH, height)
    }
  })

  ipcMain.handle(IpcChannel.Windows_GetSize, () => {
    const [width, height] = mainWindow?.getSize() ?? [MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT]
    return [width, height]
  })

  // store sync
  storeSyncService.registerIpcHandler()

  // Database (better-sqlite3 同步操作)
  // 数据库相关的IPC处理器
  ipcMain.handle(IpcChannel.Database_GetAllVaults, async (_, type: string = 'vaults') => {
    await ensureDbInitialized()
    return db.getVaults(type)
  })

  ipcMain.handle(IpcChannel.Database_GetVaultsByParentId, async (_, parentId: number) => {
    await ensureDbInitialized()
    return db.getVaultsByParentId(parentId)
  })

  ipcMain.handle(IpcChannel.Database_GetVaultById, async (_, id: number) => {
    await ensureDbInitialized()
    return db.getVaultById(id)
  })

  ipcMain.handle(IpcChannel.Database_GetVaultByTitle, async (_, title: string) => {
    await ensureDbInitialized()
    return db.getVaultByTitle(title)
  })

  ipcMain.handle(IpcChannel.Database_InsertVault, async (_, vault) => {
    await ensureDbInitialized()
    return db.insertVault(vault)
  })

  ipcMain.handle(IpcChannel.Database_UpdateVaultById, async (_, id: number, vault) => {
    await ensureDbInitialized()
    const result = db.updateVaultById(id, vault)
    return result.changes > 0
  })

  ipcMain.handle(IpcChannel.Database_DeleteVaultById, async (_, id: number) => {
    await ensureDbInitialized()
    const result = db.deleteVaultById(id)
    return result.changes > 0
  })

  ipcMain.handle(IpcChannel.Database_GetFolders, async () => {
    await ensureDbInitialized()
    return db.getFolders()
  })

  ipcMain.handle(IpcChannel.Database_CreateFolder, async (_, title: string, parentId?: number) => {
    await ensureDbInitialized()
    return db.createFolder(title, parentId)
  })

  ipcMain.handle(IpcChannel.Database_SoftDeleteVaultById, async (_, id: number) => {
    await ensureDbInitialized()
    return db.softDeleteVaultById(id)
  })

  ipcMain.handle(IpcChannel.Database_HardDeleteVaultById, async (_, id: number) => {
    await ensureDbInitialized()
    return db.hardDeleteVaultById(id)
  })

  ipcMain.handle(IpcChannel.Database_RestoreVaultById, async (_, id: number) => {
    await ensureDbInitialized()
    return db.restoreVaultById(id)
  })

  // activity
  ipcMain.handle(IpcChannel.Database_GetAllActivities, async () => {
    await ensureDbInitialized()
    return db.getAllActivities()
  })
  ipcMain.handle(IpcChannel.Database_GetLatestActivity, async () => {
    console.log('IPC handler "database:get-latest-activity" received arguments:')
    return activityService.getLatestActivity()
  })

  ipcMain.handle(
    IpcChannel.Database_GetNewActivities,
    async (_, startTime: string, endTime: string = '2099-12-31 00:00:00') => {
      await ensureDbInitialized()
      return db.getNewActivities(startTime, endTime)
    }
  )

  // tasks
  ipcMain.handle(
    IpcChannel.Database_GetAllTasks,
    async (_, startTime: string, endTime: string = '2099-12-31 00:00:00') => {
      await ensureDbInitialized()
      return db.getTasks(startTime, endTime)
    }
  )

  ipcMain.handle(
    IpcChannel.Database_UpdateTask,
    async (
      _,
      id: number,
      taskData: Partial<{ content: string; urgency: number; start_time: string; end_time: string }>
    ) => {
      await ensureDbInitialized()
      return db.updateTask(id, taskData)
    }
  )

  ipcMain.handle(IpcChannel.Database_DeleteTask, async (_, id: number) => {
    await ensureDbInitialized()
    return db.deleteTask(id)
  })

  ipcMain.handle(IpcChannel.Database_ToggleTaskStatus, async (_, id: number) => {
    await ensureDbInitialized()
    return db.toggleTaskStatus(id)
  })

  // tips
  ipcMain.handle(IpcChannel.Database_GetAllTips, async () => {
    await ensureDbInitialized()
    return db.getAllTips()
  })

  // Screen Monitor
  ipcMain.handle(IpcChannel.Screen_Monitor_Check_Permissions, () => screenshotService.checkPermissions())
  ipcMain.handle(IpcChannel.Screen_Monitor_Get_Capture_All_Sources, () => screenshotService.getCaptureAllSources())

  ipcMain.handle(IpcChannel.Screen_Monitor_Open_Prefs, () => {
    screenshotService.openPrefs()
  })

  ipcMain.handle(IpcChannel.Screen_Monitor_Take_Screenshot, (_, groupIntervalTime: string, sourceId: string) =>
    screenshotService.takeScreenshot(groupIntervalTime, sourceId)
  )

  ipcMain.handle(IpcChannel.Screen_Monitor_Take_Source_Screenshot, (_, sourceId: string) =>
    screenshotService.takeSourceScreenshot(sourceId)
  )

  ipcMain.handle(IpcChannel.Screen_Monitor_Get_Visible_Sources, () => screenshotService.getVisibleSources())

  ipcMain.handle(IpcChannel.Screen_Monitor_Delete_Screenshot, (_, filePath: string) =>
    screenshotService.deleteScreenshot(filePath)
  )

  ipcMain.handle(IpcChannel.Screen_Monitor_Read_Image_Base64, (_, filePath: string) =>
    screenshotService.readImageAsBase64(filePath)
  )

  ipcMain.handle(IpcChannel.Screen_Monitor_Get_Screenshots_By_Date, (_, date?: string) =>
    screenshotService.getScreenshotsByDate(date)
  )

  ipcMain.handle(IpcChannel.Screen_Monitor_Cleanup_Old_Screenshots, (_, retentionDays?: number) =>
    screenshotService.cleanupOldScreenshots(retentionDays)
  )

  ipcMain.handle(IpcChannel.File_Save, (_, fileName: string, fileData: Uint8Array) =>
    FileService.saveFile(fileName, fileData)
  )

  ipcMain.handle(IpcChannel.File_Read, (_, filePath: string) => FileService.readFile(filePath))

  ipcMain.handle(IpcChannel.File_Copy, (_, srcPath: string) => FileService.copyFile(srcPath))

  ipcMain.handle(IpcChannel.File_Get_All, () => FileService.getFiles())

  // Backend service related
  ipcMain.handle(IpcChannel.Backend_GetPort, () => {
    return getBackendPort()
  })

  ipcMain.handle(IpcChannel.Backend_GetStatus, () => {
    return {
      status: getBackendStatus(),
      port: getBackendPort(),
      timestamp: new Date().toISOString()
    }
  })
  // settings
  ipcMain.handle(IpcChannel.Screen_Monitor_Get_Settings, (_, key: string) => {
    return localStoreService.getSetting(key)
  })

  ipcMain.handle(IpcChannel.Screen_Monitor_Set_Settings, (_, key: string, value: unknown) => {
    return localStoreService.setSetting(key, value)
  })
  ipcMain.handle(IpcChannel.Screen_Monitor_Clear_Settings, (_, key: string) => localStoreService.clearSetting(key))
}

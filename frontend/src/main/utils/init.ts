// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import * as fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

import { isLinux, isPortable, isWin } from '@main/constant'
import { app } from 'electron'
import { execSync } from 'node:child_process'

// Please don't import any other modules which is not node/electron built-in modules

function hasWritePermission(path: string) {
  try {
    fs.accessSync(path, fs.constants.W_OK)
    return true
  } catch (error) {
    return false
  }
}

function getConfigDir() {
  return path.join(os.homedir(), '.vikingdb', 'config')
}

function getDataDirFromRegistry() {
  if (!isWin) return null

  try {
    // Read data directory from Windows Registry with timeout protection
    const result = execSync('reg query "HKCU\\Software\\MineContext" /v DataDirectory', {
      encoding: 'utf8',
      timeout: 3000, // 3 second timeout to prevent hanging
      windowsHide: true
    })

    // Parse the registry output
    // Format: "DataDirectory    REG_SZ    C:\Users\...\AppData\Local\MineContext"
    const match = result.match(/DataDirectory\s+REG_SZ\s+(.+)/)
    if (match && match[1]) {
      const dataDir = match[1].trim()
      if (fs.existsSync(dataDir) && hasWritePermission(dataDir)) {
        return dataDir
      }
    }
  } catch (error) {
    // Registry key doesn't exist, timeout, or other error - ignore and use default
    console.warn('Failed to read data directory from registry:', error)
  }

  return null
}

export function initAppDataDir() {
  const appDataPath = getAppDataPathFromConfig()
  if (appDataPath) {
    app.setPath('userData', appDataPath)
    return
  }

  if (isPortable) {
    const portableDir = process.env.PORTABLE_EXECUTABLE_DIR
    app.setPath('userData', path.join(portableDir || app.getPath('exe'), 'data'))
    return
  }

  // For Windows installer version, check registry for custom data directory
  if (isWin && !isPortable) {
    // Try to get data directory from registry (set by installer)
    const registryDataDir = getDataDirFromRegistry()
    if (registryDataDir) {
      app.setPath('userData', registryDataDir)
      return
    }

    // If no registry setting, use the default AppData location
    // (e.g., %LOCALAPPDATA%\MineContext)
    // This is the correct fallback behavior
  }
}

function getAppDataPathFromConfig() {
  try {
    const configPath = path.join(getConfigDir(), 'config.json')
    if (!fs.existsSync(configPath)) {
      return null
    }

    const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'))

    if (!config.appDataPath) {
      return null
    }

    let executablePath = app.getPath('exe')
    if (isLinux && process.env.APPIMAGE) {
      // 如果是 AppImage 打包的应用，直接使用 APPIMAGE 环境变量
      // 这样可以确保获取到正确的可执行文件路径
      executablePath = path.join(path.dirname(process.env.APPIMAGE), 'vikingdb.appimage')
    }

    if (isWin && isPortable) {
      executablePath = path.join(process.env.PORTABLE_EXECUTABLE_DIR || '', 'vikingdb-portable.exe')
    }

    let appDataPath = null
    // 兼容旧版本
    if (config.appDataPath && typeof config.appDataPath === 'string') {
      appDataPath = config.appDataPath
      // 将旧版本数据迁移到新版本
      appDataPath && updateAppDataConfig(appDataPath)
    } else {
      appDataPath = config.appDataPath.find(
        (item: { executablePath: string }) => item.executablePath === executablePath
      )?.dataPath
    }

    if (appDataPath && fs.existsSync(appDataPath) && hasWritePermission(appDataPath)) {
      return appDataPath
    }

    return null
  } catch (error) {
    return null
  }
}

export function updateAppDataConfig(appDataPath: string) {
  const configDir = getConfigDir()
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true })
  }

  // config.json
  // appDataPath: [{ executablePath: string, dataPath: string }]
  const configPath = path.join(configDir, 'config.json')
  let executablePath = app.getPath('exe')
  if (isLinux && process.env.APPIMAGE) {
    executablePath = path.join(path.dirname(process.env.APPIMAGE), 'vikingdb.appimage')
  }

  // If it is a Windows portable version, use the PORTABLE_EXECUTABLE_FILE environment variable
  if (isWin && isPortable) {
    executablePath = path.join(process.env.PORTABLE_EXECUTABLE_DIR || '', 'vikingdb-portable.exe')
  }

  if (!fs.existsSync(configPath)) {
    fs.writeFileSync(configPath, JSON.stringify({ appDataPath: [{ executablePath, dataPath: appDataPath }] }, null, 2))
    return
  }

  const config = JSON.parse(fs.readFileSync(configPath, 'utf-8'))
  if (!config.appDataPath || (config.appDataPath && typeof config.appDataPath !== 'object')) {
    config.appDataPath = []
  }

  const existingPath = config.appDataPath.find(
    (item: { executablePath: string }) => item.executablePath === executablePath
  )

  if (existingPath) {
    existingPath.dataPath = appDataPath
  } else {
    config.appDataPath.push({ executablePath, dataPath: appDataPath })
  }

  fs.writeFileSync(configPath, JSON.stringify(config, null, 2))
}

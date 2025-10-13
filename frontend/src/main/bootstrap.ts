// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { occupiedDirs } from '@shared/config/constant'
import { app } from 'electron'
import fs from 'fs'
import path from 'path'
import { initAppDataDir } from './utils/init'
import { mainLog } from '@shared/logger/main'

// 仅在打包后执行初始化
if (app.isPackaged) {
  initAppDataDir()
}

/**
 * 在应用启动早期执行：根据命令行 --new-data-path 迁移用户数据里被占用的目录
 * 关键点：
 * - 使用 app.commandLine.getSwitchValue 解析参数
 * - 跨平台，无需限制 win32
 * - 保护：新旧路径一致直接跳过；逐项 try/catch 防止崩溃
 * - 复制前确保目标父目录存在
 * - 仅在目标路径有效且不同于旧路径时操作
 */
const handleOccupiedDirsMigration = (): void => {
  // 使用 Electron 提供的命令行解析
  const switchValue = app.commandLine.getSwitchValue('new-data-path')
  const newAppDataPathRaw = switchValue && switchValue.trim()

  if (!newAppDataPathRaw) return

  // 归一化为绝对路径
  const newAppDataPath = path.isAbsolute(newAppDataPathRaw)
    ? newAppDataPathRaw
    : path.resolve(process.cwd(), newAppDataPathRaw)

  const oldAppDataPath = app.getPath('userData')

  // 新旧路径相同则跳过
  if (newAppDataPath === oldAppDataPath) {
    mainLog.warn('[Data Migration] New and old data paths are the same. Skipping copy.')
    return
  }

  mainLog.info(`[Data Migration] Start: "${oldAppDataPath}" -> "${newAppDataPath}"`)

  for (const dirName of occupiedDirs) {
    const sourcePath = path.join(oldAppDataPath, dirName)
    const destinationPath = path.join(newAppDataPath, dirName)

    try {
      if (!fs.existsSync(sourcePath)) {
        mainLog.info(`[Data Migration] Skip (not found): ${sourcePath}`)
        continue
      }

      // 确保目标父目录存在
      fs.mkdirSync(path.dirname(destinationPath), { recursive: true })

      // 递归复制（保留目录结构/文件）
      fs.cpSync(sourcePath, destinationPath, { recursive: true })

      mainLog.info(`[Data Migration] Copied: ${sourcePath} -> ${destinationPath}`)
    } catch (error: any) {
      // 常见错误：权限/只读/磁盘满等
      mainLog.error(`[Data Migration] Failed copying "${dirName}": ${String(error?.message || error)}`)
    }
  }

  mainLog.info('[Data Migration] Done.')
}

// 在创建任何窗口之前执行迁移
handleOccupiedDirsMigration()

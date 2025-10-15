// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import fs from 'node:fs'
import path from 'node:path'

import { getLogger } from '@shared/logger/main'
import { getFilesDir } from '@main/utils/file'

const logger = getLogger('FileService')

class FileService {
  constructor() {
    logger.info('FileService initialized')
  }

  // 把文件保存入目录
  async saveFile(
    fileName: string,
    fileData: Uint8Array
  ): Promise<{ success: boolean; filePath?: string; error?: string }> {
    const filesDir = getFilesDir()
    const filePath = path.join(filesDir, fileName)
    try {
      await fs.promises.writeFile(filePath, fileData)
      logger.info(`File saved to ${filePath}`)
      return { success: true, filePath }
    } catch (error: any) {
      logger.error(`Failed to save file ${filePath}:`, error)
      return { success: false, error: error.message }
    }
  }

  async readFile(filePath: string): Promise<{ success: boolean; data?: string; error?: string }> {
    try {
      const data = await fs.promises.readFile(filePath, 'utf-8')
      return { success: true, data }
    } catch (error: any) {
      logger.error(`Failed to read file at ${filePath}:`, error)
      return { success: false, error: error.message }
    }
  }

  async copyFile(srcPath: string): Promise<{ success: boolean; error?: string }> {
    const filesDir = getFilesDir()
    const destPath = path.join(filesDir, path.basename(srcPath))
    try {
      await fs.promises.copyFile(srcPath, destPath)
      return { success: true }
    } catch (error: any) {
      logger.error(`Failed to copy file from ${srcPath} to ${destPath}:`, error)
      return { success: false, error: error.message }
    }
  }

  async getFiles(): Promise<{ success: boolean; files?: any[]; error?: string }> {
    const filesDir = getFilesDir()
    try {
      const fileNames = await fs.promises.readdir(filesDir)
      const files = await Promise.all(
        fileNames.map(async (fileName) => {
          const filePath = path.join(filesDir, fileName)
          const stats = await fs.promises.stat(filePath)
          return {
            name: fileName,
            source: `${path.extname(fileName).slice(1).toUpperCase()} · ${(stats.size / 1024 / 1024).toFixed(2)}MB`,
            filePath,
            status: 'Analysis successful'
          }
        })
      )
      return { success: true, files }
    } catch (error: any) {
      logger.error('Failed to get files:', error)
      return { success: false, error: error.message }
    }
  }
}

export default new FileService()

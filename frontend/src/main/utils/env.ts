// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { isDev } from '@main/constant'
import { app } from 'electron'
import path from 'path'

export const isPackaged = app.isPackaged
export const actuallyDev = isDev && !isPackaged
export const serverRunInFrontend = true // true 表示python server 已经打包进frontend，可以类似真实环境启动调试

// 动态获取资源路径
export function getResourcesPath(): string {
  if (actuallyDev) {
    if (serverRunInFrontend) {
      // 开发环境：使用frontend目录下的backend目录
      return path.join(__dirname, '..', '..')
    }
    // 开发环境：启动backend 打包好的server
    return path.join(__dirname, '..', '..', '..', 'MineContext')

    // TODO: 开发环境：不打包python server，直连调试，未实现
  } else {
    // 生产环境：使用 process.resourcesPath（包含 extraResources）
    // process.resourcesPath 指向 resources/ 目录
    // app.getAppPath() 指向 app.asar 内部
    return process.resourcesPath
  }
}

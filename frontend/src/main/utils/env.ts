// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { isDev } from '@main/constant'
import { app } from 'electron'
import path from 'path'

export const isPackaged = app.isPackaged
export const actuallyDev = isDev && !isPackaged
export const serverRunInFrontend = true // true means the python server is packaged into the frontend and can be started and debugged like in a real environment

// Dynamically get the resources path
export function getResourcesPath(): string {
  if (actuallyDev) {
    if (serverRunInFrontend) {
      // Development environment: use the backend directory under the frontend directory
      return path.join(__dirname, '..', '..')
    }
    // Development environment: start the packaged server from the backend
    return path.join(__dirname, '..', '..', '..', 'MineContext')

    // TODO: Development environment: do not package the python server, connect directly for debugging, not implemented
  } else {
    // Production environment: use process.resourcesPath (including extraResources)
    // process.resourcesPath points to the resources/ directory
    // app.getAppPath() points to inside app.asar
    return process.resourcesPath
  }
}

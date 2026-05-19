// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { is } from '@electron-toolkit/utils'
import { app } from 'electron'
import path from 'path'

export function resolveSqliteDbPath(dbName = 'app.db'): string {
  if (app.isPackaged || !is.dev) {
    return path.join(app.getPath('userData'), 'persist', 'sqlite', dbName)
  }

  const cwd = process.cwd()
  const projectRoot = path.basename(cwd) === 'frontend' ? path.dirname(cwd) : cwd
  return path.join(projectRoot, 'persist', 'sqlite', dbName)
}

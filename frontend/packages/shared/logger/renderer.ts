// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import Logger from 'electron-log/renderer'

export type LogLevel = 'error' | 'warn' | 'info' | 'debug' | 'silly'

/**
 * Gets a logger instance with a scope.
 * @param scope - The scope name, usually the component name.
 */
export const getLogger = (scope?: string) => {
  return Logger.scope(scope || 'renderer')
}

/**
 * The default logger for the renderer process.
 */
export const rendererLog = getLogger()

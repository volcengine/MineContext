// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import Logger from 'electron-log/main'

export type LogLevel = 'error' | 'warn' | 'info' | 'debug' | 'silly'

/**
 * Gets a logger instance with a scope.
 * @param scope - The scope name, usually the module or file name.
 */
export const getLogger = (scope?: string) => {
  return Logger.scope(scope || 'main')
}

/**
 * The default logger for the main process.
 */
export const mainLog = getLogger()

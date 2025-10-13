// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import Logger from 'electron-log/main'

export type LogLevel = 'error' | 'warn' | 'info' | 'debug' | 'silly'

/**
 * 获取一个带作用域（scope）的日志记录器实例。
 * @param scope - 作用域名称，通常是模块或文件名。
 */
export const getLogger = (scope?: string) => {
  return Logger.scope(scope || 'main')
}

/**
 * 主进程的默认日志记录器。
 */
export const mainLog = getLogger()

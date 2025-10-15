// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export type LogSourceWithContext = {
  process: 'main' | 'renderer'
  window?: string // only for renderer process
  module?: string
  context?: Record<string, unknown>
}

export type LogLevel = 'error' | 'warn' | 'info' | 'debug' | 'verbose' | 'silly' | 'none'

export type LogContextData = any[]

export const LEVEL = {
  ERROR: 'error' as const,
  WARN: 'warn' as const,
  INFO: 'info' as const,
  VERBOSE: 'verbose' as const,
  DEBUG: 'debug' as const,
  SILLY: 'silly' as const,
  NONE: 'none' as const
}

export const LEVEL_MAP: Record<LogLevel, number> = {
  error: 0,
  warn: 1,
  info: 2,
  verbose: 3,
  debug: 4,
  silly: 5,
  none: 6
}





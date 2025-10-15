// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// src/main/lib/logger/init.ts

import path from 'node:path'
import { app } from 'electron'
import log from 'electron-log/main'
import { is } from '@electron-toolkit/utils'
import dayjs from 'dayjs'
import { type Json, redact } from './redact'

/**
 * Initializes the logging system. Must be called at the very beginning of the main process.
 * It handles all critical configurations:
 * 1.  **Automatic IPC**: `log.initialize()` automatically handles communication between the main and renderer processes.
 * 2.  **Tiered Transports**: Sets different log levels and formats for the Console and File transports.
 * 3.  **Dynamic Paths**: Log files are automatically split by process type (main, renderer) and date.
 * 4.  **Structured Logging (NDJSON)**: A `hook` transforms all log messages into single-line JSON strings for easy machine parsing.
 * 5.  **Security**: The `redact` function automatically sanitizes sensitive information from logs.
 * 6.  **Global Catch**: Catches unhandled exceptions and Promise rejections to prevent the application from crashing.
 */
export const initLog = () => {
  // ✨ Key step: Enable all of electron-log's magic features, including automatic IPC.
  log.initialize()

  const isDev = process.env.NODE_ENV === 'development' || is.dev

  // --- Console Transport Configuration ---
  log.transports.console.level = isDev ? 'debug' : 'warn'
  log.transports.console.format = isDev
    ? '[{h}:{i}:{s}.{ms}] [{level}]› {scope} › {text}' // More detailed during development
    : '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] [{scope}] {text}' // Include date in production

  // --- File Transport Configuration ---
  log.transports.file.level = isDev ? 'debug' : 'info'
  log.transports.file.format = '{text}' // ✨ Set format to '{text}' to allow the hook to fully control the output content
  log.transports.file.maxSize = 50 * 1024 * 1024 // 50 MB
  log.transports.file.resolvePathFn = () => {
    // ✨ Dynamically generate log paths, split by "process-date"
    const day = dayjs().format('YYYY-MM-DD')
    const name = `${process.type}-${day}.log`
    // Differentiate log storage locations for development and production environments
    const logDir = path.join(
      !app.isPackaged && isDev ? 'backend' : app.getPath('userData'),
      'frontend-logs' // Store uniformly in the logs subdirectory
    )
    return path.join(logDir, name)
  }

  // Log key Electron application events (e.g., app ready, window-all-closed)
  log.eventLogger.startLogging()

  // --- Global Error Catching ---
  process.on('uncaughtException', (err) => {
    log.error('Unhandled Exception:', err)
  })
  process.on('unhandledRejection', (reason: any) => {
    log.error('Unhandled Rejection:', reason)
  })

  // --- Core Hook: Format all logs as NDJSON ---
  log.hooks.push((m) => {
    const arr = Array.isArray(m.data) ? m.data : m.data == null ? [] : [m.data]

    let msg = ''
    const objs: Json[] = []
    const extra: any[] = []

    // ✨ Classify incoming parameters: string messages, objects, others
    for (const it of arr) {
      if (!msg && typeof it === 'string') {
        msg = it
        continue
      }
      if (it instanceof Error) {
        objs.push({ error: { name: it.name, message: it.message, stack: it.stack } })
        continue
      }
      if (it && typeof it === 'object' && !Array.isArray(it)) {
        objs.push(it)
        continue
      }
      if (it !== undefined) extra.push(it)
    }

    // Merge all objects and redact sensitive information
    const merged = Object.assign({}, ...objs)
    const data = redact(extra.length ? { ...merged, extra } : merged)

    // Build the final single-line JSON object
    const out = {
      t: dayjs().format('YYYY-MM-DD HH:mm:ss.SSS'),
      level: m.level,
      scope: m.scope,
      msg,
      data
    }

    // Use the formatted JSON string as the final log content
    m.data = [JSON.stringify(out)]
    return m
  })
}

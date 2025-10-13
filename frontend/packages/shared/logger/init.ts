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
 * 初始化日志系统。必须在主进程的最开始调用。
 * 它完成了所有关键配置：
 * 1.  **自动IPC**: `log.initialize()` 会自动处理主进程和渲染器进程之间的通信。
 * 2.  **分级传输**: 为控制台（Console）和文件（File）设置不同的日志级别和格式。
 * 3.  **动态路径**: 日志文件会根据进程类型（main, renderer）和日期自动分割。
 * 4.  **结构化日志 (NDJSON)**: 通过 `hook` 将所有日志信息转换为单行 JSON 字符串，便于机器解析。
 * 5.  **安全**: `redact` 函数会自动脱敏日志中的敏感信息。
 * 6.  **全局捕获**: 捕获未处理的异常和 Promise rejections，防止应用崩溃。
 */
export const initLog = () => {
  // ✨ 关键步骤: 开启 electron-log 的所有魔法功能，包括自动的 IPC。
  log.initialize()

  const isDev = process.env.NODE_ENV === 'development' || is.dev

  // --- 控制台传输配置 ---
  log.transports.console.level = isDev ? 'debug' : 'warn'
  log.transports.console.format = isDev
    ? '[{h}:{i}:{s}.{ms}] [{level}]› {scope} › {text}' // 开发时更详细
    : '[{y}-{m}-{d} {h}:{i}:{s}.{ms}] [{level}] [{scope}] {text}' // 生产时带日期

  // --- 文件传输配置 ---
  log.transports.file.level = isDev ? 'debug' : 'info'
  log.transports.file.format = '{text}' // ✨ 格式设为 '{text}' 以便 hook 完全控制输出内容
  log.transports.file.maxSize = 50 * 1024 * 1024 // 50 MB
  log.transports.file.resolvePathFn = () => {
    // ✨ 动态生成日志路径，按 "进程-日期" 分割
    const day = dayjs().format('YYYY-MM-DD')
    const name = `${process.type}-${day}.log`
    // 区分开发和生产环境的日志存储位置
    const logDir = path.join(
      !app.isPackaged && isDev ? 'backend' : app.getPath('userData'),
      'frontend-logs' // 统一存放在 logs 子目录
    )
    return path.join(logDir, name)
  }

  // 记录关键的 Electron 应用事件 (如 app ready, window-all-closed)
  log.eventLogger.startLogging()

  // --- 全局错误捕获 ---
  process.on('uncaughtException', (err) => {
    log.error('Unhandled Exception:', err)
  })
  process.on('unhandledRejection', (reason: any) => {
    log.error('Unhandled Rejection:', reason)
  })

  // --- 核心 Hook: 格式化所有日志为 NDJSON ---
  log.hooks.push((m) => {
    const arr = Array.isArray(m.data) ? m.data : m.data == null ? [] : [m.data]

    let msg = ''
    const objs: Json[] = []
    const extra: any[] = []

    // ✨ 将传入的多个参数进行分类：字符串消息、对象、其他
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

    // 合并所有对象，并进行脱敏
    const merged = Object.assign({}, ...objs)
    const data = redact(extra.length ? { ...merged, extra } : merged)

    // 构建最终的单行 JSON 对象
    const out = {
      t: dayjs().format('YYYY-MM-DD HH:mm:ss.SSS'),
      level: m.level,
      scope: m.scope,
      msg,
      data
    }

    // 将格式化后的 JSON 字符串作为最终的日志内容
    m.data = [JSON.stringify(out)]
    return m
  })
}

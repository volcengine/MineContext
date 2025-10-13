// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

/**
 * activity 表对应的 TypeScript 类型定义
 * 字段类型与 SQL 类型一一映射：
 * - INTEGER → number（自增 ID 为数字）
 * - TEXT → string（文本内容）
 * - JSON → 通用对象类型（Record<string, any>，若知道具体结构可细化）
 * - DATETIME → string（日期时间字符串，通常为 ISO 格式如 '2025-09-28 12:00:00'）
 */
interface Activity {
  // 自增主键（整数）
  id: number
  // 活动标题（文本）
  title: string
  // 活动内容（文本）
  content: string
  // 资源信息（JSON 格式，存储对象）
  resources: string // 若知道具体结构可替换为 { files: string[]; link?: string; ... }
  // 开始时间（日期时间字符串）
  start_time: string
  // 结束时间（日期时间字符串）
  end_time: string
  // 元数据（JSON 格式，存储额外信息）
  metadata: string // 同理，可根据实际结构细化，如 { author: string; status: 'draft' | 'published' }
}

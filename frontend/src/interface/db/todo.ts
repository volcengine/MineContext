// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export interface TODOActivity {
  id: number
  content: string
  created_at: string // 格式: YYYY-MM-DD HH:mm:ss
  start_time: string // 可能是 ISO 字符串
  end_time: string | null
  status: number
  urgency: number
  assignee: string | null
}

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export interface TODOActivity {
  id: number
  content: string
  created_at: string
  start_time: string
  end_time: string | null
  status: number
  urgency: number
  assignee: string | null
}

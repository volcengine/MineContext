// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// Vault类型定义
// 笔记实体
export interface VaultEntity {
  title?: string
  content?: string
  summary?: string
  tags?: string
}
export interface Vault extends VaultEntity {
  id: number  // 设为可选原因是新增Vault时无需给定id，避免ts类型报错
  parent_id?: number | null
  sort_order?: number
  is_folder?: number  // 0: 不是文件夹, 1: 是文件夹
  is_deleted?: number  // 0: 未删除, 1: 已删除，默认为0 未删除
  created_at?: string
  updated_at?: string
}

export interface VaultTreeNode extends Vault {
  children?: VaultTreeNode[]
  [x: string]: any
}

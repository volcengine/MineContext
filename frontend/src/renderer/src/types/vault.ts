// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// Vault type definition
// Note entity
export interface VaultEntity {
  title?: string
  content?: string
  summary?: string
  tags?: string
}
export interface Vault extends VaultEntity {
  id: number // Set as optional because there is no need to provide an id when adding a new Vault, to avoid ts type errors
  parent_id?: number | null
  sort_order?: number
  is_folder?: number // 0: not a folder, 1: is a folder
  is_deleted?: number // 0: not deleted, 1: deleted, defaults to 0 (not deleted)
  created_at?: string
  updated_at?: string
}

export interface VaultTreeNode extends Vault {
  children?: VaultTreeNode[]
  [x: string]: any
}

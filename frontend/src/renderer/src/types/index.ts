// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

export * from './file'

export * from './vault'

export interface StoreSyncAction {
  type: string
  payload: any
  meta?: {
    fromSync?: boolean
    source?: string
  }
}

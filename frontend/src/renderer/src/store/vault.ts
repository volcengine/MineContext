// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { loggerService } from '@logger'
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Vault, VaultTreeNode } from '@renderer/types'
import { findNodeById, findParentNodeById, removeNodeById, updateNodeById } from '@renderer/utils/vault'

const logger = loggerService.withContext('Store:Vault')

export interface VaultState {
  vaults: VaultTreeNode
}

const initialState: VaultState = {
  vaults: {
    id: -1, // 根节点
    children: []
  }
}

const vaultSlice = createSlice({
  name: 'vault',
  initialState,
  reducers: {
    // 初始化vaults
    initVaults(state, action: PayloadAction<{ vaults: VaultTreeNode }>) {
      state.vaults = action.payload.vaults
    },

    // 新增vault
    addVault(state, action: PayloadAction<Vault>) {
      const { parent_id, ...vault } = action.payload

      if (parent_id) {
        // 递归寻找父节点
        const parent = findNodeById(state.vaults, parent_id)
        if (parent) {
          // 确保父节点有children数组
          if (!parent.children) {
            parent.children = []
          }
          parent.children.unshift({ ...vault, name: vault.title, children: [] })
          // 对父节点的children进行排序
          parent.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
        } else {
          logger.warn(`未找到父节点 ID: ${parent_id}`)
        }
      } else {
        // 如果没有parent_id，添加到根节点
        if (!state.vaults.children) {
          state.vaults.children = []
        }
        state.vaults.children.unshift({ ...vault, children: [] })
        // 对根节点的children进行排序
        state.vaults.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
      }
    },

    // 删除vault
    deleteVault(state, action: PayloadAction<{ vaultId: number }>) {
      const success = removeNodeById(state.vaults, action.payload.vaultId)
      if (!success) {
        logger.warn(`未找到要删除的节点 ID: ${action.payload.vaultId}`)
      }
    },

    // 重命名vault，修改title
    renameVault(state, action: PayloadAction<{ vaultId: number; name: string }>) {
      const success = updateNodeById(state.vaults, action.payload.vaultId, (node) => {
        node.title = action.payload.name
        node.updated_at = new Date().toISOString()
      })
      if (!success) {
        logger.warn(`未找到要重命名的节点 ID: ${action.payload.vaultId}`)
      }
    },

    // 直接修改 笔记内容
    updateVault(state, action: PayloadAction<Vault>) {
      const success = updateNodeById(state.vaults, action.payload.id, (node) => {
        Object.assign(node, action.payload)
      })
      if (!success) {
        logger.warn(`未找到要更新的节点 ID: ${action.payload.id}`)
      }
    },

    // 移动笔记位置
    updateVaultPosition(state, action: PayloadAction<Vault>) {
      const { id: vaultId, parent_id: parentId = -1, sort_order = 0 } = action.payload

      // 1. 找到要移动的节点
      const nodeToMove = findNodeById(state.vaults, vaultId)
      if (!nodeToMove) {
        logger.warn(`未找到要移动的节点 ID: ${vaultId}`)
        return
      }

      // 2. 找到原父节点并从其children中移除该节点
      const oldParent = findParentNodeById(state.vaults, vaultId)
      if (oldParent && oldParent.children) {
        const index = oldParent.children.findIndex(child => child.id === vaultId)
        if (index !== -1) {
          oldParent.children.splice(index, 1)
        }
      }

      // 3. 找到新父节点
      let newParent: VaultTreeNode
      if (parentId === -1) {
        // 移动到根节点
        newParent = state.vaults
      } else {
        const foundParent = findNodeById(state.vaults, parentId as number)
        if (!foundParent) {
          logger.warn(`未找到新父节点 ID: ${parentId}`)
          return
        }
        newParent = foundParent
      }

      // 4. 确保新父节点有children数组
      if (!newParent.children) {
        newParent.children = []
      }

      // 5. 根据order插入到指定位置
      const insertIndex = Math.min(sort_order, newParent.children.length)
      newParent.children.splice(insertIndex, 0, nodeToMove)

      // 6. 更新节点的parent_id
      nodeToMove.parent_id = parentId

      // 7. 对新父节点的children进行排序
      newParent.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

      logger.info(`成功移动节点 ${vaultId} 到父节点 ${parentId}，位置 ${insertIndex}`)
    },
  }
})

export const {
  initVaults,
  addVault,
  deleteVault,
  renameVault,
  updateVault,
  updateVaultPosition,
} = vaultSlice.actions

export default vaultSlice.reducer

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getLogger } from '@shared/logger/renderer'
import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { Vault, VaultTreeNode } from '@renderer/types'
import { findNodeById, findParentNodeById, removeNodeById, updateNodeById } from '@renderer/utils/vault'

const logger = getLogger('Store:Vault')

export interface VaultState {
  vaults: VaultTreeNode
}

const initialState: VaultState = {
  vaults: {
    id: -1, // Root node
    children: []
  }
}

const vaultSlice = createSlice({
  name: 'vault',
  initialState,
  reducers: {
    // Initialize vaults
    initVaults(state, action: PayloadAction<{ vaults: VaultTreeNode }>) {
      state.vaults = action.payload.vaults
    },

    // Add a new vault
    addVault(state, action: PayloadAction<Vault>) {
      const { parent_id, ...vault } = action.payload

      if (parent_id) {
        // Recursively find the parent node
        const parent = findNodeById(state.vaults, parent_id)
        if (parent) {
          // Ensure the parent node has a children array
          if (!parent.children) {
            parent.children = []
          }
          parent.children.unshift({ ...vault, name: vault.title, children: [] })
          // Sort the children of the parent node
          parent.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
        } else {
          logger.warn(`Parent node with ID not found: ${parent_id}`)
        }
      } else {
        // If there is no parent_id, add to the root node
        if (!state.vaults.children) {
          state.vaults.children = []
        }
        state.vaults.children.unshift({ ...vault, children: [] })
        // Sort the children of the root node
        state.vaults.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))
      }
    },

    // Delete a vault
    deleteVault(state, action: PayloadAction<{ vaultId: number }>) {
      const success = removeNodeById(state.vaults, action.payload.vaultId)
      if (!success) {
        logger.warn(`Node to be deleted with ID not found: ${action.payload.vaultId}`)
      }
    },

    // Rename a vault, modify the title
    renameVault(state, action: PayloadAction<{ vaultId: number; name: string }>) {
      const success = updateNodeById(state.vaults, action.payload.vaultId, (node) => {
        node.title = action.payload.name
        node.updated_at = new Date().toISOString()
      })
      if (!success) {
        logger.warn(`Node to be renamed with ID not found: ${action.payload.vaultId}`)
      }
    },

    // Directly modify the note content
    updateVault(state, action: PayloadAction<Vault>) {
      const success = updateNodeById(state.vaults, action.payload.id, (node) => {
        Object.assign(node, action.payload)
      })
      if (!success) {
        logger.warn(`Node to be updated with ID not found: ${action.payload.id}`)
      }
    },

    // Move note position
    updateVaultPosition(state, action: PayloadAction<Vault>) {
      const { id: vaultId, parent_id: parentId = -1, sort_order = 0 } = action.payload

      // 1. Find the node to move
      const nodeToMove = findNodeById(state.vaults, vaultId)
      if (!nodeToMove) {
        logger.warn(`Node to be moved with ID not found: ${vaultId}`)
        return
      }

      // 2. Find the original parent node and remove the node from its children
      const oldParent = findParentNodeById(state.vaults, vaultId)
      if (oldParent && oldParent.children) {
        const index = oldParent.children.findIndex((child) => child.id === vaultId)
        if (index !== -1) {
          oldParent.children.splice(index, 1)
        }
      }

      // 3. Find the new parent node
      let newParent: VaultTreeNode
      if (parentId === -1) {
        // Move to the root node
        newParent = state.vaults
      } else {
        const foundParent = findNodeById(state.vaults, parentId as number)
        if (!foundParent) {
          logger.warn(`New parent node with ID not found: ${parentId}`)
          return
        }
        newParent = foundParent
      }

      // 4. Ensure the new parent node has a children array
      if (!newParent.children) {
        newParent.children = []
      }

      // 5. Insert into the specified position based on the order
      const insertIndex = Math.min(sort_order, newParent.children.length)
      newParent.children.splice(insertIndex, 0, nodeToMove)

      // 6. Update the node's parent_id
      nodeToMove.parent_id = parentId

      // 7. Sort the children of the new parent node
      newParent.children.sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0))

      logger.info(`Successfully moved node ${vaultId} to parent node ${parentId}, position ${insertIndex}`)
    }
  }
})

export const { initVaults, addVault, deleteVault, renameVault, updateVault, updateVaultPosition } = vaultSlice.actions

export default vaultSlice.reducer

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getAllVaults, insertVault, updateVaultById, softDeleteVaultById, createFolder } from '@renderer/databases'
import { initVaults, addVault, deleteVault, renameVault, updateVault, updateVaultPosition } from '@renderer/store/vault'
import { Vault } from '@renderer/types'
import { getLogger } from '@shared/logger/renderer'
import { sortTreeByOrder } from '@renderer/utils/vault'

import { AppDispatch } from '..'

const logger = getLogger('VaultThunk')

/**
 * Initialize the vault tree structure
 */
export const initVaultsThunk = () => async (dispatch: AppDispatch) => {
  try {
    const vaults = await getAllVaults()
    // Build the tree structure
    const vaultTree = buildVaultTree(vaults)
    dispatch(initVaults({ vaults: vaultTree }))
  } catch (error: any) {
    logger.error('Failed to initialize vaults:', error)
    throw error
  }
}

/**
 * Add a new vault (operates on both the database and the Redux store)
 */
export const addVaultThunk = (vault: Omit<Vault, 'id'>) => async (dispatch: AppDispatch) => {
  try {
    // 1. First, insert into the database
    const result = await insertVault(vault as Vault)

    // 2. Construct the complete vault object
    const newVault: Vault = {
      ...vault,
      id: result.id,
      created_at: vault.created_at || new Date().toISOString(),
      updated_at: vault.updated_at || new Date().toISOString()
    }

    // 3. Update the Redux store
    dispatch(addVault(newVault))

    logger.info(`Vault added successfully: ID ${result.id}`)
    return newVault
  } catch (error: any) {
    logger.error('Failed to add vault:', error)
    throw error
  }
}

/**
 * Delete a vault (soft delete, operates on both the database and the Redux store)
 */
export const deleteVaultThunk = (vaultId: number) => async (dispatch: AppDispatch) => {
  try {
    // 1. First, soft delete the database record
    await softDeleteVaultById(vaultId)

    // 2. Remove from the Redux store
    dispatch(deleteVault({ vaultId }))

    logger.info(`Vault deleted successfully: ID ${vaultId}`)
  } catch (error: any) {
    logger.error('Failed to delete vault:', error)
    throw error
  }
}

/**
 * Update vault content (operates on both the database and the Redux store)
 */
export const updateVaultThunk = (vaultId: number, updates: Partial<Vault>) => async (dispatch: AppDispatch) => {
  try {
    // 1. First, update the database
    await updateVaultById(vaultId, updates)

    // 2. Construct the complete update object
    const updatedVault: Vault = {
      ...updates,
      id: vaultId,
      updated_at: new Date().toISOString()
    } as Vault

    // 3. Update the Redux store
    dispatch(updateVault(updatedVault))

    return updatedVault
  } catch (error: any) {
    logger.error('Failed to update vault:', error)
    throw error
  }
}

/**
 * Move vault position
 */
export const updateVaultPositionThunk = (vaultId: number, updates: Partial<Vault>) => async (dispatch: AppDispatch) => {
  try {
    // 1. First, update the database
    await updateVaultById(vaultId, updates)

    // 2. Construct the complete update object
    const updatedVault: Vault = {
      ...updates,
      id: vaultId,
      updated_at: new Date().toISOString()
    } as Vault

    // 3. Update the Redux store
    dispatch(updateVaultPosition(updatedVault))

    return updatedVault
  } catch (error: any) {
    logger.error('Failed to update vault:', error)
    throw error
  }
}

/**
 * Rename a vault (operates on both the database and the Redux store)
 */
export const renameVaultThunk = (vaultId: number, name: string) => async (dispatch: AppDispatch) => {
  try {
    // 1. First, update the database
    await updateVaultById(vaultId, { title: name, updated_at: new Date().toISOString() })

    // 2. Update the Redux store
    dispatch(renameVault({ vaultId, name }))

    logger.info(`Vault renamed successfully: ID ${vaultId}, new name: ${name}`)
  } catch (error: any) {
    logger.error('Failed to rename vault:', error)
    throw error
  }
}

/**
 * Create a folder (operates on both the database and the Redux store)
 */
export const createFolderThunk = (title: string, parentId?: number) => async (dispatch: AppDispatch) => {
  try {
    logger.info(`Starting to create folder: ${title} - ${parentId}`)
    // 1. First, create the folder in the database
    const result = await createFolder(title, parentId)
    logger.info(`Finished creating folder: ${title} - ${parentId}`)

    // 2. Construct the folder object
    const newFolder: Vault = {
      id: result.id,
      title,
      content: '',
      parent_id: parentId || -1,
      is_folder: 1,
      is_deleted: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    // 3. Add to the Redux store
    dispatch(addVault(newFolder))

    logger.info(`Folder created successfully: ID ${result.id}, name: ${title}`)
    return newFolder
  } catch (error: any) {
    logger.error('Failed to create folder:', error)
    throw error
  }
}

/**
 * Helper function to build the vault tree structure
 */
function buildVaultTree(vaults: Vault[]) {
  // Create the root node
  const root = {
    id: -1,
    children: []
  }

  // Create a map from ID to node
  const nodeMap = new Map()
  nodeMap.set(-1, root)

  // Initialize all nodes
  vaults.forEach((vault) => {
    nodeMap.set(vault.id, {
      ...vault,
      children: []
    })
  })

  // Build the tree structure
  vaults.forEach((vault) => {
    const node = nodeMap.get(vault.id)
    // Handle Markdown symbols in the title
    // if (node.title) {
    //   node.title = removeMarkdownSymbols(node.title)
    // }
    const parentId = vault.parent_id || -1
    const parent = nodeMap.get(parentId)

    if (parent) {
      if (!parent.children) {
        parent.children = []
      }
      parent.children.push(node)
    }
  })

  // Apply sorting
  sortTreeByOrder(root)
  return root
}

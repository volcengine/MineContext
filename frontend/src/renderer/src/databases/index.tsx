// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import type { Vault } from '@renderer/types/vault'

// Vault database operations
export const getAllVaults = async () => {
  try {
    const vaults = await window.dbAPI.getAllVaults()
    return vaults
  } catch (error) {
    console.error('Failed to get all vaults:', error)
    throw error
  }
}

export const getVaultById = async (id: number) => {
  try {
    const vault = await window.dbAPI.getVaultById(id)
    return vault
  } catch (error) {
    console.error('Failed to get vault by ID:', error)
    throw error
  }
}

export const getVaultByTitle = async (title: string) => {
  try {
    const vaults = await window.dbAPI.getVaultByTitle(title)
    return vaults
  } catch (error) {
    console.error('Failed to get vault by title:', error)
    throw error
  }
}

export const updateVaultById = async (id: number, vault: Partial<Vault>) => {
  try {
    const result = await window.dbAPI.updateVaultById(id, vault)
    return result
  } catch (error) {
    console.error('Failed to update vault by ID:', error)
    throw error
  }
}

export const insertVault = async (vault: Vault) => {
  try {
    const result = await window.dbAPI.insertVault(vault)
    return result
  } catch (error) {
    console.error('Failed to insert vault:', error)
    throw error
  }
}

export const deleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.deleteVaultById(id)
    return result
  } catch (error) {
    console.error('Failed to delete vault by ID:', error)
    throw error
  }
}

// New database operation methods
export const getVaultsByParentId = async (parentId: number | null) => {
  try {
    const vaults = await window.dbAPI.getVaultsByParentId(parentId)
    return vaults
  } catch (error) {
    console.error('Failed to get vaults by parent ID:', error)
    throw error
  }
}

export const getFolders = async () => {
  try {
    const folders = await window.dbAPI.getFolders()
    return folders
  } catch (error) {
    console.error('Failed to get folders:', error)
    throw error
  }
}

export const softDeleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.softDeleteVaultById(id)
    return result
  } catch (error) {
    console.error('Failed to soft delete vault:', error)
    throw error
  }
}

export const restoreVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.restoreVaultById(id)
    return result
  } catch (error) {
    console.error('Failed to restore vault:', error)
    throw error
  }
}

export const hardDeleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.hardDeleteVaultById(id)
    return result
  } catch (error) {
    console.error('Failed to permanently delete vault:', error)
    throw error
  }
}

export const createFolder = async (title: string, parentId?: number) => {
  try {
    const result = await window.dbAPI.createFolder(title, parentId)
    return result
  } catch (error) {
    console.error('Failed to create folder:', error)
    throw error
  }
}
// Test database API
// Add a normal vault
// const newVault = await insertVault({
//   title: 'Test Vault',
//   content: 'Test content',
//   summary: 'Test summary',
//   tags: 'tag1,tag2',
//   parent_id: null,
//   is_folder: 0
//   created_at: '2024-01-01',
//   updated_at: '2024-12-31',
// })
// console.log('New Vault ID:', newVault.id)

// Create a folder
// const newFolder = await createFolder('Test Folder', null)
// console.log('New Folder ID:', newFolder.id)

// Soft delete
// await softDeleteVaultById(1)

// Restore
// await restoreVaultById(1)

// Permanently delete
// await hardDeleteVaultById(1)

// Modify
// await updateVaultById(42, {
//   title: 'Updated Vault',
//   content: 'Updated Content',
//   summary: 'Updated summary'
// })

// Find vault by ID
// const vault = await getVaultById(2)
// console.log('Vault:', vault)

// Find vault by title
// const vaults_by_title = await getVaultByTitle('Test Vault')
// console.log('Vaults:', vaults_by_title)

// Find vaults by parent ID
// const vaults_by_parent = await getVaultsByParentId(1)
// console.log('Child Vaults:', vaults_by_parent)

// Get all folders
// const folders = await getFolders()
// console.log('Folders:', folders)

// Find all vaults
// const vaults = await getVaults()
// console.log('All Vaults:', vaults)

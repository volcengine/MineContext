// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import type { Vault } from '@renderer/types/vault'

// Vault数据库操作
export const getAllVaults = async () => {
  try {
    const vaults = await window.dbAPI.getAllVaults()
    return vaults
  } catch (error) {
    console.error('获取所有Vault失败:', error)
    throw error
  }
}

export const getVaultById = async (id: number) => {
  try {
    const vault = await window.dbAPI.getVaultById(id)
    return vault
  } catch (error) {
    console.error('根据ID获取Vault失败:', error)
    throw error
  }
}

export const getVaultByTitle = async (title: string) => {
  try {
    const vaults = await window.dbAPI.getVaultByTitle(title)
    return vaults
  } catch (error) {
    console.error('根据标题获取Vault失败:', error)
    throw error
  }
}

export const updateVaultById = async (id: number, vault: Partial<Vault>) => {
  try {
    const result = await window.dbAPI.updateVaultById(id, vault)
    return result
  } catch (error) {
    console.error('根据ID更新Vault失败:', error)
    throw error
  }
}

export const insertVault = async (vault: Vault) => {
  try {
    const result = await window.dbAPI.insertVault(vault)
    return result
  } catch (error) {
    console.error('插入Vault失败:', error)
    throw error
  }
}

export const deleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.deleteVaultById(id)
    return result
  } catch (error) {
    console.error('根据ID删除Vault失败:', error)
    throw error
  }
}

// 新增的数据库操作方法
export const getVaultsByParentId = async (parentId: number | null) => {
  try {
    const vaults = await window.dbAPI.getVaultsByParentId(parentId)
    return vaults
  } catch (error) {
    console.error('根据父ID获取Vault失败:', error)
    throw error
  }
}

export const getFolders = async () => {
  try {
    const folders = await window.dbAPI.getFolders()
    return folders
  } catch (error) {
    console.error('获取文件夹失败:', error)
    throw error
  }
}

export const softDeleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.softDeleteVaultById(id)
    return result
  } catch (error) {
    console.error('软删除Vault失败:', error)
    throw error
  }
}

export const restoreVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.restoreVaultById(id)
    return result
  } catch (error) {
    console.error('恢复Vault失败:', error)
    throw error
  }
}

export const hardDeleteVaultById = async (id: number) => {
  try {
    const result = await window.dbAPI.hardDeleteVaultById(id)
    return result
  } catch (error) {
    console.error('永久删除Vault失败:', error)
    throw error
  }
}

export const createFolder = async (title: string, parentId?: number) => {
  try {
    const result = await window.dbAPI.createFolder(title, parentId)
    return result
  } catch (error) {
    console.error('创建文件夹失败:', error)
    throw error
  }
}
// 测试数据库API
// 增加普通vault
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
// console.log('新增Vault ID:', newVault.id)

// 创建文件夹
// const newFolder = await createFolder('Test Folder', null)
// console.log('新增文件夹 ID:', newFolder.id)

// 软删除
// await softDeleteVaultById(1)

// 恢复
// await restoreVaultById(1)

// 永久删除
// await hardDeleteVaultById(1)

// 修改
// await updateVaultById(42, {
//   title: 'Updated Vault',
//   content: 'Updated Content',
//   summary: 'Updated summary'
// })

// 根据id查找Vault
// const vault = await getVaultById(2)
// console.log('Vault:', vault)

// 根据标题查找Vault
// const vaults_by_title = await getVaultByTitle('Test Vault')
// console.log('Vaults:', vaults_by_title)

// 根据父ID查找Vault
// const vaults_by_parent = await getVaultsByParentId(1)
// console.log('子Vault:', vaults_by_parent)

// 获取所有文件夹
// const folders = await getFolders()
// console.log('文件夹:', folders)

// 查找全部Vaults
// const vaults = await getVaults()
// console.log('所有Vault:', vaults)


// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getAllVaults, insertVault, updateVaultById, softDeleteVaultById, createFolder } from '@renderer/databases'
import { initVaults, addVault, deleteVault, renameVault, updateVault, updateVaultPosition } from '@renderer/store/vault'
import { Vault } from '@renderer/types'
import { loggerService } from '@logger'
import { sortTreeByOrder } from '@renderer/utils/vault'

import { AppDispatch } from '..'

const logger = loggerService.withContext('VaultThunk')

/**
 * 初始化vault树结构
 */
export const initVaultsThunk = () => async (dispatch: AppDispatch) => {
  try {
    const vaults = await getAllVaults()
    // 构建树结构
    const vaultTree = buildVaultTree(vaults)
    dispatch(initVaults({ vaults: vaultTree }))
  } catch (error: any) {
    logger.error('初始化vault失败:', error)
    throw error
  }
}

/**
 * 添加新的vault（同时操作数据库和Redux store）
 */
export const addVaultThunk = (vault: Omit<Vault, 'id'>) => async (dispatch: AppDispatch) => {
  try {
    // 1. 先插入数据库
    const result = await insertVault(vault as Vault)

    // 2. 构造完整的vault对象
    const newVault: Vault = {
      ...vault,
      id: result.id,
      created_at: vault.created_at || new Date().toISOString(),
      updated_at: vault.updated_at || new Date().toISOString()
    }

    // 3. 更新Redux store
    dispatch(addVault(newVault))

    logger.info(`添加vault成功: ID ${result.id}`)
    return newVault
  } catch (error: any) {
    logger.error('添加vault失败:', error)
    throw error
  }
}

/**
 * 删除vault（软删除，同时操作数据库和Redux store）
 */
export const deleteVaultThunk = (vaultId: number) => async (dispatch: AppDispatch) => {
  try {
    // 1. 先软删除数据库记录
    await softDeleteVaultById(vaultId)

    // 2. 从Redux store中移除
    dispatch(deleteVault({ vaultId }))

    logger.info(`删除vault成功: ID ${vaultId}`)
  } catch (error: any) {
    logger.error('删除vault失败:', error)
    throw error
  }
}

/**
 * 更新vault内容（同时操作数据库和Redux store）
 */
export const updateVaultThunk = (vaultId: number, updates: Partial<Vault>) => async (dispatch: AppDispatch) => {
  try {
    // 1. 先更新数据库
    await updateVaultById(vaultId, updates)

    // 2. 构造完整的更新对象
    const updatedVault: Vault = {
      ...updates,
      id: vaultId,
      updated_at: new Date().toISOString()
    } as Vault

    // 3. 更新Redux store
    dispatch(updateVault(updatedVault))

    logger.info(`更新vault成功: ID ${vaultId}`)
    return updatedVault
  } catch (error: any) {
    logger.error('更新vault失败:', error)
    throw error
  }
}

/**
 * 移动vault位置
 */
export const updateVaultPositionThunk = (vaultId: number, updates: Partial<Vault>) => async (dispatch: AppDispatch) => {
  try {
    // 1. 先更新数据库
    await updateVaultById(vaultId, updates)

    // 2. 构造完整的更新对象
    const updatedVault: Vault = {
      ...updates,
      id: vaultId,
      updated_at: new Date().toISOString()
    } as Vault

    // 3. 更新Redux store
    dispatch(updateVaultPosition(updatedVault))

    logger.info(`更新vault成功: ID ${vaultId}`)
    return updatedVault
  } catch (error: any) {
    logger.error('更新vault失败:', error)
    throw error
  }
}

/**
 * 重命名vault（同时操作数据库和Redux store）
 */
export const renameVaultThunk = (vaultId: number, name: string) => async (dispatch: AppDispatch) => {
  try {
    // 1. 先更新数据库
    await updateVaultById(vaultId, { title: name, updated_at: new Date().toISOString() })

    // 2. 更新Redux store
    dispatch(renameVault({ vaultId, name }))

    logger.info(`重命名vault成功: ID ${vaultId}, 新名称: ${name}`)
  } catch (error: any) {
    logger.error('重命名vault失败:', error)
    throw error
  }
}

/**
 * 创建文件夹（同时操作数据库和Redux store）
 */
export const createFolderThunk = (title: string, parentId?: number) => async (dispatch: AppDispatch) => {
  try {
    logger.info(`开始创建文件夹：${title} - ${parentId}`)
    // 1. 先在数据库中创建文件夹
    const result = await createFolder(title, parentId)
    logger.info(`完成文件夹创建：${title} - ${parentId}`)

    // 2. 构造文件夹对象
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

    // 3. 添加到Redux store
    dispatch(addVault(newFolder))

    logger.info(`创建文件夹成功: ID ${result.id}, 名称: ${title}`)
    return newFolder
  } catch (error: any) {
    logger.error('创建文件夹失败:', error)
    throw error
  }
}

/**
 * 构建vault树结构的辅助函数
 */
function buildVaultTree(vaults: Vault[]) {
  // 创建根节点
  const root = {
    id: -1,
    children: []
  }

  // 创建ID到节点的映射
  const nodeMap = new Map()
  nodeMap.set(-1, root)

  // 初始化所有节点
  vaults.forEach(vault => {
    nodeMap.set(vault.id, {
      ...vault,
      children: []
    })
  })

  // 构建树结构
  vaults.forEach(vault => {
    const node = nodeMap.get(vault.id)
    // 处理标题中的Markdown符号
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

  // 应用排序
  sortTreeByOrder(root)
  return root
}

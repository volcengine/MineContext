// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { useCallback, useEffect, useState } from 'react'
import { useSelector } from 'react-redux'
import { RootState, useAppDispatch } from '@renderer/store'
import {
  initVaultsThunk,
  addVaultThunk,
  deleteVaultThunk,
  updateVaultThunk,
  updateVaultPositionThunk,
  renameVaultThunk,
  createFolderThunk,
} from '@renderer/store/thunk/vaultThunk'
import { Vault, VaultTreeNode } from '@renderer/types'
import { findNodeById, findParentNodeById, collectAllNodeIds, getNodePath, traverseNodes } from '@renderer/utils/vault'
import { loggerService } from '@logger'

const logger = loggerService.withContext('useVaults')

interface UseVaultsReturn {
  // 数据
  vaults: VaultTreeNode
  selectedVaultId: number | null
  // 状态
  loading: boolean
  error: string | null

  // 基础CRUD操作
  initVaults: () => Promise<void>
  addVault: (vault: Omit<Vault, 'id'>) => Promise<Vault | null>
  deleteVault: (vaultId: number) => Promise<void>
  updateVault: (vaultId: number, updates: Partial<Vault>) => Promise<Vault | null>
  updateVaultPosition: (vaultId: number, updates: Partial<Vault>) => Promise<Vault | null>
  saveVaultContent: (vaultId: number, content: string) => Promise<Vault | null>
  saveVaultTitle: (vaultId: number, title: string) => Promise<Vault | null>
  renameVault: (vaultId: number, name: string) => Promise<void>
  createFolder: (title: string, parentId?: number) => Promise<Vault | null>

  // 查询方法
  findVaultById: (id: number) => VaultTreeNode | null
  findParentVault: (id: number) => VaultTreeNode | null
  getVaultPath: (id: number) => VaultTreeNode[] | null
  getAllVaultIds: () => number[]

  // 过滤和搜索
  searchVaults: (keyword: string) => VaultTreeNode[]
  getVaultsByFolder: (folderId: number) => VaultTreeNode[]
  getFolders: () => VaultTreeNode[]

  // 工具方法
  isFolder: (vault: VaultTreeNode) => boolean
  hasChildren: (vault: VaultTreeNode) => boolean
  getChildrenCount: (vault: VaultTreeNode) => number

  // 设置选中vault
  setSelectedVaultId: (id: number | null) => void
}

export const useVaults = (): UseVaultsReturn => {
  const dispatch = useAppDispatch()
  const vaults = useSelector((state: RootState) => state.vault.vaults)

  // 本地状态管理
  const [selectedVaultId, setSelectedVaultId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 初始化vaults
  const initVaults = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      await dispatch(initVaultsThunk())
      logger.info('初始化vault成功')
    } catch (err: any) {
      const errorMsg = err?.message || '初始化vault失败'
      setError(errorMsg)
      logger.error('初始化vault失败:', err)
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 添加vault
  const addVault = useCallback(async (vault: Omit<Vault, 'id'>) => {
    try {
      setLoading(true)
      setError(null)
      const result = await dispatch(addVaultThunk(vault))
      logger.info('添加vault成功:', result)
      return result as Vault
    } catch (err: any) {
      const errorMsg = err?.message || '添加vault失败'
      setError(errorMsg)
      logger.error('添加vault失败:', err)
      return null
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 删除vault
  const deleteVault = useCallback(async (vaultId: number) => {
    try {
      setLoading(true)
      setError(null)
      await dispatch(deleteVaultThunk(vaultId))
      logger.info(`删除vault成功，ID: ${vaultId}`)
    } catch (err: any) {
      const errorMsg = err?.message || '删除vault失败'
      setError(errorMsg)
      logger.error('删除vault失败:', err)
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 更新vault
  const updateVault = useCallback(async (vaultId: number, updates: Partial<Vault>) => {
    try {
      setLoading(true)
      setError(null)
      const result = await dispatch(updateVaultThunk(vaultId, updates))
      return result as Vault
    } catch (err: any) {
      const errorMsg = err?.message || '更新vault失败'
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 移动vault位置
  const updateVaultPosition = useCallback(async (vaultId: number, updates: Partial<Vault>) => {
    try {
      setLoading(true)
      setError(null)
      const result = await dispatch(updateVaultPositionThunk(vaultId, updates))
      return result as Vault
    } catch (err: any) {
      const errorMsg = err?.message || '移动vault位置失败'
      setError(errorMsg)
      return null
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 修改markdown内容
  const saveVaultContent = useCallback(async (vaultId: number, content: string) => {
    return await updateVault(vaultId, { content })
  }, [updateVault])

  const saveVaultTitle = useCallback(async (vaultId: number, title: string) => {
    return await updateVault(vaultId, { title })
  }, [updateVault])

  // 重命名vault
  const renameVault = useCallback(async (vaultId: number, name: string) => {
    try {
      setLoading(true)
      setError(null)
      await dispatch(renameVaultThunk(vaultId, name))
      logger.info(`重命名vault成功，ID: ${vaultId}, 新名称: ${name}`)
    } catch (err: any) {
      const errorMsg = err?.message || '重命名vault失败'
      setError(errorMsg)
      logger.error('重命名vault失败:', err)
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 创建文件夹
  const createFolder = useCallback(async (title: string, parentId?: number) => {
    try {
      setLoading(true)
      setError(null)
      const result = await dispatch(createFolderThunk(title, parentId))
      logger.info('创建文件夹成功:', result)
      return result as Vault
    } catch (err: any) {
      const errorMsg = err?.message || '创建文件夹失败'
      setError(errorMsg)
      logger.error('创建文件夹失败:', err)
      return null
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // 查询方法
  const findVaultById = useCallback((id: number) => {
    return findNodeById(vaults, id)
  }, [vaults])

  const findParentVault = useCallback((id: number) => {
    return findParentNodeById(vaults, id)
  }, [vaults])

  const getVaultPath = useCallback((id: number) => {
    return getNodePath(vaults, id)
  }, [vaults])

  const getAllVaultIds = useCallback(() => {
    return collectAllNodeIds(vaults)
  }, [vaults])

  // 搜索vaults title
  const searchVaults = useCallback((keyword: string) => {
    const results: VaultTreeNode[] = []
    const searchKeyword = keyword.toLowerCase()

    traverseNodes(vaults, (node) => {
      if (node.id !== -1 && ( // 排除根节点
        node.title?.toLowerCase().includes(searchKeyword)
      )) {
        results.push(node)
      }
    })

    return results
  }, [vaults])

  // 获取指定文件夹下的vaults
  const getVaultsByFolder = useCallback((folderId: number) => {
    const folder = findNodeById(vaults, folderId)
    return folder?.children || []
  }, [vaults])

  // 获取所有文件夹
  const getFolders = useCallback(() => {
    const folders: VaultTreeNode[] = []

    traverseNodes(vaults, (node) => {
      if (node.id !== -1 && node.is_folder === 1) {
        folders.push(node)
      }
    })

    return folders
  }, [vaults])

  // 工具方法
  const isFolder = useCallback((vault: VaultTreeNode) => {
    return vault.is_folder === 1
  }, [])

  const hasChildren = useCallback((vault: VaultTreeNode) => {
    return Boolean(vault?.children?.length)
  }, [])

  const getChildrenCount = useCallback((vault: VaultTreeNode) => {
    return vault?.children?.length || 0
  }, [])

  // 组件挂载时自动初始化
  useEffect(() => {
    if (!vaults.children || vaults.children.length === 0) {
      initVaults()
    }
  }, [])

  return {
    // 数据
    vaults,
    selectedVaultId,
    // 状态
    loading,
    error,

    // 基础CRUD操作
    initVaults,
    addVault,
    deleteVault,
    updateVault,
    updateVaultPosition,
    saveVaultContent,
    saveVaultTitle,
    renameVault,
    createFolder,

    // 查询方法
    findVaultById,
    findParentVault,
    getVaultPath,
    getAllVaultIds,

    // 过滤和搜索
    searchVaults,
    getVaultsByFolder,
    getFolders,

    // 工具方法
    isFolder,
    hasChildren,
    getChildrenCount,

    // 设置选中vault
    setSelectedVaultId,
  }
}

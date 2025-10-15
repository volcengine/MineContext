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
  createFolderThunk
} from '@renderer/store/thunk/vaultThunk'
import { Vault, VaultTreeNode } from '@renderer/types'
import { findNodeById, findParentNodeById, collectAllNodeIds, getNodePath, traverseNodes } from '@renderer/utils/vault'
import { getLogger } from '@shared/logger/renderer'

const logger = getLogger('useVaults')

interface UseVaultsReturn {
  // Data
  vaults: VaultTreeNode
  selectedVaultId: number | null
  // Status
  loading: boolean
  error: string | null

  // Basic CRUD operations
  initVaults: () => Promise<void>
  addVault: (vault: Omit<Vault, 'id'>) => Promise<Vault | null>
  deleteVault: (vaultId: number) => Promise<void>
  updateVault: (vaultId: number, updates: Partial<Vault>) => Promise<Vault | null>
  updateVaultPosition: (vaultId: number, updates: Partial<Vault>) => Promise<Vault | null>
  saveVaultContent: (vaultId: number, content: string) => Promise<Vault | null>
  saveVaultTitle: (vaultId: number, title: string) => Promise<Vault | null>
  renameVault: (vaultId: number, name: string) => Promise<void>
  createFolder: (title: string, parentId?: number) => Promise<Vault | null>

  // Query methods
  findVaultById: (id: number) => VaultTreeNode | null
  findParentVault: (id: number) => VaultTreeNode | null
  getVaultPath: (id: number) => VaultTreeNode[] | null
  getAllVaultIds: () => number[]

  // Filtering and searching
  searchVaults: (keyword: string) => VaultTreeNode[]
  getVaultsByFolder: (folderId: number) => VaultTreeNode[]
  getFolders: () => VaultTreeNode[]

  // Utility methods
  isFolder: (vault: VaultTreeNode) => boolean
  hasChildren: (vault: VaultTreeNode) => boolean
  getChildrenCount: (vault: VaultTreeNode) => number

  // Set selected vault
  setSelectedVaultId: (id: number | null) => void
}

export const useVaults = (): UseVaultsReturn => {
  const dispatch = useAppDispatch()
  const vaults = useSelector((state: RootState) => state.vault.vaults)

  // Local state management
  const [selectedVaultId, setSelectedVaultId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Initialize vaults
  const initVaults = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      await dispatch(initVaultsThunk())
      logger.info('Vaults initialized successfully')
    } catch (err: any) {
      const errorMsg = err?.message || 'Failed to initialize vaults'
      setError(errorMsg)
      logger.error('Failed to initialize vaults:', err)
    } finally {
      setLoading(false)
    }
  }, [dispatch])

  // Add vault
  const addVault = useCallback(
    async (vault: Omit<Vault, 'id'>) => {
      try {
        setLoading(true)
        setError(null)
        const result = await dispatch(addVaultThunk(vault))
        logger.info('Vault added successfully:', result)
        return result as Vault
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to add vault'
        setError(errorMsg)
        logger.error('Failed to add vault:', err)
        return null
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Delete vault
  const deleteVault = useCallback(
    async (vaultId: number) => {
      try {
        setLoading(true)
        setError(null)
        await dispatch(deleteVaultThunk(vaultId))
        logger.info(`Vault deleted successfully, ID: ${vaultId}`)
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to delete vault'
        setError(errorMsg)
        logger.error('Failed to delete vault:', err)
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Update vault
  const updateVault = useCallback(
    async (vaultId: number, updates: Partial<Vault>) => {
      try {
        setLoading(true)
        setError(null)
        const result = await dispatch(updateVaultThunk(vaultId, updates))
        return result as Vault
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to update vault'
        setError(errorMsg)
        return null
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Move vault position
  const updateVaultPosition = useCallback(
    async (vaultId: number, updates: Partial<Vault>) => {
      try {
        setLoading(true)
        setError(null)
        const result = await dispatch(updateVaultPositionThunk(vaultId, updates))
        return result as Vault
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to move vault position'
        setError(errorMsg)
        return null
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Save markdown content
  const saveVaultContent = useCallback(
    async (vaultId: number, content: string) => {
      return await updateVault(vaultId, { content })
    },
    [updateVault]
  )

  const saveVaultTitle = useCallback(
    async (vaultId: number, title: string) => {
      return await updateVault(vaultId, { title })
    },
    [updateVault]
  )

  // Rename vault
  const renameVault = useCallback(
    async (vaultId: number, name: string) => {
      try {
        setLoading(true)
        setError(null)
        await dispatch(renameVaultThunk(vaultId, name))
        logger.info(`Vault renamed successfully, ID: ${vaultId}, new name: ${name}`)
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to rename vault'
        setError(errorMsg)
        logger.error('Failed to rename vault:', err)
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Create folder
  const createFolder = useCallback(
    async (title: string, parentId?: number) => {
      try {
        setLoading(true)
        setError(null)
        const result = await dispatch(createFolderThunk(title, parentId))
        logger.info('Folder created successfully:', result)
        return result as Vault
      } catch (err: any) {
        const errorMsg = err?.message || 'Failed to create folder'
        setError(errorMsg)
        logger.error('Failed to create folder:', err)
        return null
      } finally {
        setLoading(false)
      }
    },
    [dispatch]
  )

  // Query methods
  const findVaultById = useCallback(
    (id: number) => {
      return findNodeById(vaults, id)
    },
    [vaults]
  )

  const findParentVault = useCallback(
    (id: number) => {
      return findParentNodeById(vaults, id)
    },
    [vaults]
  )

  const getVaultPath = useCallback(
    (id: number) => {
      return getNodePath(vaults, id)
    },
    [vaults]
  )

  const getAllVaultIds = useCallback(() => {
    return collectAllNodeIds(vaults)
  }, [vaults])

  // Search vault titles
  const searchVaults = useCallback(
    (keyword: string) => {
      const results: VaultTreeNode[] = []
      const searchKeyword = keyword.toLowerCase()

      traverseNodes(vaults, (node) => {
        if (
          node.id !== -1 && // Exclude root node
          node.title?.toLowerCase().includes(searchKeyword)
        ) {
          results.push(node)
        }
      })

      return results
    },
    [vaults]
  )

  // Get vaults in a specific folder
  const getVaultsByFolder = useCallback(
    (folderId: number) => {
      const folder = findNodeById(vaults, folderId)
      return folder?.children || []
    },
    [vaults]
  )

  // Get all folders
  const getFolders = useCallback(() => {
    const folders: VaultTreeNode[] = []

    traverseNodes(vaults, (node) => {
      if (node.id !== -1 && node.is_folder === 1) {
        folders.push(node)
      }
    })

    return folders
  }, [vaults])

  // Utility methods
  const isFolder = useCallback((vault: VaultTreeNode) => {
    return vault.is_folder === 1
  }, [])

  const hasChildren = useCallback((vault: VaultTreeNode) => {
    return Boolean(vault?.children?.length)
  }, [])

  const getChildrenCount = useCallback((vault: VaultTreeNode) => {
    return vault?.children?.length || 0
  }, [])

  // Automatically initialize on component mount
  useEffect(() => {
    if (!vaults.children || vaults.children.length === 0) {
      initVaults()
    }
  }, [])

  return {
    // Data
    vaults,
    selectedVaultId,
    // Status
    loading,
    error,

    // Basic CRUD operations
    initVaults,
    addVault,
    deleteVault,
    updateVault,
    updateVaultPosition,
    saveVaultContent,
    saveVaultTitle,
    renameVault,
    createFolder,

    // Query methods
    findVaultById,
    findParentVault,
    getVaultPath,
    getAllVaultIds,

    // Filtering and searching
    searchVaults,
    getVaultsByFolder,
    getFolders,

    // Utility methods
    isFolder,
    hasChildren,
    getChildrenCount,

    // Set selected vault
    setSelectedVaultId
  }
}

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.

import { getLogger } from '@shared/logger/main'
import type { Vault } from '@types'
import { DB } from './Database'
import { VaultDocumentType } from '@shared/enums/global-enum'
import dayjs from 'dayjs'
// SPDX-License-Identifier: Apache-2.0
const logger = getLogger('VaultDatabaseService')

export interface VaultQueryOptions {
  documentTypes?: VaultDocumentType | VaultDocumentType[] // Document types filter
  isFolder?: number // 0: files only, 1: folders only, undefined: all
  isDeleted?: number // 0: not deleted, 1: deleted, undefined: all
  parentId?: number | null // Filter by parent folder
  createdFrom?: number // Created time lower bound (Unix timestamp in milliseconds)
  createdTo?: number // Created time upper bound (Unix timestamp in milliseconds)
  updatedFrom?: number // Updated time lower bound (Unix timestamp in milliseconds)
  updatedTo?: number // Updated time upper bound (Unix timestamp in milliseconds)
  limit?: number // Max number of results
  offset?: number // Offset for pagination
}
class VaultDatabaseService {
  /**
   * Query Vaults with flexible filters including time range and document types
   * @param options Query options with multiple filters
   * @returns Array of Vault items
   */
  public queryVaults(options: VaultQueryOptions = {}): Vault[] {
    try {
      const db = DB.getInstance()

      // Build WHERE conditions
      const conditions: string[] = []
      const params: Record<string, any> = {}

      // Document types filter
      if (options.documentTypes !== undefined) {
        const types = Array.isArray(options.documentTypes)
          ? options.documentTypes
          : [options.documentTypes]
        const placeholders = types.map((_, index) => `@docType${index}`).join(', ')
        conditions.push(`document_type IN (${placeholders})`)
        types.forEach((type, index) => {
          params[`docType${index}`] = type
        })
      }

      // Folder filter
      if (options.isFolder !== undefined) {
        conditions.push('is_folder = @isFolder')
        params.isFolder = options.isFolder
      }

      // Deleted filter
      if (options.isDeleted !== undefined) {
        conditions.push('is_deleted = @isDeleted')
        params.isDeleted = options.isDeleted
      } else {
        // Default: exclude deleted items
        conditions.push('is_deleted = 0')
      }

      // Parent ID filter
      if (options.parentId !== undefined) {
        if (options.parentId === null) {
          conditions.push('parent_id IS NULL')
        } else {
          conditions.push('parent_id = @parentId')
          params.parentId = options.parentId
        }
      }

      // Created time range
      if (options.createdFrom !== undefined) {
        conditions.push('created_at >= @createdFrom')
        params.createdFrom = dayjs(options.createdFrom).toISOString()
      }

      if (options.createdTo !== undefined) {
        conditions.push('created_at <= @createdTo')
        params.createdTo = dayjs(options.createdTo).toISOString()
      }

      // Updated time range
      if (options.updatedFrom !== undefined) {
        conditions.push('updated_at >= @updatedFrom')
        params.updatedFrom = dayjs(options.updatedFrom).toISOString()
      }

      if (options.updatedTo !== undefined) {
        conditions.push('updated_at <= @updatedTo')
        params.updatedTo = dayjs(options.updatedTo).toISOString()
      }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''
      const limit = options.limit ?? 100
      const offset = options.offset ?? 0

      const sql = `
        SELECT * FROM vaults
        ${whereClause}
        ORDER BY updated_at DESC, id DESC
        LIMIT ${limit} OFFSET ${offset}
      `

      const result = db.query<Vault>(sql, conditions.length > 0 ? params : undefined)
      logger.debug(`📊 Queried ${result.length} vaults with options:`, options)
      return result
    } catch (error) {
      logger.error('❌ Failed to query Vaults with options:', error)
      throw error
    }
  }

  public getVaults(): Vault[] {
    try {
      const db = DB.getInstance()
      const sql = `SELECT * FROM vaults WHERE is_deleted = 0 ORDER BY id DESC`
      const rows = db.query<Vault>(sql)
      logger.debug(`📊 Found all ${rows.length} vaults (not including deleted)`)
      return rows
    } catch (error) {
      logger.error('❌ Failed to query Vaults:', error)
      throw error
    }
  }
  // Query Vault by ID
  public getVaultById(id: number): Vault | undefined {
    try {
      const db = DB.getInstance()
      const sql = 'SELECT * FROM vaults WHERE id = ? AND is_deleted = 0'
      const row = db.queryOne<Vault>(sql, id)
      logger.info(`📋 Querying Vault by ID: ${id}`, row ? '✅ Found' : '❌ Not found')
      return row
    } catch (error) {
      logger.error('❌ Failed to query Vault by ID:', error)
      throw error
    }
  }
  // Query Vaults by document type
  public getVaultsByDocumentType(documentType: VaultDocumentType | VaultDocumentType[]): Vault[] {
    if (!documentType || (Array.isArray(documentType) && documentType.length === 0)) {
      logger.warn('⚠️ getVaultsByTypes called with empty array.')
      return []
    }
    try {
      const placeholders = Array.isArray(documentType) ? documentType.map(() => '?').join(', ') : '?'
      const db = DB.getInstance()
      const sql = `SELECT * FROM vaults WHERE document_type IN (${placeholders}) AND is_deleted = 0 ORDER BY id DESC`
      const rows = db.query<Vault>(sql, Array.isArray(documentType) ? documentType : [documentType])
      logger.info(`📊 Found ${rows.length} Vaults for document type: ${documentType}`)
      return rows
    } catch (error) {
      logger.error('❌ Failed to query Vaults by document type:', error)
      throw error
    }
  }

  // Query Vaults by parent ID
  public getVaultsByParentId(parentId: number | null): Vault[] {
    try {
      const db = DB.getInstance()
      const sql = 'SELECT * FROM vaults WHERE parent_id = ? AND is_deleted = 0 ORDER BY id DESC'
      const rows = db.query<Vault>(sql, parentId)
      logger.info(`📊 Found ${rows.length} Vaults for parent ID: ${parentId}`)
      return rows
    } catch (error) {
      logger.error('❌ Failed to query Vaults by parent ID:', error)
      throw error
    }
  }

  // Query folders
  public getFolders(): Vault[] {
    try {
      const db = DB.getInstance()
      const sql = 'SELECT * FROM vaults WHERE is_folder = 1 AND is_deleted = 0 ORDER BY id DESC'
      const rows = db.query<Vault>(sql)
      logger.info(`📁 Found ${rows.length} folders`)
      return rows
    } catch (error) {
      logger.error('❌ Failed to query folders:', error)
      throw error
    }
  }

  public getVaultByTitle(title: string): Vault[] {
    try {
      const db = DB.getInstance()
      const sql = 'SELECT * FROM vaults WHERE title = ? AND is_deleted = 0'
      const rows = db.query<Vault>(sql, title)
      logger.info(`📋 Querying Vault by title: ${title}`, rows.length > 0 ? `✅ Found ${rows.length}` : '❌ Not found')
      return rows
    } catch (error) {
      logger.error('❌ Failed to query Vault by title:', error)
      throw error
    }
  }

  // Insert a Vault
  public insertVault(vault: Vault): { id: number } {
    try {
      const db = DB.getInstance()

      const dataToInsert = {
        title: vault.title || '',
        content: vault.content,
        summary: vault.summary || '',
        tags: vault.tags || '',
        parent_id: vault.parent_id ?? null,
        is_folder: vault.is_folder || 0,
        is_deleted: 0,
        sort_order: vault.sort_order || 0
        // created_at: dayjs().toISOString(),
        // updated_at: dayjs().toISOString()
      }

      const result = db.insert('vaults', dataToInsert)
      const newId = result.lastInsertRowid as number

      logger.info('✅ Vault inserted successfully:', newId)
      return { id: newId }
    } catch (error) {
      logger.error('❌ Failed to insert Vault:', error)
      throw error
    }
  }

  // Update a Vault
  public updateVaultById(id: number, vaultUpdate: Partial<Vault>): { changes: number } {
    try {
      // If there are no fields to update, return directly
      if (Object.keys(vaultUpdate).length === 0) {
        logger.info(`ℹ️ No fields to update for Vault ${id}`)
        return { changes: 0 }
      }

      const db = DB.getInstance()

      const result = db.update('vaults', vaultUpdate, { id })

      logger.info(`✅ Vault updated successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      logger.error('❌ Failed to update Vault:', error)
      throw error
    }
  }

  // Soft delete a Vault (mark as deleted)
  public softDeleteVaultById(id: number): { changes: number } {
    try {
      const db = DB.getInstance()
      const result = db.update('vaults', { is_deleted: 1 }, { id })

      logger.info(`🗑️ Vault soft deleted successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      logger.error('❌ Failed to soft delete Vault:', error)
      throw error
    }
  }

  // Restore a deleted Vault
  public restoreVaultById(id: number): { changes: number } {
    try {
      const db = DB.getInstance()

      const result = db.update('vaults', { is_deleted: 0 }, { id })

      logger.info(`♻️ Vault restored successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      logger.error('❌ Failed to restore Vault:', error)
      throw error
    }
  }

  // Hard delete a Vault (permanently delete)
  public hardDeleteVaultById(id: number): { changes: number } {
    try {
      const db = DB.getInstance()
      const sql = 'DELETE FROM vaults WHERE id = ?'
      const result = db.execute(sql, id)

      logger.info(`💥 Vault permanently deleted successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      logger.error('❌ Failed to permanently delete Vault:', error)
      throw error
    }
  }

  // Create a folder
  public createFolder(title: string, parentId?: number): { id: number } {
    try {
      const db = DB.getInstance()

      const folderData = {
        title,
        is_folder: 1,
        parent_id: parentId ?? null,
        is_deleted: 0
      }

      const result = db.insert('vaults', folderData)
      const newId = result.lastInsertRowid as number

      logger.info('📁 Folder created successfully:', newId)
      return { id: newId }
    } catch (error) {
      logger.error('❌ Failed to create folder:', error)
      throw error
    }
  }

  // Delete a Vault (This is an alias for hard delete)
  public deleteVaultById(id: number): { changes: number } {
    // This method is identical to hardDelete, so we can just call it.
    logger.info(`🗑️ Calling hard delete for Vault ID: ${id}`)
    return this.hardDeleteVaultById(id)
  }

  /**
   * Get Vaults within a time range (created_at)
   * @param createdFrom Created time lower bound (Unix timestamp)
   * @param createdTo Created time upper bound (Unix timestamp)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Vault items
   */
  public getVaultsInTimeRange(
    createdFrom: number,
    createdTo: number,
    limit = 100,
    offset = 0
  ): Vault[] {
    return this.queryVaults({
      createdFrom,
      createdTo,
      limit,
      offset
    })
  }

  /**
   * Get Vaults by multiple document types with time range
   * @param documentTypes Document types to filter
   * @param createdFrom Optional created time lower bound
   * @param createdTo Optional created time upper bound
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Vault items
   */
  public getVaultsByTypesAndTimeRange(
    documentTypes: VaultDocumentType | VaultDocumentType[],
    createdFrom?: number,
    createdTo?: number,
    limit = 100,
    offset = 0
  ): Vault[] {
    return this.queryVaults({
      documentTypes,
      createdFrom,
      createdTo,
      limit,
      offset
    })
  }

  /**
   * Get recently updated Vaults
   * @param days Number of days to look back (default: 7)
   * @param limit Max number of results
   * @returns Array of Vault items
   */
  public getRecentlyUpdatedVaults(days = 7, limit = 100): Vault[] {
    const updatedFrom = dayjs().subtract(days, 'day').valueOf()
    const updatedTo = dayjs().valueOf()

    return this.queryVaults({
      updatedFrom,
      updatedTo,
      limit
    })
  }

  /**
   * Get Vaults by folder with time range
   * @param parentId Parent folder ID (null for root level)
   * @param createdFrom Optional created time lower bound
   * @param createdTo Optional created time upper bound
   * @param limit Max number of results
   * @returns Array of Vault items
   */
  public getVaultsByFolderAndTimeRange(
    parentId: number | null,
    createdFrom?: number,
    createdTo?: number,
    limit = 100
  ): Vault[] {
    return this.queryVaults({
      parentId,
      createdFrom,
      createdTo,
      limit
    })
  }
}
export { VaultDatabaseService }

// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.

import { getLogger } from '@shared/logger/main'
import type { Vault } from '@types'
import { DB } from './Database'
// SPDX-License-Identifier: Apache-2.0
const logger = getLogger('VaultDatabaseService')
class VaultDatabaseService {
  public getVaults(type: string = 'vaults'): Vault[] {
    try {
      const db = DB.getInstance()
      const sql = `SELECT * FROM vaults WHERE is_deleted = 0 AND document_type = ? ORDER BY id DESC`
      const rows = db.query<Vault>(sql, type)
      logger.debug(`📊 Found ${rows.length} ${type}`)
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
}
export { VaultDatabaseService }

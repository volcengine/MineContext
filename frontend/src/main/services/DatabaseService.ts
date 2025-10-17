// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// electron/database.ts - SQLite Database Manager (ES Module Compatible)
import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'fs'
import { app } from 'electron'
import type { Vault } from '@types'
import { toSqliteDatetime } from '../utils/time'
import { is } from '@electron-toolkit/utils'
import { DB } from './Database'
import { TODOActivity } from '@interface/db/todo'

class DatabaseManager {
  private db: Database.Database | null = null
  private dbPath: string
  private isInitialized: boolean = false
  private initPromise: Promise<void> | null = null

  constructor() {
    // Dynamically get the application path
    // this.dbPath = path.join(app.getPath('userData'), "persist", "sqlite", "app.db")
    this.dbPath = path.join(
      !app.isPackaged && is.dev ? 'backend' : app.getPath('userData'),
      'persist',
      'sqlite',
      'app.db'
    )
    console.log('📁 Database path:', this.dbPath)
  }

  // Asynchronously initialize the database
  public async initialize(): Promise<void> {
    if (this.isInitialized) {
      return
    }

    if (this.initPromise) {
      return this.initPromise
    }

    this.initPromise = this._initialize()
    return this.initPromise
  }

  private async _initialize(): Promise<void> {
    try {
      // Wait for the database directory to be created
      await this.waitForDatabaseDirectory()

      this.db = new Database(this.dbPath)

      // Enable WAL mode for better performance
      this.db!.pragma('journal_mode = WAL')

      // Only initialize the table structure when needed
      this.ensureTablesExist()
      this.isInitialized = true
      console.log('✅ Database initialized successfully')
    } catch (error) {
      console.error('❌ Database initialization failed:', error)
      throw error
    }
  }

  // Wait for the database directory to be created
  private async waitForDatabaseDirectory(): Promise<void> {
    const maxRetries = 30 // Wait for a maximum of 30 seconds
    const retryDelay = 1000 // Check once per second

    for (let i = 0; i < maxRetries; i++) {
      const dbDir = path.dirname(this.dbPath)

      if (fs.existsSync(dbDir)) {
        console.log('📁 Database directory found:', dbDir)
        return
      }

      console.log(`⏳ Waiting for database directory... (${i + 1}/${maxRetries})`)
      await new Promise((resolve) => setTimeout(resolve, retryDelay))
    }

    throw new Error(`Database directory not found after ${maxRetries} seconds: ${path.dirname(this.dbPath)}`)
  }

  // Ensure the database is initialized
  private ensureInitialized(): void {
    if (!this.isInitialized || !this.db) {
      throw new Error('Database not initialized. Call initialize() first.')
    }
  }

  private ensureTablesExist() {
    try {
      // Check if the table exists
      const tableExists = this.db!.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='vaults'").get()

      if (!tableExists) {
        console.log('📊 Creating vaults table for the first time...')
        // this.createVaultsTable()
      }
    } catch (error) {
      console.error('❌ Failed to ensure tables exist:', error)
      throw error
    }
  }

  // // todo: Move table definitions to the backend
  // private createVaultsTable() {
  //   this.db!.exec(`
  //     CREATE TABLE vaults (
  //       id INTEGER PRIMARY KEY AUTOINCREMENT,
  //       parent_id INTEGER,
  //       sort_order INTEGER,
  //       title TEXT,
  //       content TEXT,
  //       summary TEXT,
  //       tags TEXT,
  //       is_folder INTEGER DEFAULT 0,
  //       is_deleted INTEGER DEFAULT 0,
  //       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  //       updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  //       FOREIGN KEY (parent_id) REFERENCES vaults(id)
  //     );
  //   `)
  //   // Create indexes to improve query performance
  //   this.db!.exec(`
  //     CREATE INDEX IF NOT EXISTS idx_vaults_title ON vaults(title);
  //     CREATE INDEX IF NOT EXISTS idx_vaults_parent_id ON vaults(parent_id);
  //     CREATE INDEX IF NOT EXISTS idx_vaults_order ON vaults(sort_order);
  //     CREATE INDEX IF NOT EXISTS idx_vaults_is_folder ON vaults(is_folder);
  //     CREATE INDEX IF NOT EXISTS idx_vaults_is_deleted ON vaults(is_deleted);
  //   `)
  //   console.log('✅ Vaults table created successfully')
  // }

  // private createTodoTable() {
  //   this.db!.exec(`
  //     CREATE TABLE todo (
  //       id INTEGER PRIMARY KEY AUTOINCREMENT,
  //       content TEXT,
  //       created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  //       start_time DATETIME,
  //       end_time DATETIME,
  //       status INTEGER DEFAULT 0,
  //       urgency INTEGER DEFAULT 0
  //     );
  //   `)
  //   this.db!.exec(`
  //     CREATE INDEX IF NOT EXISTS idx_todo_status ON todo(status);
  //     CREATE INDEX IF NOT EXISTS idx_todo_urgency ON todo(urgency);
  //   `)
  //   console.log('✅ Todo table created successfully')
  // }

  // private createActivityTable() {
  //   this.db!.exec(`
  //     CREATE TABLE activity (
  //       id INTEGER PRIMARY KEY AUTOINCREMENT,
  //       title TEXT,
  //       content TEXT,
  //       resources JSON,
  //       start_time DATETIME,
  //       end_time DATETIME
  //     );
  //   `)
  //   this.db!.exec(`
  //     CREATE INDEX IF NOT EXISTS idx_activity_status ON activity(title);
  //     CREATE INDEX IF NOT EXISTS idx_activity_urgency ON activity(start_time);
  //   `)
  //   console.log('✅ Activity table created successfully')
  // }

  // private createTipsTable() {
  //   this.db!.exec(`
  //     CREATE TABLE tips (
  //       id INTEGER PRIMARY KEY AUTOINCREMENT,
  //       content TEXT,
  //       created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  //     );
  //   `)
  //   this.db!.exec(`
  //     CREATE INDEX IF NOT EXISTS idx_tips_status ON tips(content);
  //   `)
  //   console.log('✅ Tips table created successfully')
  // }

  // Query all Vaults (excluding deleted ones)
  public getVaults(type: string = 'vaults'): Vault[] {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare(`SELECT * FROM vaults WHERE is_deleted = 0 AND document_type = ? ORDER BY id DESC`)
      const rows = stmt.all(type) as Vault[]
      console.log(`📊 Found ${rows.length} ${type}`)
      return rows
    } catch (error) {
      console.error('❌ Failed to query Vaults:', error)
      throw error
    }
  }

  // Query Vault by ID
  public getVaultById(id: number): Vault | undefined {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM vaults WHERE id = ? AND is_deleted = 0')
      const row = stmt.get(id) as Vault | undefined
      console.log(`📋 Querying Vault by ID: ${id}`, row ? '✅ Found' : '❌ Not found')
      return row
    } catch (error) {
      console.error('❌ Failed to query Vault by ID:', error)
      throw error
    }
  }

  // Query Vaults by parent ID
  public getVaultsByParentId(parentId: number | null): Vault[] {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM vaults WHERE parent_id = ? AND is_deleted = 0 ORDER BY id DESC')
      const rows = stmt.all(parentId) as Vault[]
      console.log(`📊 Found ${rows.length} Vaults by parent ID`)
      return rows
    } catch (error) {
      console.error('❌ Failed to query Vaults by parent ID:', error)
      throw error
    }
  }

  // Query folders
  public getFolders(): Vault[] {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM vaults WHERE is_folder = 1 AND is_deleted = 0 ORDER BY id DESC')
      const rows = stmt.all() as Vault[]
      console.log(`📁 Found ${rows.length} folders`)
      return rows
    } catch (error) {
      console.error('❌ Failed to query folders:', error)
      throw error
    }
  }

  public getVaultByTitle(title: string): Vault[] {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM vaults WHERE title = ? AND is_deleted = 0')
      const rows = stmt.all([title]) as Vault[]
      console.log(`📋 Querying Vault by title: ${title}`, rows ? `✅ Found ${rows.length}` : '❌ Not found')
      return rows
    } catch (error) {
      console.error('❌ Failed to query Vault by title:', error)
      throw error
    }
  }

  // Insert a Vault
  public insertVault(vault: Vault): { id: number } {
    try {
      this.ensureInitialized()
      const title = vault.title || ''
      const summary = vault.summary || ''
      const tags = vault.tags || ''
      const parent_id = vault.parent_id || null
      const is_folder = vault.is_folder || 0
      const sort_order = vault.sort_order || 0

      const stmt = this.db!.prepare(
        'INSERT INTO vaults (title, content, summary, tags, parent_id, is_folder, is_deleted, created_at, updated_at, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
      )

      const now = new Date()
      const result = stmt.run(
        title,
        vault.content,
        summary,
        tags,
        parent_id,
        is_folder,
        0,
        toSqliteDatetime(now),
        toSqliteDatetime(now),
        sort_order
      )

      console.log('✅ Vault inserted successfully:', result.lastInsertRowid)
      return { id: result.lastInsertRowid as number }
    } catch (error) {
      console.error('❌ Failed to insert Vault:', error)
      throw error
    }
  }

  // Update a Vault
  public updateVaultById(id: number, vault: Partial<Vault>): { changes: number } {
    try {
      this.ensureInitialized()
      // Check if the Vault exists
      const existingVault = this.getVaultById(id)
      if (!existingVault) {
        throw new Error(`Vault with ID ${id} not found`)
      }

      // Find the changed fields
      const changedFields: string[] = []
      const values: any[] = []

      const fieldMapping = {
        title: vault.title !== undefined && vault.title !== existingVault.title,
        content: vault.content !== undefined && vault.content !== existingVault.content,
        summary: vault.summary !== undefined && vault.summary !== existingVault.summary,
        tags: vault.tags !== undefined && vault.tags !== existingVault.tags,
        parent_id: vault.parent_id !== undefined && vault.parent_id !== existingVault.parent_id,
        is_folder: vault.is_folder !== undefined && vault.is_folder !== existingVault.is_folder,
        is_deleted: vault.is_deleted !== undefined && vault.is_deleted !== existingVault.is_deleted,
        created_at: vault.created_at !== undefined && vault.created_at !== existingVault.created_at,
        updated_at: vault.updated_at !== undefined && vault.updated_at !== existingVault.updated_at
      }

      // Build the update statement
      Object.entries(fieldMapping).forEach(([field, hasChanged]) => {
        if (hasChanged) {
          changedFields.push(field)
          values.push(vault[field as keyof Vault])
        }
      })

      // If there are no changed fields, return directly
      if (changedFields.length === 0) {
        console.log(`ℹ️ No fields to update for Vault ${id}`)
        return { changes: 0 }
      }

      // Add the update timestamp
      changedFields.push('updated_at')
      values.push(new Date().toISOString())

      // Build the dynamic SQL
      const setClause = changedFields.map((field) => `${field} = ?`).join(', ')
      const sql = `UPDATE vaults SET ${setClause} WHERE id = ?`
      values.push(id)

      const stmt = this.db!.prepare(sql)
      const result = stmt.run(...values)

      console.log(
        `✅ Vault updated successfully: ID ${id}, updated fields: ${changedFields.join(', ')}, rows affected: ${result.changes}`
      )
      return { changes: result.changes }
    } catch (error) {
      console.error('❌ Failed to update Vault:', error)
      throw error
    }
  }

  // Soft delete a Vault (mark as deleted)
  public softDeleteVaultById(id: number): { changes: number } {
    try {
      this.ensureInitialized()
      // Check if the Vault exists
      const existingVault = this.getVaultById(id)
      if (!existingVault) {
        throw new Error(`Vault with ID ${id} not found`)
      }

      const stmt = this.db!.prepare('UPDATE vaults SET is_deleted = 1, updated_at = ? WHERE id = ?')
      const now = new Date().toISOString()
      const result = stmt.run(now, id)

      console.log(`🗑️ Vault soft deleted successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      console.error('❌ Failed to soft delete Vault:', error)
      throw error
    }
  }

  // Restore a deleted Vault
  public restoreVaultById(id: number): { changes: number } {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('UPDATE vaults SET is_deleted = 0, updated_at = ? WHERE id = ?')
      const now = new Date().toISOString()
      const result = stmt.run(now, id)

      console.log(`♻️ Vault restored successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      console.error('❌ Failed to restore Vault:', error)
      throw error
    }
  }

  // Hard delete a Vault (permanently delete)
  public hardDeleteVaultById(id: number): { changes: number } {
    try {
      this.ensureInitialized()
      // Check if the Vault exists
      const existingVault = this.getVaultById(id)
      if (!existingVault) {
        throw new Error(`Vault with ID ${id} not found`)
      }

      const stmt = this.db!.prepare('DELETE FROM vaults WHERE id = ?')
      const result = stmt.run(id)

      console.log(`💥 Vault permanently deleted successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      console.error('❌ Failed to permanently delete Vault:', error)
      throw error
    }
  }

  // Create a folder
  public createFolder(title: string, parentId?: number): { id: number } {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare(
        'INSERT INTO vaults (title, content, is_folder, parent_id, is_deleted, created_at, updated_at) VALUES (?, ?, 1, ?, 0, ?, ?)'
      )

      const now = new Date().toISOString()
      const result = stmt.run(title, '', parentId || null, now, now)

      console.log('📁 Folder created successfully:', result.lastInsertRowid)
      return { id: result.lastInsertRowid as number }
    } catch (error) {
      console.error('❌ Failed to create folder:', error)
      throw error
    }
  }

  // Delete a Vault
  public deleteVaultById(id: number): { changes: number } {
    try {
      this.ensureInitialized()
      // Check if the Vault exists
      const existingVault = this.getVaultById(id)
      if (!existingVault) {
        throw new Error(`Vault with ID ${id} not found`)
      }

      const stmt = this.db!.prepare('DELETE FROM vaults WHERE id = ?')
      const result = stmt.run(id)

      console.log(`🗑️ Vault deleted successfully: ID ${id}, rows affected: ${result.changes}`)
      return { changes: result.changes }
    } catch (error) {
      console.error('❌ Failed to delete Vault:', error)
      throw error
    }
  }

  // Get all activities
  public getAllActivities() {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM activity')
      const rows = stmt.all()
      console.log('✅ All activities retrieved successfully:', rows)
      return rows
    } catch (error) {
      console.error('❌ Failed to get all activities:', error)
      throw error
    }
  }

  // Get new activities
  // "2024-01-15T10:30:00.000Z" or "2024-01-15 10:30:00" format
  public getNewActivities(startTime: string, endTime: string = '2099-12-31 00:00:00') {
    try {
      this.ensureInitialized()
      const start = toSqliteDatetime(new Date(startTime))
      const end = toSqliteDatetime(new Date(endTime))
      const stmt = this.db!.prepare(
        'SELECT * FROM activity WHERE start_time > ? AND start_time < ? ORDER BY start_time ASC'
      )
      const rows = stmt.all(start, end)
      return rows
    } catch (error) {
      console.error('❌ Failed to get new activities:', error)
      throw error
    }
  }

  public getTasks(startTime: string, endTime: string = '2099-12-31 00:00:00') {
    try {
      this.ensureInitialized()
      const start = toSqliteDatetime(startTime)
      const end = toSqliteDatetime(endTime)
      const db = DB.getInstance(DB.dbName)
      const sql = 'SELECT * FROM todo WHERE start_time > ? AND start_time < ? ORDER BY start_time ASC'
      const rows = db.query<TODOActivity>(sql, [start, end])
      return rows
    } catch (error) {
      console.error('❌ Failed to get tasks:', error)
      throw error
    }
  }

  // Add to the appropriate place in the file
  public addTask(
    taskData: Partial<{ content?: string; status?: number; start_time?: string; end_time?: string; urgency?: number }>
  ) {
    try {
      this.ensureInitialized()
      const db = DB.getInstance(DB.dbName)
      const info = db.insert('todo', taskData)
      return info
    } catch (error) {
      console.error('❌ Failed to add task:', error)
      throw error
    }
  }

  public toggleTaskStatus(taskId: number) {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('UPDATE todo SET status = 1 - status WHERE id = ?')
      const result = stmt.run(taskId)
      console.log('✅ Task status toggled successfully')
      return result
    } catch (error) {
      console.error('❌ Failed to toggle task status:', error)
      throw error
    }
  }

  public updateTask(
    taskId: number,
    taskData: Partial<{ content: string; urgency: number; start_time: string; end_time: string }>
  ) {
    try {
      this.ensureInitialized()

      // Build the dynamic update statement
      const updateFields: string[] = []
      const values: any[] = []

      if (taskData.content !== undefined) {
        updateFields.push('content = ?')
        values.push(taskData.content)
      }
      if (taskData.urgency !== undefined) {
        updateFields.push('urgency = ?')
        values.push(taskData.urgency)
      }
      if (taskData.start_time !== undefined) {
        updateFields.push('start_time = ?')
        values.push(taskData.start_time)
      }
      if (taskData.end_time !== undefined) {
        updateFields.push('end_time = ?')
        values.push(taskData.end_time)
      }

      if (updateFields.length === 0) {
        throw new Error('No fields provided to update')
      }

      values.push(taskId) // Parameter for the WHERE clause

      const stmt = this.db!.prepare(`UPDATE todo SET ${updateFields.join(', ')} WHERE id = ?`)
      const result = stmt.run(...values)

      console.log(`✅ Task updated successfully: ID ${taskId}, rows affected: ${result.changes}`)
      return result
    } catch (error) {
      console.error('❌ Failed to update task:', error)
      throw error
    }
  }

  public deleteTask(taskId: number) {
    try {
      this.ensureInitialized()

      // Check if the task exists
      const existingTask = this.db!.prepare('SELECT * FROM todo WHERE id = ?').get(taskId)
      if (!existingTask) {
        throw new Error(`Task with ID ${taskId} not found`)
      }

      const stmt = this.db!.prepare('DELETE FROM todo WHERE id = ?')
      const result = stmt.run(taskId)

      console.log(`✅ Task deleted successfully: ID ${taskId}, rows affected: ${result.changes}`)
      return result
    } catch (error) {
      console.error('❌ Failed to delete task:', error)
      throw error
    }
  }

  public getAllTips() {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM tips')
      const rows = stmt.all()
      console.log('✅ Tips retrieved successfully')
      return rows
    } catch (error) {
      console.error('❌ Failed to get tips:', error)
      throw error
    }
  }

  close() {
    try {
      console.log('🔒 Closing database connection...')
      this.db?.close()
    } catch (error) {
      console.error('❌ Error closing database:', error)
    }
  }
}

// 导出单例实例
const databaseManager = new DatabaseManager()
export default databaseManager

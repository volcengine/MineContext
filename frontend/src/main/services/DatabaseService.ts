// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// electron/database.ts - SQLite Database Manager (ES Module Compatible)
import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'fs'
import { app } from 'electron'
import { isValidIsoString, toSqliteDatetime } from '../utils/time'
import { is } from '@electron-toolkit/utils'
import { DB } from './Database'
import { TODOActivity } from '@interface/db/todo'
import { getLogger } from '@shared/logger/main'
import { VaultDatabaseService } from './VaultDatabaseService'
const logger = getLogger('DatabaseManager')
class DatabaseManager extends VaultDatabaseService {
  private db: Database.Database | null = null
  private dbPath: string
  private isInitialized: boolean = false
  private initPromise: Promise<void> | null = null

  constructor() {
    super()
    // Dynamically get the application path
    // this.dbPath = path.join(app.getPath('userData'), "persist", "sqlite", "app.db")
    this.dbPath = path.join(
      !app.isPackaged && is.dev ? 'backend' : app.getPath('userData'),
      'persist',
      'sqlite',
      'app.db'
    )
    logger.info('📁 Database path:', this.dbPath)
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
      logger.info('✅ Database initialized successfully')
    } catch (error) {
      logger.error('❌ Database initialization failed:', error)
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
        logger.info('📁 Database directory found:', dbDir)
        return
      }

      logger.info(`⏳ Waiting for database directory... (${i + 1}/${maxRetries})`)
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
        logger.info('📊 Creating vaults table for the first time...')
        // this.createVaultsTable()
      }
    } catch (error) {
      logger.error('❌ Failed to ensure tables exist:', error)
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
  //   logger.info('✅ Vaults table created successfully')
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
  //   logger.info('✅ Todo table created successfully')
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
  //   logger.info('✅ Activity table created successfully')
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
  //   logger.info('✅ Tips table created successfully')
  // }

  // Get all activities
  public getAllActivities() {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM activity')
      const rows = stmt.all()
      logger.info('✅ All activities retrieved successfully:', rows)
      return rows
    } catch (error) {
      logger.error('❌ Failed to get all activities:', error)
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
      logger.error('❌ Failed to get new activities:', error)
      throw error
    }
  }

  public getTasks(startTime: string, endTime: string) {
    try {
      this.ensureInitialized()
      if (!isValidIsoString(startTime)) {
        logger.error('❌ Invalid startTime format:', startTime)
        throw new Error('Invalid startTime format. Expected ISO 8601 string.')
      }
      if (!isValidIsoString(endTime)) {
        logger.error('❌ Invalid endTime format:', endTime)
        throw new Error('Invalid endTime format. Expected ISO 8601 string.')
      }
      const db = DB.getInstance(DB.dbName)
      const sql = 'SELECT * FROM todo WHERE start_time >= ? AND start_time < ? ORDER BY start_time ASC'
      const rows = db.query<TODOActivity>(sql, [startTime, endTime])
      return rows
    } catch (error) {
      logger.error('❌ Failed to get tasks:', error)
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
      logger.error('❌ Failed to add task:', error)
      throw error
    }
  }

  public toggleTaskStatus(taskId: number) {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('UPDATE todo SET status = 1 - status WHERE id = ?')
      const result = stmt.run(taskId)
      logger.info('✅ Task status toggled successfully')
      return result
    } catch (error) {
      logger.error('❌ Failed to toggle task status:', error)
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

      logger.info(`✅ Task updated successfully: ID ${taskId}, rows affected: ${result.changes}`)
      return result
    } catch (error) {
      logger.error('❌ Failed to update task:', error)
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

      logger.info(`✅ Task deleted successfully: ID ${taskId}, rows affected: ${result.changes}`)
      return result
    } catch (error) {
      logger.error('❌ Failed to delete task:', error)
      throw error
    }
  }

  public getAllTips() {
    try {
      this.ensureInitialized()
      const stmt = this.db!.prepare('SELECT * FROM tips')
      const rows = stmt.all()
      logger.info('✅ Tips retrieved successfully')
      return rows
    } catch (error) {
      logger.error('❌ Failed to get tips:', error)
      throw error
    }
  }

  close() {
    try {
      logger.info('🔒 Closing database connection...')
      this.db?.close()
    } catch (error) {
      logger.error('❌ Error closing database:', error)
    }
  }
}

// 导出单例实例
const databaseManager = new DatabaseManager()
export default databaseManager

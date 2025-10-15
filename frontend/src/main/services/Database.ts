// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { is } from '@electron-toolkit/utils'
import BetterSqlite3, { type Statement, type RunResult, type Database as BetterSqliteDatabase } from 'better-sqlite3'
import path from 'path'
import fs from 'fs'
import { app } from 'electron'

/**
 * Represents the result of a query returning a list of items.
 * @template T The type of items in the result array.
 */
type QueryResult<T> = T[]

/**
 * Represents the result of a query returning a single item.
 * @template T The type of the item.
 */
type QueryOneResult<T> = T | undefined

/**
 * A robust, production-ready database wrapper for better-sqlite3,
 * built upon the official documentation's best practices.
 */
export class DB {
  public static dbName = 'app.db'
  private static instance?: DB
  private readonly db: BetterSqliteDatabase
  private static readonly statementCache = new Map<string, Statement>()

  /**
   * The constructor is private to enforce the singleton pattern.
   * Use DB.getInstance() to get the database connection.
   * @param dbFilePath The full path to the SQLite database file.
   */
  private constructor(dbFilePath: string) {
    const dir = path.dirname(dbFilePath)
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true })
    }
    const options: BetterSqlite3.Options = {
      verbose: is.dev ? console.log : undefined, // Can be enabled for debugging to print executed SQL
      fileMustExist: false
    }
    this.db = new BetterSqlite3(dbFilePath, options)

    this.applyBestPractices()
    this.setupExitHooks()
  }

  private applyBestPractices(): void {
    this.db.pragma('journal_mode = WAL')
    this.db.pragma('synchronous = NORMAL')
    this.db.pragma('busy_timeout = 5000')
    this.db.pragma('cache_size = -64000') // 64MB
    this.db.pragma('foreign_keys = ON')
  }

  private setupExitHooks(): void {
    process.on('exit', () => this.close())
    process.on('SIGHUP', () => process.exit(128 + 1))
    process.on('SIGINT', () => process.exit(128 + 2))
    process.on('SIGTERM', () => process.exit(128 + 15))
  }

  public static getInstance(dbName: string = 'app.db', dbPath1?: string): DB {
    if (!this.instance) {
      // It is recommended to place the database file in a fixed location, such as the data folder in the project root directory
      const dbPath =
        dbPath1 ||
        path.join(!app.isPackaged && is.dev ? 'backend' : app.getPath('userData'), 'persist', 'sqlite', dbName)
      this.instance = new DB(dbPath)
    }
    return this.instance
  }

  public close(): void {
    if (this.db && this.db.open) {
      this.db.close()
      console.log('Database connection closed.')
    }
  }

  private prepare(sql: string): Statement {
    if (DB.statementCache.has(sql)) {
      return DB.statementCache.get(sql)!
    }
    const stmt = this.db.prepare(sql)
    DB.statementCache.set(sql, stmt)
    return stmt
  }

  public insert<T extends object>(table: string, data: T): RunResult {
    const keys = Object.keys(data)
    const columns = keys.join(', ')
    const placeholders = keys.map((key) => `@${key}`).join(', ')
    const sql = `INSERT INTO ${table} (${columns}) VALUES (${placeholders})`
    return this.prepare(sql).run(data)
  }

  public insertMany<T extends object>(table: string, items: T[]): void {
    if (!items || items.length === 0) return

    const firstItem = items[0]
    const keys = Object.keys(firstItem)
    const columns = keys.join(', ')
    const placeholders = keys.map((key) => `@${key}`).join(', ')
    const sql = `INSERT INTO ${table} (${columns}) VALUES (${placeholders})`

    const insertStatement = this.prepare(sql)
    const insertTransaction = this.db.transaction((records: T[]) => {
      for (const record of records) {
        insertStatement.run(record)
      }
    })

    try {
      insertTransaction(items)
    } catch (err) {
      console.error(`Transaction failed for bulk insert into ${table}:`, err)
      throw err
    }
  }

  public update<TData extends object, TWhere extends object>(table: string, data: TData, where: TWhere): RunResult {
    const dataKeys = Object.keys(data)
    const whereKeys = Object.keys(where)
    if (dataKeys.length === 0 || whereKeys.length === 0) {
      throw new Error('Update operation requires both data and where clauses.')
    }

    const setClause = dataKeys.map((key) => `${key} = @${key}`).join(', ')
    const whereClause = whereKeys.map((key) => `${key} = @where_${key}`).join(' AND ')
    const sql = `UPDATE ${table} SET ${setClause} WHERE ${whereClause}`

    const params: Record<string, any> = {}
    for (const key in data) {
      params[key] = data[key as keyof TData]
    }
    for (const key in where) {
      params[`where_${key}`] = where[key as keyof TWhere]
    }

    return this.prepare(sql).run(params)
  }

  public upsert<T extends object>(table: string, data: T, conflictTarget: keyof T | (keyof T)[]): RunResult {
    const keys = Object.keys(data)
    const columns = keys.join(', ')
    const placeholders = keys.map((key) => `@${key}`).join(', ')
    const conflictCols = Array.isArray(conflictTarget) ? conflictTarget.join(', ') : (conflictTarget as string)

    const conflictKeys = new Set(Array.isArray(conflictTarget) ? conflictTarget : [conflictTarget])
    const updateKeys = keys.filter((key) => !conflictKeys.has(key as keyof T))

    if (updateKeys.length === 0) {
      const sql = `INSERT INTO ${table} (${columns}) VALUES (${placeholders}) ON CONFLICT(${conflictCols}) DO NOTHING`
      return this.prepare(sql).run(data)
    }

    const updateClause = updateKeys.map((key) => `${key} = excluded.${key}`).join(', ')
    const sql = `INSERT INTO ${table} (${columns}) VALUES (${placeholders}) ON CONFLICT(${conflictCols}) DO UPDATE SET ${updateClause}`
    return this.prepare(sql).run(data)
  }

  /**
   * FINAL FIX: This method now correctly handles calls with and without parameters.
   */
  public queryOne<T extends object>(sql: string, params?: any): QueryOneResult<T> {
    const stmt = this.prepare(sql)
    return (params !== undefined ? stmt.get(params) : stmt.get()) as QueryOneResult<T>
  }

  /**
   * FINAL FIX: This method now correctly handles calls with and without parameters.
   */
  public query<T extends object>(sql: string, params?: any): QueryResult<T> {
    const stmt = this.prepare(sql)
    return (params !== undefined ? stmt.all(params) : stmt.all()) as QueryResult<T>
  }

  /**
   * FINAL FIX: This method now correctly handles calls with and without parameters.
   */
  public execute(sql: string, params?: any): RunResult {
    const stmt = this.prepare(sql)
    return params !== undefined ? stmt.run(params) : stmt.run()
  }
}

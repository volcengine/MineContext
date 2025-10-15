// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

// electron/main/taskQueueManager.ts
import Database from 'better-sqlite3'
import { BrowserWindow } from 'electron'
import { Worker } from 'worker_threads'
import path from 'path'

export class TaskQueueManager {
  private db: Database.Database
  private win: BrowserWindow
  private workers: Record<string, Worker> = {}

  constructor(dbPath: string, win: BrowserWindow) {
    this.db = new Database(dbPath)
    this.db.pragma('journal_mode = WAL')
    this.win = win
    this.initSchema()

    // Start two Workers
    this.workers['dbQuery'] = this.createWorker('dbWorker.js')
    this.workers['fetchApi'] = this.createWorker('apiWorker.js')
  }

  private initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        payload JSON NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending',
        retries INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        cron TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
    `)
  }

  private createWorker(file: string) {
    const worker = new Worker(path.join(__dirname, file), {
      env: { DB_PATH: this.db.name } // Pass DB path to Worker
    })

    worker.on('message', (msg) => {
      if (msg.channel && this.win && !this.win.isDestroyed()) {
        this.win.webContents.send(msg.channel, msg.data)
      }
    })

    return worker
  }

  /** Add a task */
  addTask(type: string, payload: any, maxRetries = 3, cronExp?: string) {
    const info = this.db
      .prepare('INSERT INTO tasks (type, payload, max_retries, cron) VALUES (@type, @payload, @max_retries, @cron)')
      .run({
        type,
        payload: JSON.stringify(payload),
        max_retries: maxRetries,
        cron: cronExp || null
      })

    const id = info.lastInsertRowid as number

    // Distribute to the corresponding Worker
    if (this.workers[type]) {
      this.workers[type].postMessage({ action: 'addTask', id, type, cron: cronExp })
    }

    return id
  }

  /** Delete a task */
  deleteTask(id: number, type: string) {
    if (this.workers[type]) {
      this.workers[type].postMessage({ action: 'deleteTask', id })
    }
    this.db.prepare('DELETE FROM tasks WHERE id=?').run(id)
  }

  getAllTasks() {
    return this.db.prepare('SELECT * FROM tasks ORDER BY created_at DESC').all()
  }
}

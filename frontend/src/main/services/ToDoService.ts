import { getLogger } from '@shared/logger/main'
import { DB } from './Database'
import dayjs from 'dayjs'

const logger = getLogger('ToDoService')

export interface ToDo {
  id: number
  content: string
  created_at: string
  start_time: string
  end_time?: string
  status: number
  urgency: number
  assignee?: string
  reason?: string
}

export interface ToDoQueryOptions {
  status?: number
  startTimeFrom?: number // Unix timestamp (milliseconds)
  startTimeTo?: number // Unix timestamp (milliseconds)
  endTimeFrom?: number // Unix timestamp (milliseconds)
  endTimeTo?: number // Unix timestamp (milliseconds)
  limit?: number
  offset?: number
}

class ToDoService {
  private static db: DB

  private static getDB(): DB {
    if (!this.db) {
      this.db = DB.getInstance()
    }
    return this.db
  }

  /**
   * Query TODOs with time range and status filters
   * @param options Query options including status and time range filters
   * @returns Array of TODO items
   */
  static queryToDos(options: ToDoQueryOptions = {}): ToDo[] {
    try {
      const db = this.getDB()

      // Build WHERE conditions
      const conditions: string[] = []
      const params: Record<string, any> = {}

      if (options.status !== undefined) {
        conditions.push('status = @status')
        params.status = options.status
      }

      if (options.startTimeFrom !== undefined) {
        conditions.push('start_time >= @startTimeFrom')
        params.startTimeFrom = dayjs(options.startTimeFrom).toISOString()
      }

      if (options.startTimeTo !== undefined) {
        conditions.push('start_time <= @startTimeTo')
        params.startTimeTo = dayjs(options.startTimeTo).toISOString()
      }

      if (options.endTimeFrom !== undefined) {
        conditions.push('end_time >= @endTimeFrom')
        params.endTimeFrom = dayjs(options.endTimeFrom).toISOString()
      }

      if (options.endTimeTo !== undefined) {
        conditions.push('end_time <= @endTimeTo')
        params.endTimeTo = dayjs(options.endTimeTo).toISOString()
      }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''
      const limit = options.limit ?? 100
      const offset = options.offset ?? 0

      const sql = `
        SELECT id, content, created_at, start_time, end_time, status, urgency, assignee, reason
        FROM todo
        ${whereClause}
        ORDER BY urgency DESC, created_at DESC
        LIMIT ${limit} OFFSET ${offset}
      `

      const result = db.query<ToDo>(sql, conditions.length > 0 ? params : undefined)
      logger.log(`Queried ${result.length} TODOs with options:`, options)
      return result
    } catch (error) {
      logger.error('Failed to query TODOs:', error)
      throw error
    }
  }

  /**
   * Get a single TODO by ID
   * @param id TODO ID
   * @returns TODO item or undefined
   */
  static getToDoById(id: number): ToDo | undefined {
    try {
      const db = this.getDB()
      const sql = `
        SELECT id, content, created_at, start_time, end_time, status, urgency, assignee, reason
        FROM todo
        WHERE id = @id
      `
      const result = db.queryOne<ToDo>(sql, { id })
      return result
    } catch (error) {
      logger.error(`Failed to get TODO with id ${id}:`, error)
      throw error
    }
  }

  /**
   * Create a new TODO item
   * @param todo TODO data (without id)
   * @returns The inserted row ID
   */
  static createToDo(todo: Omit<ToDo, 'id' | 'created_at'>): number {
    try {
      const db = this.getDB()
      const data = {
        content: todo.content,
        start_time: todo.start_time || dayjs().toISOString(),
        end_time: todo.end_time || null,
        status: todo.status ?? 0,
        urgency: todo.urgency ?? 0,
        assignee: todo.assignee || null,
        reason: todo.reason || null
      }
      const result = db.insert('todo', data)
      logger.log(`Created TODO with id ${result.lastInsertRowid}`)
      return result.lastInsertRowid as number
    } catch (error) {
      logger.error('Failed to create TODO:', error)
      throw error
    }
  }

  /**
   * Update TODO status
   * @param id TODO ID
   * @param status New status
   * @param endTime Optional end time as Unix timestamp (defaults to now if status is 1)
   * @returns Number of affected rows
   */
  static updateToDoStatus(id: number, status: number, endTime?: number): number {
    try {
      const db = this.getDB()
      const data = {
        status,
        end_time: status === 1 && !endTime ? dayjs().toISOString() : endTime ? dayjs(endTime).toISOString() : null
      }
      const result = db.update('todo', data, { id })
      logger.log(`Updated TODO ${id} status to ${status}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to update TODO ${id} status:`, error)
      throw error
    }
  }

  /**
   * Update TODO fields
   * @param id TODO ID
   * @param updates Fields to update
   * @returns Number of affected rows
   */
  static updateToDo(id: number, updates: Partial<Omit<ToDo, 'id' | 'created_at'>>): number {
    try {
      const db = this.getDB()
      const data: Record<string, any> = {}

      if (updates.content !== undefined) data.content = updates.content
      if (updates.start_time !== undefined) data.start_time = updates.start_time
      if (updates.end_time !== undefined) data.end_time = updates.end_time
      if (updates.status !== undefined) data.status = updates.status
      if (updates.urgency !== undefined) data.urgency = updates.urgency
      if (updates.assignee !== undefined) data.assignee = updates.assignee
      if (updates.reason !== undefined) data.reason = updates.reason

      const result = db.update('todo', data, { id })
      logger.log(`Updated TODO ${id}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to update TODO ${id}:`, error)
      throw error
    }
  }

  /**
   * Delete a TODO item
   * @param id TODO ID
   * @returns Number of affected rows
   */
  static deleteToDo(id: number): number {
    try {
      const db = this.getDB()
      const sql = `DELETE FROM todo WHERE id = @id`
      const result = db.execute(sql, { id })
      logger.log(`Deleted TODO ${id}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to delete TODO ${id}:`, error)
      throw error
    }
  }

  /**
   * Get TODOs by status
   * @param status Status value (0 = pending, 1 = completed, etc.)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of TODO items
   */
  static getToDosByStatus(status: number, limit = 100, offset = 0): ToDo[] {
    return this.queryToDos({ status, limit, offset })
  }

  /**
   * Get TODOs within a time range
   * @param startFrom Start time lower bound (Unix timestamp)
   * @param startTo Start time upper bound (Unix timestamp)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of TODO items
   */
  static getToDosInTimeRange(
    startFrom: number,
    startTo: number,
    limit = 100,
    offset = 0
  ): ToDo[] {
    return this.queryToDos({
      startTimeFrom: startFrom,
      startTimeTo: startTo,
      limit,
      offset
    })
  }

  /**
   * Get all TODOs (with pagination)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of TODO items
   */
  static getAllToDos(limit = 100, offset = 0): ToDo[] {
    return this.queryToDos({ limit, offset })
  }
}

export { ToDoService }

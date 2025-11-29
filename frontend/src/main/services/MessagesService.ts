// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getLogger } from '@shared/logger/main'
import { DB } from './Database'
import dayjs from 'dayjs'

const logger = getLogger('MessagesService')

export interface Conversation {
  id: number
  title?: string
  user_id?: string
  page_name: string
  status: string
  metadata: string
  created_at: string
  updated_at: string
}

export interface ConversationQueryOptions {
  status?: string // 'active' | 'deleted' | etc.
  pageName?: string // Filter by page name
  userId?: string // Filter by user ID
  createdFrom?: number // Created time lower bound (Unix timestamp in milliseconds)
  createdTo?: number // Created time upper bound (Unix timestamp in milliseconds)
  updatedFrom?: number // Updated time lower bound (Unix timestamp in milliseconds)
  updatedTo?: number // Updated time upper bound (Unix timestamp in milliseconds)
  limit?: number // Max number of results
  offset?: number // Offset for pagination
}

class MessagesService {
  private static db: DB

  private static getDB(): DB {
    if (!this.db) {
      this.db = DB.getInstance()
    }
    return this.db
  }

  /**
   * Query conversations with time range and status filters
   * @param options Query options including status and time range filters
   * @returns Array of Conversation items
   */
  static queryConversations(options: ConversationQueryOptions = {}): Conversation[] {
    try {
      const db = this.getDB()

      // Build WHERE conditions
      const conditions: string[] = []
      const params: Record<string, any> = {}

      if (options.status !== undefined) {
        conditions.push('status = @status')
        params.status = options.status
      }

      if (options.pageName !== undefined) {
        conditions.push('page_name = @pageName')
        params.pageName = options.pageName
      }

      if (options.userId !== undefined) {
        conditions.push('user_id = @userId')
        params.userId = options.userId
      }

      if (options.createdFrom !== undefined) {
        conditions.push('created_at >= @createdFrom')
        params.createdFrom = dayjs(options.createdFrom).toISOString()
      }

      if (options.createdTo !== undefined) {
        conditions.push('created_at <= @createdTo')
        params.createdTo = dayjs(options.createdTo).toISOString()
      }

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
        SELECT id, title, user_id, page_name, status, metadata, created_at, updated_at
        FROM conversations
        ${whereClause}
        ORDER BY updated_at DESC
        LIMIT ${limit} OFFSET ${offset}
      `

      const result = db.query<Conversation>(sql, conditions.length > 0 ? params : undefined)
      logger.log(`Queried ${result.length} conversations with options:`, options)
      return result
    } catch (error) {
      logger.error('Failed to query conversations:', error)
      throw error
    }
  }

  /**
   * Get a single conversation by ID
   * @param id Conversation ID
   * @returns Conversation item or undefined
   */
  static getConversationById(id: number): Conversation | undefined {
    try {
      const db = this.getDB()
      const sql = `
        SELECT id, title, user_id, page_name, status, metadata, created_at, updated_at
        FROM conversations
        WHERE id = @id
      `
      const result = db.queryOne<Conversation>(sql, { id })
      return result
    } catch (error) {
      logger.error(`Failed to get conversation with id ${id}:`, error)
      throw error
    }
  }

  /**
   * Create a new conversation
   * @param conversation Conversation data (without id, created_at, updated_at)
   * @returns The inserted row ID
   */
  static createConversation(conversation: Omit<Conversation, 'id' | 'created_at' | 'updated_at'>): number {
    try {
      const db = this.getDB()
      const data = {
        title: conversation.title || null,
        user_id: conversation.user_id || null,
        page_name: conversation.page_name || 'home',
        status: conversation.status || 'active',
        metadata: conversation.metadata || '{}'
      }
      const result = db.insert('conversations', data)
      logger.log(`Created conversation with id ${result.lastInsertRowid}`)
      return result.lastInsertRowid as number
    } catch (error) {
      logger.error('Failed to create conversation:', error)
      throw error
    }
  }

  /**
   * Update conversation
   * @param id Conversation ID
   * @param updates Fields to update
   * @returns Number of affected rows
   */
  static updateConversation(
    id: number,
    updates: Partial<Omit<Conversation, 'id' | 'created_at' | 'updated_at'>>
  ): number {
    try {
      const db = this.getDB()
      const data: Record<string, any> = {}

      if (updates.title !== undefined) data.title = updates.title
      if (updates.user_id !== undefined) data.user_id = updates.user_id
      if (updates.page_name !== undefined) data.page_name = updates.page_name
      if (updates.status !== undefined) data.status = updates.status
      if (updates.metadata !== undefined) data.metadata = updates.metadata

      // Auto update updated_at
      data.updated_at = dayjs().toISOString()

      const result = db.update('conversations', data, { id })
      logger.log(`Updated conversation ${id}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to update conversation ${id}:`, error)
      throw error
    }
  }

  /**
   * Delete conversation (soft delete by setting status to 'deleted')
   * @param id Conversation ID
   * @returns Number of affected rows
   */
  static deleteConversation(id: number): number {
    try {
      const db = this.getDB()
      const data = {
        status: 'deleted',
        updated_at: dayjs().toISOString()
      }
      const result = db.update('conversations', data, { id })
      logger.log(`Deleted conversation ${id}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to delete conversation ${id}:`, error)
      throw error
    }
  }

  /**
   * Hard delete conversation (permanently delete)
   * @param id Conversation ID
   * @returns Number of affected rows
   */
  static hardDeleteConversation(id: number): number {
    try {
      const db = this.getDB()
      const sql = `DELETE FROM conversations WHERE id = @id`
      const result = db.execute(sql, { id })
      logger.log(`Hard deleted conversation ${id}`)
      return result.changes
    } catch (error) {
      logger.error(`Failed to hard delete conversation ${id}:`, error)
      throw error
    }
  }

  /**
   * Get conversations by status
   * @param status Status value ('active', 'deleted', etc.)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Conversation items
   */
  static getConversationsByStatus(status: string, limit = 100, offset = 0): Conversation[] {
    return this.queryConversations({ status, limit, offset })
  }

  /**
   * Get conversations within a time range (created_at)
   * @param createdFrom Created time lower bound (Unix timestamp)
   * @param createdTo Created time upper bound (Unix timestamp)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Conversation items
   */
  static getConversationsInTimeRange(createdFrom: number, createdTo: number, limit = 100, offset = 0): Conversation[] {
    return this.queryConversations({
      createdFrom,
      createdTo,
      limit,
      offset
    })
  }

  /**
   * Get recently updated conversations
   * @param days Number of days to look back (default: 7)
   * @param limit Max number of results
   * @returns Array of Conversation items
   */
  static getRecentlyUpdatedConversations(days = 7, limit = 100): Conversation[] {
    const updatedFrom = dayjs().subtract(days, 'day').valueOf()
    const updatedTo = dayjs().valueOf()

    return this.queryConversations({
      updatedFrom,
      updatedTo,
      limit
    })
  }

  /**
   * Get conversations by page name
   * @param pageName Page name filter
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Conversation items
   */
  static getConversationsByPageName(pageName: string, limit = 100, offset = 0): Conversation[] {
    return this.queryConversations({ pageName, limit, offset })
  }

  /**
   * Get conversations by user ID
   * @param userId User ID filter
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Conversation items
   */
  static getConversationsByUserId(userId: string, limit = 100, offset = 0): Conversation[] {
    return this.queryConversations({ userId, limit, offset })
  }

  /**
   * Get active conversations for a specific page and time range
   * @param pageName Page name filter
   * @param createdFrom Optional created time lower bound
   * @param createdTo Optional created time upper bound
   * @param limit Max number of results
   * @returns Array of Conversation items
   */
  static getActiveConversationsByPageAndTimeRange(
    pageName: string,
    createdFrom?: number,
    createdTo?: number,
    limit = 100
  ): Conversation[] {
    return this.queryConversations({
      status: 'active',
      pageName,
      createdFrom,
      createdTo,
      limit
    })
  }

  /**
   * Get all active conversations (with pagination)
   * @param limit Max number of results
   * @param offset Offset for pagination
   * @returns Array of Conversation items
   */
  static getAllActiveConversations(limit = 100, offset = 0): Conversation[] {
    return this.queryConversations({ status: 'active', limit, offset })
  }

  /**
   * Count conversations by filters
   * @param options Query options
   * @returns Total count
   */
  static countConversations(options: ConversationQueryOptions = {}): number {
    try {
      const db = this.getDB()

      // Build WHERE conditions
      const conditions: string[] = []
      const params: Record<string, any> = {}

      if (options.status !== undefined) {
        conditions.push('status = @status')
        params.status = options.status
      }

      if (options.pageName !== undefined) {
        conditions.push('page_name = @pageName')
        params.pageName = options.pageName
      }

      if (options.userId !== undefined) {
        conditions.push('user_id = @userId')
        params.userId = options.userId
      }

      if (options.createdFrom !== undefined) {
        conditions.push('created_at >= @createdFrom')
        params.createdFrom = dayjs(options.createdFrom).toISOString()
      }

      if (options.createdTo !== undefined) {
        conditions.push('created_at <= @createdTo')
        params.createdTo = dayjs(options.createdTo).toISOString()
      }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : ''

      const sql = `
        SELECT COUNT(*) as count
        FROM conversations
        ${whereClause}
      `

      const result = db.queryOne<{ count: number }>(sql, conditions.length > 0 ? params : undefined)
      return result?.count ?? 0
    } catch (error) {
      logger.error('Failed to count conversations:', error)
      throw error
    }
  }
}

export { MessagesService }

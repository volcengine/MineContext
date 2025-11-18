// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import { getLogger } from '@shared/logger/main'
import dayjs from 'dayjs'
import { ToDoService } from './ToDoService'
import { MessagesService } from './MessagesService'
import { VaultDatabaseService } from './VaultDatabaseService'
import axios from 'axios'
import { getBackendPort } from '@main/backend'

const logger = getLogger('HeatmapService')

/**
 * Heatmap data aggregated from multiple sources
 */
export interface HeatmapData {
  date: string // Date in YYYY-MM-DD format
  todos: number // Number of todos
  conversations: number // Number of conversations
  vaults: number // Number of vaults
  screenshots: number // Number of screenshots
  documents: number // Number of documents
  contexts: number // Number of contexts
  total: number // Total activity count
}

/**
 * Data stats from monitoring API (aggregated)
 */
interface MonitoringDataStats {
  data_type: string
  count: number
  context_type?: string
}

/**
 * Data stats trend from monitoring API (time series)
 */
interface MonitoringDataTrend {
  timestamp: string // ISO timestamp or time_bucket
  data_type: string
  count: number
  context_type?: string
}

/**
 * Response from monitoring API
 */
interface MonitoringResponse {
  success: boolean
  data: MonitoringDataStats[]
}

/**
 * Response from monitoring range API (aggregated stats for a time range)
 */
interface MonitoringRangeResponse {
  success: boolean
  data: {
    by_data_type: Record<string, number>
    total_data_processed: number
    by_context_type: Record<string, number>
    time_range: {
      start_time: string
      end_time: string
    }
  }
}

class HeatmapService {
  /**
   * Get aggregated heatmap data for a time range
   * @param startTime Start time (Unix timestamp in milliseconds)
   * @param endTime End time (Unix timestamp in milliseconds)
   * @returns Array of heatmap data grouped by date
   */
  static async getHeatmapData(startTime: number, endTime: number): Promise<HeatmapData[]> {
    try {
      logger.log(
        `Fetching heatmap data from ${dayjs(startTime).format('YYYY-MM-DD')} to ${dayjs(endTime).format('YYYY-MM-DD')}`
      )

      // Fetch data from all sources in parallel
      const [todos, conversations, vaults, monitoringTrend] = await Promise.all([
        this.getToDosData(startTime, endTime, 1), // Only fetch completed todos
        this.getConversationsData(startTime, endTime, 'active'),
        this.getVaultsData(startTime, endTime),
        this.getMonitoringTrendData(startTime, endTime)
      ])

      // Generate date range
      const dateMap = this.generateDateMap(startTime, endTime)

      // Aggregate todos by date
      todos.forEach((todo) => {
        const date = dayjs(todo.start_time).format('YYYY-MM-DD')
        if (dateMap[date]) {
          dateMap[date].todos++
        }
      })

      // Aggregate conversations by date
      conversations.forEach((conversation) => {
        const date = dayjs(conversation.created_at).format('YYYY-MM-DD')
        if (dateMap[date]) {
          dateMap[date].conversations++
        }
      })

      // Aggregate vaults by date
      vaults.forEach((vault) => {
        const date = dayjs(vault.created_at).format('YYYY-MM-DD')
        if (dateMap[date]) {
          dateMap[date].vaults++
        }
      })

      // Aggregate monitoring trend data by date
      monitoringTrend.forEach((item) => {
        const date = dayjs(item.timestamp).format('YYYY-MM-DD')
        if (dateMap[date]) {
          // Map data_type to corresponding field
          switch (item.data_type) {
            case 'screenshot':
              dateMap[date].screenshots += item.count
              break
            case 'document':
              dateMap[date].documents += item.count
              break
            case 'context':
              dateMap[date].contexts += item.count
              break
          }
        }
      })

      // Calculate totals and convert to array
      const result = Object.keys(dateMap)
        .sort()
        .map((date) => {
          const data = dateMap[date]
          data.total = data.todos + data.conversations + data.vaults + data.screenshots + data.documents + data.contexts
          return data
        })

      logger.log(`Generated heatmap data for ${result.length} days`)
      return result
    } catch (error) {
      logger.error('Failed to get heatmap data:', error)
      throw error
    }
  }

  /**
   * Generate a map of dates with initialized counts
   */
  private static generateDateMap(startTime: number, endTime: number): Record<string, HeatmapData> {
    const dateMap: Record<string, HeatmapData> = {}
    let currentDate = dayjs(startTime).startOf('day')
    const endDate = dayjs(endTime).startOf('day')

    while (currentDate.isBefore(endDate) || currentDate.isSame(endDate)) {
      const dateStr = currentDate.format('YYYY-MM-DD')
      dateMap[dateStr] = {
        date: dateStr,
        todos: 0,
        conversations: 0,
        vaults: 0,
        screenshots: 0,
        documents: 0,
        contexts: 0,
        total: 0
      }
      currentDate = currentDate.add(1, 'day')
    }

    return dateMap
  }

  /**
   * Fetch todos data from ToDoService
   */
  private static async getToDosData(startTime: number, endTime: number, status: number) {
    try {
      // Note: ToDoService uses startTimeFrom/startTimeTo for filtering
      // We use these to filter by when the todo was started, not created
      return ToDoService.queryToDos({
        startTimeFrom: startTime,
        startTimeTo: endTime,
        limit: 10000, // High limit to get all data
        status
      })
    } catch (error) {
      logger.error('Failed to fetch todos data:', error)
      return []
    }
  }

  /**
   * Fetch conversations data from MessagesService
   */
  private static async getConversationsData(startTime: number, endTime: number, status: string) {
    try {
      return MessagesService.queryConversations({
        createdFrom: startTime,
        createdTo: endTime,
        limit: 10000,
        status
      })
    } catch (error) {
      logger.error('Failed to fetch conversations data:', error)
      return []
    }
  }

  /**
   * Fetch vaults data from VaultDatabaseService
   */
  private static async getVaultsData(startTime: number, endTime: number) {
    try {
      const service = new VaultDatabaseService()
      return service.queryVaults({
        createdFrom: startTime,
        createdTo: endTime,
        limit: 10000
      })
    } catch (error) {
      logger.error('Failed to fetch vaults data:', error)
      return []
    }
  }

  /**
   * Fetch monitoring data (screenshots, documents, contexts) from API
   * This returns aggregated stats for the entire time range
   */
  static async getMonitoringData(startTime: number, endTime: number): Promise<MonitoringDataStats[]> {
    try {
      const response = await axios.get<MonitoringResponse>('/api/monitoring/data-stats-range', {
        params: {
          start_time: dayjs(startTime).toISOString(),
          end_time: dayjs(endTime).toISOString()
        }
      })

      if (response.data.success) {
        return response.data.data
      }
      return []
    } catch (error) {
      logger.error('Failed to fetch monitoring data:', error)
      return []
    }
  }

  /**
   * Fetch monitoring trend data (time series data broken down by time buckets)
   * This is used internally to get per-day granularity for heatmap
   * Note: The range API returns aggregated data, so we distribute it evenly across the date range
   */
  private static async getMonitoringTrendData(startTime: number, endTime: number): Promise<MonitoringDataTrend[]> {
    try {
      // Convert timestamps to ISO format for the API
      const startTimeISO = dayjs(startTime).toISOString()
      const endTimeISO = dayjs(endTime).toISOString()

      // Use the range API which provides aggregated data for the specified time range
      const response = await axios.get<MonitoringRangeResponse>(
        `http://127.0.0.1:${getBackendPort()}/api/monitoring/data-stats-range`,
        {
          params: {
            start_time: startTimeISO,
            end_time: endTimeISO
          }
        }
      )

      if (response.data.success && response.data.data) {
        const rangeData = response.data.data
        const result: MonitoringDataTrend[] = []

        // Calculate the number of days in the range
        const startDay = dayjs(startTime).startOf('day')
        const endDay = dayjs(endTime).startOf('day')
        const numDays = endDay.diff(startDay, 'day') + 1

        // Distribute the aggregated counts evenly across each day
        // For each data type, create entries for each day in the range
        const dataTypes = ['screenshot', 'document', 'context'] as const

        for (const dataType of dataTypes) {
          const totalCount = rangeData.by_data_type[dataType] || 0
          const countPerDay = Math.floor(totalCount / numDays)
          const remainder = totalCount % numDays

          let currentDay = startDay
          for (let i = 0; i < numDays; i++) {
            // Distribute remainder to first few days
            const dayCount = countPerDay + (i < remainder ? 1 : 0)
            if (dayCount > 0) {
              result.push({
                timestamp: currentDay.toISOString(),
                data_type: dataType,
                count: dayCount
              })
            }
            currentDay = currentDay.add(1, 'day')
          }
        }

        return result
      }
      return []
    } catch (error) {
      logger.error('Failed to fetch monitoring trend data:', error)
      return []
    }
  }

  /**
   * Get monitoring stats summary for a time range
   * Returns aggregated counts by data type
   */
  static async getMonitoringStatsSummary(
    startTime: number,
    endTime: number
  ): Promise<{
    screenshots: number
    documents: number
    contexts: number
    total: number
  }> {
    try {
      const stats = await this.getMonitoringData(startTime, endTime)

      const summary = stats.reduce(
        (acc, stat) => {
          switch (stat.data_type) {
            case 'screenshot':
              acc.screenshots += stat.count
              break
            case 'document':
              acc.documents += stat.count
              break
            case 'context':
              acc.contexts += stat.count
              break
          }
          return acc
        },
        {
          screenshots: 0,
          documents: 0,
          contexts: 0,
          total: 0
        }
      )

      summary.total = summary.screenshots + summary.documents + summary.contexts
      return summary
    } catch (error) {
      logger.error('Failed to get monitoring stats summary:', error)
      return {
        screenshots: 0,
        documents: 0,
        contexts: 0,
        total: 0
      }
    }
  }

  /**
   * Get heatmap data for a specific date range (convenience method)
   * @param days Number of days to look back (default: 30)
   * @returns Array of heatmap data
   */
  static async getRecentHeatmapData(days = 30): Promise<HeatmapData[]> {
    const endTime = dayjs().endOf('day').valueOf()
    const startTime = dayjs().subtract(days, 'day').startOf('day').valueOf()
    return this.getHeatmapData(startTime, endTime)
  }

  /**
   * Get heatmap data for current month
   */
  static async getCurrentMonthHeatmapData(): Promise<HeatmapData[]> {
    const startTime = dayjs().startOf('month').valueOf()
    const endTime = dayjs().endOf('month').valueOf()
    return this.getHeatmapData(startTime, endTime)
  }

  /**
   * Get heatmap data for current year
   */
  static async getCurrentYearHeatmapData(): Promise<HeatmapData[]> {
    const startTime = dayjs().startOf('year').valueOf()
    const endTime = dayjs().endOf('year').valueOf()
    return this.getHeatmapData(startTime, endTime)
  }

  /**
   * Get heatmap data for a custom date range
   * @param startDate Start date string (e.g., '2025-01-01')
   * @param endDate End date string (e.g., '2025-11-17')
   */
  static async getHeatmapDataByDateRange(startDate: string, endDate: string): Promise<HeatmapData[]> {
    const startTime = dayjs(startDate).startOf('day').valueOf()
    const endTime = dayjs(endDate).endOf('day').valueOf()
    return this.getHeatmapData(startTime, endTime)
  }

  /**
   * Get activity summary for a time range
   */
  static async getActivitySummary(
    startTime: number,
    endTime: number
  ): Promise<{
    totalTodos: number
    totalConversations: number
    totalVaults: number
    totalScreenshots: number
    totalDocuments: number
    totalContexts: number
    totalActivity: number
    dailyAverage: number
    peakDate: string
    peakCount: number
  }> {
    const heatmapData = await this.getHeatmapData(startTime, endTime)

    const summary = heatmapData.reduce(
      (acc, day) => ({
        totalTodos: acc.totalTodos + day.todos,
        totalConversations: acc.totalConversations + day.conversations,
        totalVaults: acc.totalVaults + day.vaults,
        totalScreenshots: acc.totalScreenshots + day.screenshots,
        totalDocuments: acc.totalDocuments + day.documents,
        totalContexts: acc.totalContexts + day.contexts,
        totalActivity: acc.totalActivity + day.total
      }),
      {
        totalTodos: 0,
        totalConversations: 0,
        totalVaults: 0,
        totalScreenshots: 0,
        totalDocuments: 0,
        totalContexts: 0,
        totalActivity: 0
      }
    )

    // Find peak date
    let peakDate = ''
    let peakCount = 0
    heatmapData.forEach((day) => {
      if (day.total > peakCount) {
        peakCount = day.total
        peakDate = day.date
      }
    })

    const dailyAverage = heatmapData.length > 0 ? summary.totalActivity / heatmapData.length : 0

    return {
      ...summary,
      dailyAverage,
      peakDate,
      peakCount
    }
  }
}

export { HeatmapService }

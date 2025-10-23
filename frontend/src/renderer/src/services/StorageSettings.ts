// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  headers: {
    'Content-Type': 'application/json'
  }
})

export interface StorageManagementConfig {
  retention_days: number // 7-90 days
  max_storage_size_mb: number // 0 means unlimited
  auto_cleanup_enabled: boolean
}

export interface StorageStats {
  total_size_mb: number
  file_count: number
  oldest_file_date: string
  newest_file_date: string
  retention_days: number
  max_storage_size_mb: number
}

/**
 * Get storage management settings
 */
export const getStorageSettings = async () => {
  try {
    const response = await apiClient.get('/api/storage_settings/get')
    return response.data
  } catch (error) {
    console.error('Failed to get storage settings:', error)
    throw error
  }
}

/**
 * Update storage management settings
 */
export const updateStorageSettings = async (config: StorageManagementConfig) => {
  try {
    const response = await apiClient.post('/api/storage_settings/update', {
      config
    })
    return response.data
  } catch (error) {
    console.error('Failed to update storage settings:', error)
    throw error
  }
}

/**
 * Get storage statistics
 */
export const getStorageStats = async () => {
  try {
    const response = await apiClient.get('/api/storage_settings/stats')
    return response.data
  } catch (error) {
    console.error('Failed to get storage stats:', error)
    throw error
  }
}

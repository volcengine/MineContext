// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from '@renderer/services/axiosConfig'

// Model configuration interface
export interface ModelConfig {
  modelPlatform: string // Model platform, e.g., doubao, openai, custom
  modelId: string // VLM model ID
  baseUrl: string // API base URL
  embeddingModelId: string // Embedding model ID
  apiKey: string // API key
  embeddingBaseUrl?: string // Optional separate embedding base URL
  embeddingApiKey?: string // Optional separate embedding API key
  embeddingModelPlatform?: string // Optional separate embedding platform
}

// API response data structure
export interface ModelInfoResponseData {
  config: ModelConfig
}

// Complete API response structure
export interface ApiResponse<T> {
  code: number
  status: number
  message: string
  data: T
}

// Update request interface
export interface UpdateRequest {
  modelPlatform: string
  modelId: string
  baseUrl: string
  embeddingModelId: string
  apiKey: string
  embeddingBaseUrl?: string
  embeddingApiKey?: string
  embeddingModelPlatform?: string
}

// Get model settings information
export const getModelInfo = async (): Promise<ApiResponse<ModelInfoResponseData>> => {
  const res = await axiosInstance.get<ApiResponse<ModelInfoResponseData>>('/api/model_settings/get')
  return res.data
}

// Update model settings information
// Update model settings information response data structure
export interface UpdateModelSettingsResponseData {
  success: boolean
  message: string
}

export const updateModelSettings = async (
  params: UpdateRequest
): Promise<ApiResponse<UpdateModelSettingsResponseData>> => {
  const res = await axiosInstance.post<ApiResponse<UpdateModelSettingsResponseData>>('/api/model_settings/update', {
    config: {
      ...params
    }
  })
  console.log('Submit interface response:', res)
  return res.data
}

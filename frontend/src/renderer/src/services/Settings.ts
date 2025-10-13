// Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd.
// SPDX-License-Identifier: Apache-2.0

import axiosInstance from '@renderer/services/axiosConfig'

// 模型配置接口
export interface ModelConfig {
  modelPlatform: string // 模型平台，如、doubao、openai
  modelId: string // VLM 模型 ID
  baseUrl: string // API 基础 URL
  embeddingModelId: string // Embedding 模型 ID
  apiKey: string // API 密钥
}

// 接口响应数据结构
export interface ModelInfoResponseData {
  config: ModelConfig
}

// 完整接口响应结构
export interface ApiResponse<T> {
  code: number
  status: number
  message: string
  data: T
}

// 更新请求接口
export interface UpdateRequest {
  modelPlatform: string
  modelId: string
  baseUrl: string
  embeddingModelId: string
  apiKey: string
}

// 获取模型设置信息
export const getModelInfo = async (): Promise<ApiResponse<ModelInfoResponseData>> => {
  const res = await axiosInstance.get<ApiResponse<ModelInfoResponseData>>('/api/model_settings/get')
  return res.data
}

// 更新模型设置信息
// 更新模型设置信息响应数据结构
export interface UpdateModelSettingsResponseData {
  success: boolean
  message: string
}

export const updateModelSettings = async (params: UpdateRequest): Promise<ApiResponse<UpdateModelSettingsResponseData>> => {
  const res = await axiosInstance.post<ApiResponse<UpdateModelSettingsResponseData>>('/api/model_settings/update', {
    config: {
      ...params
    }
  })
  console.log('提交接口响应:', res)
  return res.data
}
